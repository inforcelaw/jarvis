from __future__ import annotations

import logging
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


def run_conversation_turn(conversation: ConversationSettings, speech: SpeechSettings) -> None:
    if not conversation.enabled:
        return

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
