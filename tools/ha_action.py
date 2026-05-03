#!/usr/bin/env python3
"""Call simple Home Assistant services with no external dependencies."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ha_client import SUPPORTED_ACTIONS, call_service, entity_domain, load_config, resolve_action


def require_action(entity_id: str, action: str) -> tuple[str, str]:
    resolved = resolve_action(entity_id, action)
    domain = entity_domain(entity_id)
    if resolved is not None:
        return resolved
    if domain not in SUPPORTED_ACTIONS:
        supported = ", ".join(sorted(SUPPORTED_ACTIONS))
        raise SystemExit(f"Unsupported entity domain '{domain}'. Supported: {supported}")
    allowed = ", ".join(sorted(SUPPORTED_ACTIONS[domain]))
    raise SystemExit(f"Unsupported action '{action}' for {domain}. Allowed: {allowed}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call a Home Assistant service.")
    parser.add_argument("entity_id", help="Entity to control, for example light.kitchen.")
    parser.add_argument(
        "action",
        nargs="?",
        default="auto",
        help="Action to run: auto, toggle, turn_on, or turn_off.",
    )
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    parser.add_argument("--yes", action="store_true", help="Actually call the service.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    domain, service = require_action(args.entity_id, args.action)

    print(f"Entity:  {args.entity_id}")
    print(f"Service: {domain}.{service}")

    if not args.yes:
        print()
        print("Dry run only. Add --yes to actually call this service.")
        return 0

    result = call_service(
        config["base_url"],
        config["token"],
        domain,
        service,
        args.entity_id,
        args.timeout,
    )
    changed = len(result) if isinstance(result, list) else 0
    print(f"Done. Home Assistant returned {changed} changed state(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
