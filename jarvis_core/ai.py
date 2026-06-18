from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import urllib.error
import urllib.request

from jarvis_core.config import ConversationSettings

log = logging.getLogger("jarvis.ai")


@dataclass(frozen=True)
class AIReply:
    provider: str
    model: str
    text: str


class AIProviderError(RuntimeError):
    pass


def available_providers(settings: ConversationSettings) -> list[str]:
    providers: list[str] = []
    if settings.openai_api_key:
        providers.append("openai")
    if settings.anthropic_api_key:
        providers.append("anthropic")
    if settings.google_api_key:
        providers.append("gemini")
    if settings.ollama_enabled:
        providers.append("ollama")
    return providers


def choose_provider(prompt: str, settings: ConversationSettings) -> str | None:
    configured = available_providers(settings)
    if not configured:
        return None

    requested = settings.ai_mode
    if requested and requested != "auto":
        return requested if requested in configured else configured[0]

    text = prompt.lower()
    coding_words = {
        "code",
        "python",
        "javascript",
        "discord",
        "bot",
        "error",
        "stack trace",
        "repo",
        "github",
        "fix",
        "debug",
        "function",
    }
    fast_words = {"quick", "simple", "short", "summarise", "summarize", "explain"}
    private_words = {"private", "offline", "local", "no cloud", "don't send"}

    if any(word in text for word in private_words) and "ollama" in configured:
        return "ollama"
    if any(word in text for word in coding_words):
        for provider in ("anthropic", "openai", "gemini", "ollama"):
            if provider in configured:
                return provider
    if any(word in text for word in fast_words):
        for provider in ("gemini", "openai", "anthropic", "ollama"):
            if provider in configured:
                return provider

    for provider in ("openai", "anthropic", "gemini", "ollama"):
        if provider in configured:
            return provider
    return configured[0]


def ask_ai(prompt: str, settings: ConversationSettings) -> AIReply:
    provider = choose_provider(prompt, settings)
    if provider is None:
        raise AIProviderError(
            "No AI providers are configured. Add OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or enable Ollama."
        )

    log.info("Routing question to %s", provider)
    if provider == "openai":
        return _ask_openai(prompt, settings)
    if provider == "anthropic":
        return _ask_anthropic(prompt, settings)
    if provider == "gemini":
        return _ask_gemini(prompt, settings)
    if provider == "ollama":
        return _ask_ollama(prompt, settings)
    raise AIProviderError(f"Unsupported provider: {provider}")


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _looks_like_text_model(model_id: str) -> bool:
    mid = model_id.lower()
    blocked = (
        "audio",
        "transcribe",
        "tts",
        "speech",
        "image",
        "vision",
        "embed",
        "moderation",
        "realtime",
        "search",
    )
    return mid.startswith(("gpt-", "o")) and not any(word in mid for word in blocked)


def _select_openai_model(client, settings: ConversationSettings) -> str:
    requested = settings.openai_model.strip()
    if requested and requested.lower() != "auto":
        return requested

    try:
        models = client.models.list()
        ids = sorted({getattr(model, "id", "") for model in models.data if getattr(model, "id", "")})
    except Exception as exc:
        log.warning("Could not list OpenAI models; falling back to gpt-4o-mini: %s", exc)
        return "gpt-4o-mini"

    for preferred in settings.openai_model_preferences:
        if preferred in ids:
            log.info("OpenAI auto-selected model: %s", preferred)
            return preferred

    for model_id in ids:
        if _looks_like_text_model(model_id):
            log.info("OpenAI auto-selected available text model: %s", model_id)
            return model_id

    raise AIProviderError("OpenAI key worked, but no usable text model was found from models.list().")


def _ask_openai(prompt: str, settings: ConversationSettings) -> AIReply:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIProviderError("Install OpenAI support with: python -m pip install -r requirements.txt") from exc

    client = OpenAI(api_key=settings.openai_api_key)
    model = _select_openai_model(client, settings)

    try:
        response = client.responses.create(
            model=model,
            instructions=settings.system_prompt,
            input=prompt,
        )
    except Exception as exc:
        message = str(exc)
        if "model_not_found" in message or "does not exist" in message:
            raise AIProviderError(
                f"OpenAI model {model!r} was rejected. Set JARVIS_OPENAI_MODEL=auto or choose a model listed for your API key."
            ) from exc
        raise

    text = getattr(response, "output_text", "") or str(response)
    return AIReply("openai", model, _trim(text, settings.max_response_chars))


def _ask_anthropic(prompt: str, settings: ConversationSettings) -> AIReply:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise AIProviderError("Install Anthropic support with: python -m pip install -r requirements.txt") from exc

    client = Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=500,
        system=settings.system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    chunks = []
    for block in message.content:
        text = getattr(block, "text", "")
        if text:
            chunks.append(text)
    return AIReply("anthropic", settings.anthropic_model, _trim("\n".join(chunks), settings.max_response_chars))


def _ask_gemini(prompt: str, settings: ConversationSettings) -> AIReply:
    try:
        from google import genai
    except ImportError as exc:
        raise AIProviderError("Install Gemini support with: python -m pip install -r requirements.txt") from exc

    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=f"{settings.system_prompt}\n\nUser: {prompt}",
    )
    return AIReply("gemini", settings.gemini_model, _trim(getattr(response, "text", ""), settings.max_response_chars))


def _ask_ollama(prompt: str, settings: ConversationSettings) -> AIReply:
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": settings.system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        settings.ollama_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise AIProviderError(f"Ollama request failed: {exc}") from exc

    parsed = json.loads(body)
    text = parsed.get("message", {}).get("content", "")
    return AIReply("ollama", settings.ollama_model, _trim(text, settings.max_response_chars))
