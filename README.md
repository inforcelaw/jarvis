# JARVIS Clap Core

This is a restart of the JARVIS project around the original **double-clap desktop trigger** idea.

Instead of one huge script that directly opens everything, the project now has a small modular core:

- microphone listener
- reusable double-clap detector
- safer action launcher
- `.env` based configuration
- dry-run mode for testing

The goal is to make this the base for a real desktop assistant later: clap to wake, then JARVIS can open the coding setup, run local tools, or eventually connect to a GUI/agent layer.

## Current behaviour

When a valid double clap is detected, JARVIS can:

- open Claude in Chrome
- open Cursor
- optionally open a startup URI such as Spotify
- optionally open Binance, but this is **off by default**

Text-to-speech and ElevenLabs were intentionally removed from this restart. We can add voice later once the core is stable.

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
  actions/
    launcher.py               # safe app/URL launching
  triggers/
    clap.py                   # reusable double-clap detector
```

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
- **Cursor does not open:** install Cursor or add the `cursor` command to PATH.
