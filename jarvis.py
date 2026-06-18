#!/usr/bin/env python3
"""Jarvis entrypoint.

This project now starts from the original double-clap script idea, but the code is
split into a small core so it can grow into a proper desktop assistant instead
of staying as one giant automation file.
"""

from __future__ import annotations

import sys

from jarvis_core.app import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
