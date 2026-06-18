from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import webbrowser

from jarvis_core.config import ActionSettings

log = logging.getLogger("jarvis.actions")


def _popen_hidden(args: list[str]) -> None:
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(args, **kwargs)


def open_uri(uri: str, *, dry_run: bool = False) -> None:
    uri = uri.strip()
    if not uri:
        return
    if dry_run:
        log.info("DRY RUN: would open URI: %s", uri)
        return
    try:
        if sys.platform == "win32":
            os.startfile(uri)  # type: ignore[attr-defined]
        else:
            webbrowser.open(uri)
    except OSError as exc:
        log.warning("Could not open URI %s: %s", uri, exc)


def chrome_executable() -> str | None:
    if sys.platform == "win32":
        for base in (
            os.environ.get("ProgramFiles", r"C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ):
            if not base:
                continue
            path = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(path):
                return path
    return shutil.which("google-chrome") or shutil.which("chrome")


def open_in_chrome(url: str, *, label: str, dry_run: bool = False) -> None:
    url = url.strip()
    if not url:
        return
    chrome = chrome_executable()
    if dry_run:
        log.info("DRY RUN: would open %s in Chrome: %s", label, url)
        return
    try:
        if chrome:
            _popen_hidden([chrome, "--new-window", url])
        else:
            log.warning("Chrome not found; opening %s in default browser.", label)
            webbrowser.open(url)
    except OSError as exc:
        log.warning("Could not open %s: %s", label, exc)


def cursor_executable() -> str | None:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        for sub in ("Programs\\cursor\\Cursor.exe", "Programs\\Cursor\\Cursor.exe"):
            if local:
                path = os.path.join(local, *sub.split("\\"))
                if os.path.isfile(path):
                    return path
    return shutil.which("cursor")


def open_cursor(*, new_window: bool, dry_run: bool = False) -> None:
    exe = cursor_executable()
    if dry_run:
        log.info("DRY RUN: would open Cursor%s", " new window" if new_window else "")
        return
    if not exe:
        log.warning("Could not find Cursor. Install Cursor or add `cursor` to PATH.")
        return
    try:
        args = [exe, "-n"] if new_window else [exe]
        _popen_hidden(args)
    except OSError as exc:
        log.warning("Could not open Cursor: %s", exc)


def run_startup_actions(settings: ActionSettings) -> None:
    """Run the configured startup action preset.

    This is deliberately much safer than the original script: Binance defaults
    off, there is no TTS yet, and everything can be tested with dry-run mode.
    """
    if settings.play_startup_uri and settings.startup_uri:
        open_uri(settings.startup_uri, dry_run=settings.dry_run)
    if settings.open_claude:
        open_in_chrome(settings.claude_url, label="Claude", dry_run=settings.dry_run)
    if settings.open_binance:
        open_in_chrome(settings.binance_url, label="Binance BTC", dry_run=settings.dry_run)
    if settings.open_cursor:
        open_cursor(new_window=settings.cursor_new_window, dry_run=settings.dry_run)
