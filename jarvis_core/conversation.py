from __future__ import annotations

from dataclasses import replace
import logging
import re
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from jarvis_core.ai import AIProviderError, ask_ai
from jarvis_core.config import ConversationSettings, SpeechSettings
from jarvis_core.speech import speak_text

log = logging.getLogger("jarvis.conversation")


def _write_wav(samples: list[np.ndarray], sample_rate: int, channels: int) -> Path:
    if samples:
        audio = np.concatenate(samples).reshape(-1)
    else:
        audio = np.zeros(int(sample_rate * 0.25), dtype=np.float32)

    pcm_i16 = np.clip(audio, -1.0, 1.0)
    pcm_i16 = (pcm_i16 * 32767).astype(np.int16)

    tmp = Path(tempfile.gettempdir()) / "jarvis_question.wav"
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_i16.tobytes())
    return tmp


def _rms(block: np.ndarray) -> float:
    data = block.reshape(-1).astype(np.float64)
    if data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(data**2)))


def _record_question_fixed(settings: ConversationSettings) -> Path:
    seconds = max(1.0, settings.listen_seconds)
    sample_rate = 16000
    channels = 1
    log.info("Listening for your question for %.1f seconds...", seconds)
    if settings.pre_listen_delay_s > 0:
        time.sleep(settings.pre_listen_delay_s)

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
    )
    sd.wait()
    return _write_wav([audio], sample_rate, channels)


def _record_question_vad(settings: ConversationSettings) -> Path:
    max_seconds = max(1.0, settings.listen_seconds)
    sample_rate = 16000
    channels = 1
    block_ms = 80
    block_size = int(sample_rate * block_ms / 1000)
    min_record_s = max(0.1, settings.vad_min_record_s)
    silence_s = max(0.2, settings.vad_silence_s)

    log.info(
        "Listening up to %.1fs; auto-stopping after %.2fs silence...",
        max_seconds,
        silence_s,
    )
    if settings.pre_listen_delay_s > 0:
        time.sleep(settings.pre_listen_delay_s)

    frames: list[np.ndarray] = []
    heard_speech = False
    speech_started_at: float | None = None
    last_voice_at: float | None = None
    started_at = time.monotonic()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        blocksize=block_size,
    ) as stream:
        while True:
            block, overflowed = stream.read(block_size)
            if overflowed:
                log.warning("Conversation input overflow; try a quieter device or larger block.")

            now = time.monotonic()
            elapsed = now - started_at
            level = _rms(block)

            if not heard_speech and level >= settings.vad_start_rms:
                heard_speech = True
                speech_started_at = now
                last_voice_at = now
                log.info("Speech detected; recording question...")

            if heard_speech:
                frames.append(block.copy())
                if level >= settings.vad_stop_rms:
                    last_voice_at = now

                recorded_s = now - (speech_started_at or now)
                silent_s = now - (last_voice_at or now)
                if recorded_s >= min_record_s and silent_s >= silence_s:
                    log.info("Question capture stopped after %.2fs of silence.", silent_s)
                    break
            elif elapsed >= max_seconds:
                log.info("No speech detected before timeout.")
                break

            if elapsed >= max_seconds:
                log.info("Question capture reached max %.1fs window.", max_seconds)
                break

    return _write_wav(frames, sample_rate, channels)


def _record_question(settings: ConversationSettings) -> Path:
    if settings.vad_enabled:
        return _record_question_vad(settings)
    return _record_question_fixed(settings)


def _transcribe_openai(path: Path, settings: ConversationSettings) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for microphone transcription.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install OpenAI support with: python -m pip install -r requirements.txt") from exc

    client = OpenAI(api_key=settings.openai_api_key)
    with path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=settings.transcribe_model,
            file=audio_file,
            response_format="text",
        )
    return str(transcript).strip()


def transcribe_question(settings: ConversationSettings) -> str:
    if settings.transcribe_provider != "openai":
        raise RuntimeError("Only OpenAI transcription is currently implemented.")
    audio_path = _record_question(settings)
    log.info("Transcribing question...")
    return _transcribe_openai(audio_path, settings)


def _normalise_phrase(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _wake_phrase_match(transcript: str, phrases: tuple[str, ...]) -> tuple[bool, str]:
    """Return (matched, remainder_after_wake_phrase)."""
    cleaned_words = _normalise_phrase(transcript).split()
    if not cleaned_words:
        return False, ""

    for phrase in phrases:
        phrase_words = _normalise_phrase(phrase).split()
        if not phrase_words:
            continue
        for i in range(0, len(cleaned_words) - len(phrase_words) + 1):
            if cleaned_words[i : i + len(phrase_words)] == phrase_words:
                remainder_words = cleaned_words[i + len(phrase_words) :]
                return True, " ".join(remainder_words).strip()
    return False, ""


def wait_for_wake_phrase(settings: ConversationSettings) -> str | None:
    """Listen for 'hey Jarvis'/'hey Javis' after the clap.

    Returns:
      - None if the wake phrase was not heard.
      - '' if the wake phrase was heard but no question followed.
      - remainder text when the user says: 'hey Jarvis, <question>'.
    """
    wake_settings = replace(
        settings,
        listen_seconds=settings.wake_listen_seconds,
        pre_listen_delay_s=min(settings.pre_listen_delay_s, 0.10),
        vad_min_record_s=min(settings.vad_min_record_s, 0.45),
        vad_silence_s=min(settings.vad_silence_s, 0.55),
    )

    attempts = max(1, settings.wake_retries)
    phrase_text = " / ".join(settings.wake_phrases)
    for attempt in range(1, attempts + 1):
        log.info("Armed. Say %r to continue. Attempt %d/%d.", phrase_text, attempt, attempts)
        try:
            transcript = transcribe_question(wake_settings)
        except Exception as exc:
            log.warning("Could not check wake phrase: %s", exc)
            return None

        if not transcript:
            log.info("Wake check heard nothing.")
            continue

        log.info("Wake check heard: %s", transcript)
        matched, remainder = _wake_phrase_match(transcript, settings.wake_phrases)
        if not matched:
            log.info("Wake phrase not detected; returning to clap listener.")
            continue

        log.info("Wake phrase accepted.")
        if settings.wake_use_remainder_as_question and remainder:
            log.info("Using wake phrase remainder as question: %s", remainder)
            return remainder
        return ""

    return None


def run_conversation_turn(conversation: ConversationSettings, speech: SpeechSettings) -> None:
    if not conversation.enabled:
        return

    question = ""
    if conversation.wake_after_clap_enabled:
        wake_remainder = wait_for_wake_phrase(conversation)
        if wake_remainder is None:
            return
        question = wake_remainder.strip()

    if not question:
        try:
            question = transcribe_question(conversation)
        except Exception as exc:
            log.warning("Could not transcribe question: %s", exc)
            return

    if not question:
        log.info("No question detected.")
        return

    log.info("You asked: %s", question)
    try:
        reply = ask_ai(question, conversation)
    except AIProviderError as exc:
        log.warning("AI response failed: %s", exc)
        return
    except Exception as exc:
        log.warning("Unexpected AI response error: %s", exc)
        return

    log.info("JARVIS [%s/%s]: %s", reply.provider, reply.model, reply.text)
    speak_text(speech, reply.text)
