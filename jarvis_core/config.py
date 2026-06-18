from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ClapSettings:
    sample_rate: int = _env_int("JARVIS_SAMPLE_RATE", 44100)
    block_ms: int = _env_int("JARVIS_BLOCK_MS", 40)
    channels: int = _env_int("JARVIS_CHANNELS", 1)
    spike_ratio: float = _env_float("JARVIS_SPIKE_RATIO", 7.0)
    cooldown_s: float = _env_float("JARVIS_COOLDOWN_S", 0.45)
    min_double_gap_s: float = _env_float("JARVIS_MIN_DOUBLE_GAP_S", 0.05)
    max_double_gap_s: float = _env_float("JARVIS_MAX_DOUBLE_GAP_S", 0.35)
    retrigger_ratio: float = _env_float("JARVIS_RETRIGGER_RATIO", 0.55)
    noise_floor_alpha: float = _env_float("JARVIS_NOISE_FLOOR_ALPHA", 0.992)
    min_rms: float = _env_float("JARVIS_MIN_RMS", 0.012)
    quiet_gate_mult: float = _env_float("JARVIS_QUIET_GATE_MULT", 2.2)

    @property
    def block_size(self) -> int:
        return max(1, int(self.sample_rate * self.block_ms / 1000))


@dataclass(frozen=True)
class ActionSettings:
    dry_run: bool = _env_bool("JARVIS_DRY_RUN", False)
    play_startup_uri: bool = _env_bool("JARVIS_PLAY_STARTUP_URI", True)
    startup_uri: str = os.environ.get("JARVIS_STARTUP_URI", "").strip()
    open_claude: bool = _env_bool("JARVIS_OPEN_CLAUDE", True)
    claude_url: str = os.environ.get("JARVIS_CLAUDE_URL", "https://claude.ai/new").strip()
    open_cursor: bool = _env_bool("JARVIS_OPEN_CURSOR", True)
    cursor_new_window: bool = _env_bool("JARVIS_CURSOR_NEW_WINDOW", False)
    open_binance: bool = _env_bool("JARVIS_OPEN_BINANCE", False)
    binance_url: str = os.environ.get("JARVIS_BINANCE_URL", "https://www.binance.com/en/trade/BTC_USDT").strip()


@dataclass(frozen=True)
class SpeechSettings:
    enabled: bool = _env_bool("JARVIS_SPEECH_ENABLED", True)
    speak_once: bool = _env_bool("JARVIS_SPEAK_ONCE", True)
    after_actions_delay_s: float = _env_float("JARVIS_SPEECH_DELAY_S", 1.0)
    phrase: str = os.environ.get(
        "JARVIS_WELCOME_PHRASE",
        "Welcome home sir. Systems are online.",
    ).strip()
    cache_enabled: bool = _env_bool("JARVIS_SPEECH_CACHE_ENABLED", True)
    cache_dir: str = os.environ.get("JARVIS_SPEECH_CACHE_DIR", "").strip()
    elevenlabs_api_key: str = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    elevenlabs_voice_id: str = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    elevenlabs_model_id: str = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
    elevenlabs_output_format: str = os.environ.get("ELEVENLABS_OUTPUT_FORMAT", "pcm_24000").strip()
    elevenlabs_pcm_sample_rate: int = _env_int("ELEVENLABS_PCM_SAMPLE_RATE", 24000)


@dataclass(frozen=True)
class ConversationSettings:
    enabled: bool = _env_bool("JARVIS_CONVERSATION_ENABLED", True)
    listen_seconds: float = _env_float("JARVIS_LISTEN_SECONDS", 7.0)
    pre_listen_delay_s: float = _env_float("JARVIS_PRE_LISTEN_DELAY_S", 0.4)
    transcribe_provider: str = os.environ.get("JARVIS_TRANSCRIBE_PROVIDER", "openai").strip().lower()
    transcribe_model: str = os.environ.get("JARVIS_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe").strip()
    ai_mode: str = os.environ.get("JARVIS_AI_MODE", "auto").strip().lower()
    max_response_chars: int = _env_int("JARVIS_MAX_RESPONSE_CHARS", 900)
    system_prompt: str = os.environ.get(
        "JARVIS_SYSTEM_PROMPT",
        "You are JARVIS: calm, capable, precise, lightly witty, and useful. "
        "Answer like a loyal desktop assistant. Keep replies brief unless detail is needed.",
    ).strip()

    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "").strip()
    openai_model: str = os.environ.get("JARVIS_OPENAI_MODEL", "gpt-5.5-mini").strip()

    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    anthropic_model: str = os.environ.get("JARVIS_ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()

    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "").strip()
    gemini_model: str = os.environ.get("JARVIS_GEMINI_MODEL", "gemini-3.5-flash").strip()

    ollama_enabled: bool = _env_bool("JARVIS_OLLAMA_ENABLED", False)
    ollama_url: str = os.environ.get("JARVIS_OLLAMA_URL", "http://localhost:11434/api/chat").strip()
    ollama_model: str = os.environ.get("JARVIS_OLLAMA_MODEL", "llama3.2").strip()


@dataclass(frozen=True)
class AppSettings:
    clap: ClapSettings = ClapSettings()
    actions: ActionSettings = ActionSettings()
    speech: SpeechSettings = SpeechSettings()
    conversation: ConversationSettings = ConversationSettings()


def load_settings() -> AppSettings:
    return AppSettings()
