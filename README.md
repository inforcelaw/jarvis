# JARVIS Clap Core

This is a restart of the JARVIS project around the original **double-clap desktop trigger** idea.

Instead of one huge script that directly opens everything, the project now has a small modular core:

- microphone listener
- reusable double-clap detector
- "hey Jarvis" wake phrase after clapping
- safer action launcher
- optional ElevenLabs welcome/answer speech
- voice conversation mode
- AI provider router
- local operator/screen-control tools
- `.env` based configuration
- dry-run mode for testing

The goal is to make this the base for a real desktop assistant: clap to arm, say "hey Jarvis", ask a question or screen command, then JARVIS responds or performs an allowed local action.

## Current behaviour

When a valid double clap is detected, JARVIS can:

- open Claude in Chrome
- open Cursor
- optionally open a startup URI such as Spotify
- wait for "hey Jarvis" or "hey Javis"
- listen for a spoken question
- transcribe that question with OpenAI speech-to-text
- route the question to OpenAI, Claude, Gemini, or Ollama
- speak the AI answer back with the configured ElevenLabs voice
- take screenshots
- describe the current screen using an OpenAI vision-capable model
- open allowed apps or URLs
- optionally control mouse, keyboard, and typing when enabled in `.env`

Speech is isolated in `jarvis_core/speech.py`, AI routing is in `jarvis_core/ai.py`, conversation is in `jarvis_core/conversation.py`, and screen controls live under `jarvis_core/operator/`.

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
| `JARVIS_WAKE_AFTER_CLAP_ENABLED` | Requires "hey Jarvis" after the clap. |
| `JARVIS_WAKE_PHRASES` | Wake phrases, default `hey jarvis,hey javis`. |
| `JARVIS_CONVERSATION_ENABLED` | Enables listen/transcribe/respond mode. |
| `JARVIS_AI_MODE` | `auto`, `openai`, `anthropic`, `gemini`, or `ollama`. |
| `OPENAI_API_KEY` | Required for transcription, OpenAI replies, and screen description. |
| `ELEVENLABS_API_KEY` | Required for fresh ElevenLabs speech generation. |
| `ELEVENLABS_VOICE_ID` | Required voice ID for ElevenLabs speech. |
| `JARVIS_OPERATOR_ENABLED` | Enables local screen/operator commands. |
| `JARVIS_OPERATOR_ALLOW_MOUSE` | Enables click/move/scroll commands. Default `false`. |
| `JARVIS_OPERATOR_ALLOW_KEYBOARD` | Enables key/hotkey commands. Default `false`. |
| `JARVIS_OPERATOR_ALLOW_TYPING` | Enables spoken typing commands. Default `false`. |

## Voice examples

```txt
Double clap
"hey Jarvis, describe my screen"
```

```txt
Double clap
"hey Jarvis, take a screenshot"
```

```txt
Double clap
"hey Jarvis, open cursor"
```

```txt
Double clap
"hey Jarvis"
JARVIS listens again
"what is this error on my screen"
```

Mouse and keyboard commands are disabled by default. To enable them:

```env
JARVIS_OPERATOR_ALLOW_MOUSE=true
JARVIS_OPERATOR_ALLOW_KEYBOARD=true
JARVIS_OPERATOR_ALLOW_TYPING=true
```

Then commands like these become available:

```txt
"hey Jarvis, click 500 300"
"hey Jarvis, press ctrl l"
"hey Jarvis, type hello world"
"hey Jarvis, scroll down"
```

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
  conversation.py             # wake phrase, record, transcribe, route commands
  speech.py                   # optional ElevenLabs welcome/answer speech
  actions/
    launcher.py               # safe app/URL launching
  operator/
    commands.py               # voice command parser
    control.py                # mouse, keyboard, app, URL helpers
    screen.py                 # screenshots and screen descriptions
  triggers/
    clap.py                   # reusable double-clap detector
```

## Speech notes

Speech uses ElevenLabs PCM output and caches generated WAV files under `.cache/jarvis_speech/` by default. If the phrase, voice, model, or output format changes, JARVIS generates a new cached file.

If speech is enabled but `ELEVENLABS_API_KEY` or `ELEVENLABS_VOICE_ID` is missing, the listener keeps running and logs a warning instead of crashing.

## Conversation notes

Conversation mode uses voice activity detection so it stops recording after you finish speaking instead of always waiting the full window.

OpenAI is currently used for transcription. The answer can be routed to OpenAI, Claude, Gemini, or Ollama depending on your settings.

## Operator notes

Operator mode is intentionally gated. Screenshots and screen description are available by default. Mouse, keyboard, and typing require explicit `.env` switches.

`pyautogui` fail-safe is enabled: moving your mouse to a screen corner can interrupt runaway automation.

## Troubleshooting

- **No reaction to claps:** lower `JARVIS_SPIKE_RATIO` slightly.
- **False triggers:** raise `JARVIS_SPIKE_RATIO` or `JARVIS_MIN_RMS`.
- **Wake phrase missed:** increase `JARVIS_WAKE_LISTEN_SECONDS` or add phrases to `JARVIS_WAKE_PHRASES`.
- **Audio errors:** try `JARVIS_SAMPLE_RATE=48000` or check microphone permissions.
- **No speech:** set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`, then restart.
- **No transcription:** set `OPENAI_API_KEY`, then restart.
- **No screen description:** set `OPENAI_API_KEY` and keep `JARVIS_OPERATOR_DESCRIBE_SCREEN_ENABLED=true`.
- **Mouse or typing is blocked:** enable the relevant `JARVIS_OPERATOR_ALLOW_*` setting.
- **Cursor does not open:** install Cursor or add the `cursor` command to PATH.
