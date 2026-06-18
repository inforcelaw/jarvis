from __future__ import annotations

import hashlib
import logging
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from jarvis_core.config import ROOT_DIR, SpeechSettings

log = logging.getLogger("jarvis.speech")


def _cache_dir(settings: SpeechSettings) -> Path:
    if settings.cache_dir:
        return Path(settings.cache_dir).expanduser().resolve()
    return ROOT_DIR / ".cache" / "jarvis_speech"


def _cache_path(settings: SpeechSettings) -> Path:
    key = "|".join(
        [
            settings.phrase,
            settings.elevenlabs_voice_id,
            settings.elevenlabs_model_id,
            settings.elevenlabs_output_format,
        ]
    ).encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()[:24]
    return _cache_dir(settings) / f"{digest}.wav"


def _pcm_rate(settings: SpeechSettings) -> int:
    if settings.elevenlabs_pcm_sample_rate:
        return settings.elevenlabs_pcm_sample_rate
    if settings.elevenlabs_output_format.startswith("pcm_"):
        try:
            return int(settings.elevenlabs_output_format.split("_", maxsplit=1)[1])
        except (ValueError, IndexError):
            pass
    return 24000


def _play_pcm_bytes(raw: bytes, sample_rate: int) -> bool:
    if not raw:
        return False
    try:
        pcm_i16 = np.frombuffer(raw, dtype=np.int16)
        pcm_f = pcm_i16.astype(np.float32) / 32768.0
        sd.play(pcm_f, sample_rate)
        sd.wait()
        return True
    except Exception as exc:
        log.warning("Could not play speech audio: %s", exc)
        return False


def _play_cached_wav(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            if channels != 1 or sample_width != 2:
                log.warning(
                    "Unsupported cached speech WAV: channels=%s sample_width=%s",
                    channels,
                    sample_width,
                )
                return False
            raw = wf.readframes(wf.getnframes())
    except (OSError, wave.Error) as exc:
        log.warning("Could not read cached speech audio: %s", exc)
        return False
    return _play_pcm_bytes(raw, sample_rate)


def _save_wav(path: Path, raw: bytes, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(raw)
        tmp.replace(path)
    except OSError:
        if tmp.is_file():
            tmp.unlink(missing_ok=True)
        raise


def speak_welcome(settings: SpeechSettings) -> None:
    """Speak the configured JARVIS welcome phrase through ElevenLabs.

    Failures are logged and never crash the clap listener.
    """
    if not settings.enabled:
        return
    if not settings.phrase:
        return
    if settings.after_actions_delay_s > 0:
        time.sleep(settings.after_actions_delay_s)

    if not settings.elevenlabs_voice_id:
        log.warning("Speech enabled but ELEVENLABS_VOICE_ID is missing.")
        return

    cache_path = _cache_path(settings)
    if settings.cache_enabled and cache_path.is_file():
        log.info("Playing welcome speech from cache: %s", cache_path)
        if _play_cached_wav(cache_path):
            return
        log.warning("Cached speech failed, requesting fresh audio.")

    if not settings.elevenlabs_api_key:
        log.warning("Speech enabled but ELEVENLABS_API_KEY is missing.")
        return

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        log.warning("Install ElevenLabs support with: python -m pip install -r requirements.txt")
        return

    try:
        client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        chunks = client.text_to_speech.convert(
            voice_id=settings.elevenlabs_voice_id,
            text=settings.phrase,
            model_id=settings.elevenlabs_model_id,
            output_format=settings.elevenlabs_output_format,
        )
        raw = b"".join(chunks)
    except Exception as exc:
        log.warning("ElevenLabs speech failed: %s", exc)
        return

    sample_rate = _pcm_rate(settings)
    if settings.cache_enabled:
        try:
            _save_wav(cache_path, raw, sample_rate)
            log.info("Saved welcome speech cache: %s", cache_path)
        except OSError as exc:
            log.warning("Could not save speech cache: %s", exc)

    _play_pcm_bytes(raw, sample_rate)
