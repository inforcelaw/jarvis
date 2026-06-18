from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from jarvis_core.config import ConversationSettings, OperatorSettings, SpeechSettings
from jarvis_core.operator.control import (
    click_xy,
    hotkey,
    move_xy,
    open_app,
    open_url,
    press_key,
    scroll,
    type_text,
)
from jarvis_core.operator.screen import describe_screen_with_model_fallback, take_screenshot
from jarvis_core.speech import speak_text

log = logging.getLogger("jarvis.operator.commands")


@dataclass(frozen=True)
class OperatorResult:
    handled: bool
    message: str = ""


def _numbers(text: str) -> list[int]:
    return [int(num) for num in re.findall(r"-?\d+", text)]


def _after(text: str, *markers: str) -> str:
    lowered = text.lower()
    for marker in markers:
        idx = lowered.find(marker)
        if idx != -1:
            return text[idx + len(marker) :].strip(" :,-")
    return ""


def _speak_and_return(message: str, speech: SpeechSettings) -> OperatorResult:
    log.info("Operator: %s", message)
    speak_text(speech, message)
    return OperatorResult(True, message)


def try_handle_operator_command(
    question: str,
    operator: OperatorSettings,
    conversation: ConversationSettings,
    speech: SpeechSettings,
) -> OperatorResult:
    if not operator.enabled:
        return OperatorResult(False)

    text = question.strip()
    lowered = text.lower()

    if any(phrase in lowered for phrase in ("take screenshot", "take a screenshot", "screen shot", "screenshot")):
        try:
            path = take_screenshot(operator)
            return _speak_and_return(f"Screenshot captured and saved to {path.name}.", speech)
        except Exception as exc:
            return _speak_and_return(f"I could not take a screenshot: {exc}", speech)

    if any(phrase in lowered for phrase in ("describe screen", "describe my screen", "what am i looking at", "what's on my screen", "read my screen", "look at my screen")):
        try:
            description = describe_screen_with_model_fallback(operator, conversation, text)
            return _speak_and_return(description, speech)
        except Exception as exc:
            return _speak_and_return(f"I could not describe the screen: {exc}", speech)

    if lowered.startswith("open "):
        target = _after(text, "open")
        if re.match(r"^(https?://)?[\w.-]+\.[a-z]{2,}", target, flags=re.I):
            return _speak_and_return(open_url(target, operator), speech)
        return _speak_and_return(open_app(target, operator), speech)

    if lowered.startswith("go to ") or lowered.startswith("open website "):
        url = _after(text, "go to", "open website")
        return _speak_and_return(open_url(url, operator), speech)

    if lowered.startswith("click"):
        nums = _numbers(text)
        if len(nums) >= 2:
            return _speak_and_return(click_xy(nums[0], nums[1], operator), speech)
        return _speak_and_return("Tell me the X and Y coordinates to click, for example: click 500 300.", speech)

    if lowered.startswith("move mouse") or lowered.startswith("move cursor"):
        nums = _numbers(text)
        if len(nums) >= 2:
            return _speak_and_return(move_xy(nums[0], nums[1], operator), speech)
        return _speak_and_return("Tell me the X and Y coordinates to move to, for example: move mouse 500 300.", speech)

    if lowered.startswith("scroll"):
        amount = 5
        if "down" in lowered:
            amount = -5
        elif "up" in lowered:
            amount = 5
        nums = _numbers(text)
        if nums:
            amount = nums[0]
            if "down" in lowered:
                amount = -abs(amount)
        return _speak_and_return(scroll(amount, operator), speech)

    if lowered.startswith("press "):
        rest = _after(text, "press")
        if "+" in rest:
            keys = [part.strip() for part in rest.split("+")]
            return _speak_and_return(hotkey(keys, operator), speech)
        words = rest.split()
        if len(words) > 1 and words[0].lower() in {"ctrl", "control", "shift", "alt", "win", "windows"}:
            aliases = {"control": "ctrl", "windows": "win"}
            keys = [aliases.get(word.lower(), word.lower()) for word in words]
            return _speak_and_return(hotkey(keys, operator), speech)
        return _speak_and_return(press_key(rest, operator), speech)

    if lowered.startswith("type ") or lowered.startswith("write "):
        content = _after(text, "type", "write")
        return _speak_and_return(type_text(content, operator), speech)

    return OperatorResult(False)
