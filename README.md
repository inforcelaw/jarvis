# JARVIS Clap Core

This is a restart of the JARVIS project around the original **double-clap desktop trigger** idea.

Instead of one huge script that directly opens everything, the project now has a small modular core:

- microphone listener
- reusable double-clap detector
- safer action launcher
- optional ElevenLabs welcome speech
- `.env` based configuration
- dry-run mode for testing

The goal is to make this the base for a real desktop assistant later: clap to wake, then JARVIS can open the coding setup, speak a welcome line, run local tools, or eventually connect to a GUI/agent layer.

## Current behaviour

When a valid double clap is detected, JARVIS can:

- open Claude in Chrome
- open Cursor
- optionally open a startup URI such as Spotify
- optionally speak a welcome line with ElevenLabs
- optionally open Binance, but this is **off by default**

Speech is back in the restart, but it is isolated in `jarvis_core/speech.py` so it can be changed or disabled without touching the clap detector.

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
| `JARVIS_STARTUP_URI` | The URL/URI to open when startup URI is enabled. |
| `JARVIS_SPEECH_ENABLED` | Enables/disables ElevenLabs welcome speech. |
| `JARVIS_SPEAK_ONCE` | If `true`, speaks only once per run. |
| `JARVIS_WELCOME_PHRASE` | The line JARVIS says after the clap trigger. |
| `ELEVENLABS_API_KEY` | Required for fresh ElevenLabs speech generation. |
| `ELEVENLABS_VOICE_ID` | Required voice ID for ElevenLabs speech. |
| `JARVIS_OPEN_BINANCE` | Off by default. Enables Binance launch only when deliberately set. |

## Run

Test safely first:

```bash
python jarvis.py --dry-run
```

Run normally:

```bash
python jarvis.py
```

Stop with `Ctrl+C`.

## Project structure

```txt
jarvis.py                     # small launcher
jarvis_core/
  app.py                      # main microphone loop
  audio.py                    # RMS audio helpers
  config.py                   # .env settings
  speech.py                   # optional ElevenLabs welcome speech
  actions/
    launcher.py               # safe app/URL launching
  triggers/
    clap.py                   # reusable double-clap detector
```

## Speech notes

Speech uses ElevenLabs PCM output and caches generated WAV files under `.cache/jarvis_speech/` by default. If the phrase, voice, model, or output format changes, JARVIS generates a new cached file.

If speech is enabled but `ELEVENLABS_API_KEY` or `ELEVENLABS_VOICE_ID` is missing, the listener keeps running and logs a warning instead of crashing.

## Next roadmap

### v0.2 — Setup Launcher

- improve Cursor focus instead of only launch
- bring back multi-monitor Chrome placement cleanly
- add preset profiles: coding, school, hosting, RP/server work

### v0.3 — Local JARVIS Console

- terminal HUD view
- live logs that feel like real Discord/Python bot logs
- action queue and approval cards

### v0.4 — Agent Layer

- connect clap trigger to a local assistant loop
- let JARVIS create/fix code projects inside a workspace
- add optional Discord/coding assistant mode

## Troubleshooting

- **No reaction to claps:** lower `JARVIS_SPIKE_RATIO` slightly.
- **False triggers:** raise `JARVIS_SPIKE_RATIO` or `JARVIS_MIN_RMS`.
- **Audio errors:** try `JARVIS_SAMPLE_RATE=48000` or check microphone permissions.
- **No speech:** set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`, then restart.
- **Cursor does not open:** install Cursor or add the `cursor` command to PATH.
