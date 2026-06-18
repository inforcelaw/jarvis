from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path
import time

import numpy as np
import sounddevice as sd

from jarvis_core.ai import AIProviderError, ask_ai
from jarvis_core.config import ConversationSettings, SpeechSettings
from jarvis_core.speech import speak_text

log = logging.getLogger("jarvis.conversation")


def _record_question(settings: ConversationSettings) -> Path:
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

    pcm_i16 = np.clip(audio.reshape(-1), -1.0, 1.0)
    pcm_i16 = (pcm_i16 * 32767).astype(np.int16)

    tmp = Path(tempfile.gettempdir()) / "jarvis_question.wav"
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_i16.tobytes())
    return tmp


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
