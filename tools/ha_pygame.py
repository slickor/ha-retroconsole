#!/usr/bin/env python3
"""Launch the HA RetroConsole pygame UI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the repository root is on sys.path when running the script directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ha_client import load_config
from ui.app import HARetroApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HA RetroConsole: pygame Home Assistant UI.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path, require_favorites=True)
    app = HARetroApp(config, args.timeout, config_path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
