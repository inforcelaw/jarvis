from __future__ import annotations

import argparse
from dataclasses import replace
import logging
import threading

import sounddevice as sd

from jarvis_core.actions.launcher import run_startup_actions
from jarvis_core.audio import rms_mono
from jarvis_core.config import load_settings
from jarvis_core.conversation import run_conversation_turn
from jarvis_core.speech import speak_welcome
from jarvis_core.triggers.clap import ClapEvent, DoubleClapDetector


log = logging.getLogger("jarvis")


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jarvis clap-core assistant launcher")
    parser.add_argument("--dry-run", action="store_true", help="Detect claps but only log actions")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-conversation", action="store_true", help="Disable listen/transcribe/respond mode")
    return parser


def wait_for_double_clap(settings, detector: DoubleClapDetector) -> ClapEvent:
    """Open the microphone only while listening for the wake clap.

    The stream is closed before conversation mode records the user's question.
    That avoids fighting over the same mic device on Windows.
    """
    with sd.InputStream(
        samplerate=settings.sample_rate,
        channels=settings.channels,
        dtype="float32",
        blocksize=settings.block_size,
    ) as stream:
        while True:
            data, overflowed = stream.read(settings.block_size)
            if overflowed:
                log.warning("Input overflow; try increasing JARVIS_BLOCK_MS.")

            level = rms_mono(data)
            event = detector.update(level)
            if event is not None:
                return event


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)

    settings = load_settings()
    if args.dry_run:
        settings = replace(settings, actions=replace(settings.actions, dry_run=True))
    if args.no_conversation:
        settings = replace(settings, conversation=replace(settings.conversation, enabled=False))

    clap_settings = settings.clap
    detector = DoubleClapDetector(clap_settings)
    welcome_has_played = False

    log.info("JARVIS clap core online.")
    log.info(
        "Listening for double clap: %.2f-%.2fs apart | rate=%d | block=%dms | spike_ratio=%.1f",
        clap_settings.min_double_gap_s,
        clap_settings.max_double_gap_s,
        clap_settings.sample_rate,
        clap_settings.block_ms,
        clap_settings.spike_ratio,
    )
    if settings.actions.dry_run:
        log.info("Dry-run mode enabled. Actions will be logged only.")
    if settings.speech.enabled:
        log.info("Speech enabled for welcome/answers.")
    if settings.speech.welcome_enabled:
        log.info(
            "Welcome speech enabled%s.",
            " and set to run once" if settings.speech.speak_once else "",
        )
    if settings.conversation.enabled:
        log.info("Conversation mode enabled. JARVIS will listen after the clap trigger.")

    try:
        while True:
            event = wait_for_double_clap(clap_settings, detector)
            log.info(
                "Double clap detected: gap=%.3fs rms=%.5f noise_floor=%.5f threshold=%.5f",
                event.gap_s,
                event.level,
                event.noise_floor,
                event.threshold,
            )

            threading.Thread(
                target=run_startup_actions,
                args=(settings.actions,),
                daemon=True,
            ).start()

            welcome_allowed_now = (
                settings.speech.welcome_before_conversation or not settings.conversation.enabled
            )
            should_speak_welcome = (
                settings.speech.enabled
                and settings.speech.welcome_enabled
                and welcome_allowed_now
                and (not settings.speech.speak_once or not welcome_has_played)
            )
            if should_speak_welcome:
                welcome_has_played = True
                speak_welcome(settings.speech)

            if settings.conversation.enabled:
                run_conversation_turn(settings.conversation, settings.speech)

            log.info("Returning to clap listener.")
    except KeyboardInterrupt:
        log.info("JARVIS clap core stopped.")
        return 0
    except sd.PortAudioError as exc:
        log.error("Audio error: %s", exc)
        log.error("Try changing JARVIS_SAMPLE_RATE to 48000 or check microphone permissions.")
        return 1
