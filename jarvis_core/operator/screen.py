from __future__ import annotations

import base64
from dataclasses import replace
import logging
import mimetypes
from pathlib import Path
from time import strftime

from jarvis_core.ai import _select_openai_model, _trim
from jarvis_core.config import ConversationSettings, OperatorSettings, ROOT_DIR

log = logging.getLogger("jarvis.operator.screen")


def _screenshot_dir(settings: OperatorSettings) -> Path:
    if settings.screenshot_dir:
        return Path(settings.screenshot_dir).expanduser().resolve()
    return ROOT_DIR / ".cache" / "screenshots"


def take_screenshot(settings: OperatorSettings) -> Path:
    if not settings.screenshot_enabled:
        raise RuntimeError("Screenshots are disabled. Set JARVIS_OPERATOR_SCREENSHOT_ENABLED=true.")

    try:
        import mss
        import mss.tools
    except ImportError as exc:
        raise RuntimeError("Install screen support with: python -m pip install -r requirements.txt") from exc

    out_dir = _screenshot_dir(settings)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"screen_{strftime('%Y%m%d_%H%M%S')}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        shot = sct.grab(monitor)
        mss.tools.to_png(shot.rgb, shot.size, output=str(path))

    log.info("Screenshot saved: %s", path)
    return path


def _image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def describe_screen(
    operator: OperatorSettings,
    conversation: ConversationSettings,
    prompt: str | None = None,
) -> str:
    if not operator.describe_screen_enabled:
        raise RuntimeError("Screen description is disabled. Set JARVIS_OPERATOR_DESCRIBE_SCREEN_ENABLED=true.")
    if not conversation.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to describe screenshots.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install OpenAI support with: python -m pip install -r requirements.txt") from exc

    path = take_screenshot(operator)
    client = OpenAI(api_key=conversation.openai_api_key)
    if operator.vision_model and operator.vision_model.lower() != "auto":
        model = operator.vision_model
    else:
        model = _select_openai_model(client, conversation)

    instruction = prompt or "Describe what is visible on my screen. Be concise and useful."
    response = client.responses.create(
        model=model,
        instructions=(
            "You are JARVIS looking at the user's current screen. "
            "Describe visible UI, errors, selected text, or obvious next actions. "
            "Do not claim to see details that are not visible."
        ),
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": instruction},
                    {"type": "input_image", "image_url": _image_data_url(path)},
                ],
            }
        ],
    )
    text = getattr(response, "output_text", "") or str(response)
    return _trim(text, operator.max_description_chars)


def describe_screen_with_model_fallback(
    operator: OperatorSettings,
    conversation: ConversationSettings,
    prompt: str | None = None,
) -> str:
    """Describe the screen, retrying with common vision-capable fallbacks if needed."""
    try:
        return describe_screen(operator, conversation, prompt)
    except Exception as exc:
        message = str(exc)
        if "image" not in message.lower() and "vision" not in message.lower() and "model" not in message.lower():
            raise
        for fallback in ("gpt-4.1-mini", "gpt-4o-mini"):
            try:
                log.warning("Vision request failed; retrying with %s: %s", fallback, exc)
                return describe_screen(
                    operator,
                    replace(conversation, openai_model=fallback),
                    prompt,
                )
            except Exception:
                continue
        raise
