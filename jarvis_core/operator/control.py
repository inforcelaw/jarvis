from __future__ import annotations

import logging
import re
import subprocess
import sys
import webbrowser

from jarvis_core.config import OperatorSettings

log = logging.getLogger("jarvis.operator.control")


_APP_COMMANDS: dict[str, list[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "chrome": ["chrome.exe"],
    "cursor": ["cursor"],
}


def _pyautogui():
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError("Install screen control support with: python -m pip install -r requirements.txt") from exc
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9:/._ -]+", " ", text.lower()).strip()


def open_app(name: str, settings: OperatorSettings) -> str:
    if not settings.allow_open_apps:
        return "Opening apps is disabled. Set JARVIS_OPERATOR_ALLOW_OPEN_APPS=true."

    app = _normalise(name).split()[0] if name.strip() else ""
    allowed = {item.lower() for item in settings.allowed_apps}
    if app not in allowed:
        return f"I cannot open {app!r}; it is not in JARVIS_OPERATOR_ALLOWED_APPS."

    command = _APP_COMMANDS.get(app)
    if not command:
        return f"I do not have an app mapping for {app!r} yet."

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(command, **kwargs)
        return f"Opening {app}."
    except OSError as exc:
        return f"I could not open {app}: {exc}"


def open_url(url: str, settings: OperatorSettings) -> str:
    if not settings.allow_urls:
        return "Opening URLs is disabled. Set JARVIS_OPERATOR_ALLOW_URLS=true."
    url = url.strip()
    if not url:
        return "No URL was provided."
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."


def click_xy(x: int, y: int, settings: OperatorSettings) -> str:
    if not settings.allow_mouse:
        return "Mouse control is disabled. Set JARVIS_OPERATOR_ALLOW_MOUSE=true to allow clicking."
    pg = _pyautogui()
    pg.click(x=x, y=y)
    return f"Clicked {x}, {y}."


def move_xy(x: int, y: int, settings: OperatorSettings) -> str:
    if not settings.allow_mouse:
        return "Mouse control is disabled. Set JARVIS_OPERATOR_ALLOW_MOUSE=true to allow moving."
    pg = _pyautogui()
    pg.moveTo(x, y, duration=0.1)
    return f"Moved mouse to {x}, {y}."


def scroll(amount: int, settings: OperatorSettings) -> str:
    if not settings.allow_mouse:
        return "Mouse control is disabled. Set JARVIS_OPERATOR_ALLOW_MOUSE=true to allow scrolling."
    pg = _pyautogui()
    pg.scroll(amount)
    return "Scrolled."


def press_key(key: str, settings: OperatorSettings) -> str:
    if not settings.allow_keyboard:
        return "Keyboard control is disabled. Set JARVIS_OPERATOR_ALLOW_KEYBOARD=true to allow key presses."
    key = _normalise(key).replace(" ", "")
    if not key:
        return "No key was provided."
    pg = _pyautogui()
    pg.press(key)
    return f"Pressed {key}."


def hotkey(keys: list[str], settings: OperatorSettings) -> str:
    if not settings.allow_keyboard:
        return "Keyboard control is disabled. Set JARVIS_OPERATOR_ALLOW_KEYBOARD=true to allow hotkeys."
    cleaned = [_normalise(key).replace(" ", "") for key in keys if key.strip()]
    if not cleaned:
        return "No hotkey was provided."
    pg = _pyautogui()
    pg.hotkey(*cleaned)
    return f"Pressed {' + '.join(cleaned)}."


def type_text(text: str, settings: OperatorSettings) -> str:
    if not settings.allow_typing:
        return "Typing is disabled. Set JARVIS_OPERATOR_ALLOW_TYPING=true to allow text entry."
    if not settings.allow_keyboard:
        return "Keyboard control is disabled. Set JARVIS_OPERATOR_ALLOW_KEYBOARD=true to allow typing."
    text = text.strip()
    if not text:
        return "No text was provided."
    try:
        import pyperclip
        pyperclip.copy(text)
        pg = _pyautogui()
        pg.hotkey("ctrl", "v")
    except Exception:
        pg = _pyautogui()
        pg.write(text, interval=0.005)
    return "Typed the requested text."
