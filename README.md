# JARVIS Clap Core

This is a restart of the JARVIS project around the original **double-clap desktop trigger** idea.

Instead of one huge script that directly opens everything, the project now has a small modular core:

- microphone listener
- reusable double-clap detector
- safer action launcher
- optional ElevenLabs welcome/answer speech
- voice conversation mode
- AI provider router
- `.env` based configuration
- dry-run mode for testing

The goal is to make this the base for a real desktop assistant: clap to wake, ask a question, JARVIS transcribes it, routes it to the best configured AI, and speaks the answer back.

## Current behaviour

When a valid double clap is detected, JARVIS can:

- open Claude in Chrome
- open Cursor
- optionally open a startup URI such as Spotify
- optionally speak a welcome line with ElevenLabs
- listen for a spoken question
- transcribe that question with OpenAI speech-to-text
- route the question to OpenAI, Claude, Gemini, or Ollama
- speak the AI answer back with the configured ElevenLabs voice

Speech is isolated in `jarvis_core/speech.py`, AI routing is in `jarvis_core/ai.py`, and the mic conversation turn is in `jarvis_core/conversation.py`.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configure

Copy the example environment file:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Then edit `.env`.

Useful settings:

| Variable | Purpose |
| --- | --- |
| `JARVIS_DRY_RUN` | When `true`, clap detection only logs actions. |
| `JARVIS_SPIKE_RATIO` | Higher = fewer false triggers. Lower = more sensitive. |
| `JARVIS_MAX_DOUBLE_GAP_S` | Maximum time between the two claps. |
| `JARVIS_OPEN_CLAUDE` | Opens Claude after the clap trigger. |
| `JARVIS_OPEN_CURSOR` | Opens Cursor after the clap trigger. |
| `JARVIS_PLAY_STARTUP_URI` | Enables opening a custom URI such as Spotify. |
| `JARVIS_SPEECH_ENABLED` | Enables/disables ElevenLabs welcome and answer speech. |
| `JARVIS_WELCOME_PHRASE` | The line JARVIS says after the clap trigger. |
| `ELEVENLABS_API_KEY` | Required for fresh ElevenLabs speech generation. |
| `ELEVENLABS_VOICE_ID` | Required voice ID for ElevenLabs speech. |
| `JARVIS_CONVERSATION_ENABLED` | Enables listen/transcribe/respond mode. |
| `JARVIS_LISTEN_SECONDS` | How long JARVIS records your question after the clap. |
| `JARVIS_AI_MODE` | `auto`, `openai`, `anthropic`, `gemini`, or `ollama`. |
| `OPENAI_API_KEY` | Required for transcription and OpenAI responses. |
| `ANTHROPIC_API_KEY` | Enables Claude routing. |
| `GOOGLE_API_KEY` | Enables Gemini routing. |
| `JARVIS_OLLAMA_ENABLED` | Enables local Ollama routing. |

## AI routing

`JARVIS_AI_MODE=auto` picks between configured providers:

- coding/debug/Discord/repo questions prefer Claude, then OpenAI
- quick/simple summary questions prefer Gemini, then OpenAI
- local/offline questions prefer Ollama if enabled
- general questions prefer OpenAI first

You can force a provider by setting:

```env
JARVIS_AI_MODE=openai
```

or:

```env
JARVIS_AI_MODE=anthropic
```

## Run

Test clap detection safely first:

```bash
python jarvis.py --dry-run
```

Run normally:

```bash
python jarvis.py
```

Run without conversation mode:

```bash
python jarvis.py --no-conversation
```

Stop with `Ctrl+C`.

## Project structure

```txt
jarvis.py                     # small launcher
jarvis_core/
  ai.py                       # AI provider router
  app.py                      # main microphone loop
  audio.py                    # RMS audio helpers
  config.py                   # .env settings
  conversation.py             # record, transcribe, ask AI, speak answer
  speech.py                   # optional ElevenLabs welcome/answer speech
  actions/
    launcher.py               # safe app/URL launching
  triggers/
    clap.py                   # reusable double-clap detector
```

## Speech notes

Speech uses ElevenLabs PCM output and caches generated WAV files under `.cache/jarvis_speech/` by default. If the phrase, voice, model, or output format changes, JARVIS generates a new cached file.

If speech is enabled but `ELEVENLABS_API_KEY` or `ELEVENLABS_VOICE_ID` is missing, the listener keeps running and logs a warning instead of crashing.

## Conversation notes

Conversation mode currently records a fixed window after the clap trigger. Start with `JARVIS_LISTEN_SECONDS=7.0`, then increase it if your questions are getting cut off.

OpenAI is currently used for transcription. The answer can be routed to OpenAI, Claude, Gemini, or Ollama depending on your settings.

## Troubleshooting

- **No reaction to claps:** lower `JARVIS_SPIKE_RATIO` slightly.
- **False triggers:** raise `JARVIS_SPIKE_RATIO` or `JARVIS_MIN_RMS`.
- **Audio errors:** try `JARVIS_SAMPLE_RATE=48000` or check microphone permissions.
- **No speech:** set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`, then restart.
- **No transcription:** set `OPENAI_API_KEY`, then restart.
- **No AI answer:** configure at least one provider key or enable Ollama.
- **Cursor does not open:** install Cursor or add the `cursor` command to PATH.
