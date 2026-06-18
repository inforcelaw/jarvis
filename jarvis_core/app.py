from __future__ import annotations

import argparse
import logging
import threading

import sounddevice as sd

from jarvis_core.actions.launcher import run_startup_actions
from jarvis_core.audio import rms_mono
from jarvis_core.config import load_settings
from jarvis_core.triggers.clap import DoubleClapDetector


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)

    settings = load_settings()
    if args.dry_run:
        # Keep dataclass frozen by creating a shallow replacement of actions.
        object.__setattr__(settings.actions, "dry_run", True)

    clap_settings = settings.clap
    detector = DoubleClapDetector(clap_settings)

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

    try:
        with sd.InputStream(
            samplerate=clap_settings.sample_rate,
            channels=clap_settings.channels,
            dtype="float32",
            blocksize=clap_settings.block_size,
        ) as stream:
            while True:
                data, overflowed = stream.read(clap_settings.block_size)
                if overflowed:
                    log.warning("Input overflow; try increasing JARVIS_BLOCK_MS.")

                level = rms_mono(data)
                event = detector.update(level)
                if event is None:
                    continue

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
    except KeyboardInterrupt:
        log.info("JARVIS clap core stopped.")
        return 0
    except sd.PortAudioError as exc:
        log.error("Audio error: %s", exc)
        log.error("Try changing JARVIS_SAMPLE_RATE to 48000 or check microphone permissions.")
        return 1
