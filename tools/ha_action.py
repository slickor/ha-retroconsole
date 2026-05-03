#!/usr/bin/env python3
"""Call simple Home Assistant services with no external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SUPPORTED_ACTIONS = {
    "light": {"toggle", "turn_on", "turn_off"},
    "switch": {"toggle", "turn_on", "turn_off"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
}


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"Config not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Config is not valid JSON: {exc}")

    base_url = str(config.get("base_url", "")).strip().rstrip("/")
    token = str(config.get("token", "")).strip()

    if not base_url:
        raise SystemExit("Missing config value: base_url")
    if not token or token == "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE":
        raise SystemExit("Missing config value: token")

    config["base_url"] = base_url
    config["token"] = token
    return config


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def resolve_action(entity_id: str, action: str) -> tuple[str, str]:
    domain = entity_domain(entity_id)
    if domain not in SUPPORTED_ACTIONS:
        supported = ", ".join(sorted(SUPPORTED_ACTIONS))
        raise SystemExit(f"Unsupported entity domain '{domain}'. Supported: {supported}")

    if action == "auto":
        action = "toggle" if "toggle" in SUPPORTED_ACTIONS[domain] else "turn_on"

    if action not in SUPPORTED_ACTIONS[domain]:
        allowed = ", ".join(sorted(SUPPORTED_ACTIONS[domain]))
        raise SystemExit(f"Unsupported action '{action}' for {domain}. Allowed: {allowed}")

    return domain, action


def call_service(
    base_url: str,
    token: str,
    domain: str,
    service: str,
    entity_id: str,
    timeout: float,
) -> Any:
    body = json.dumps({"entity_id": entity_id}).encode("utf-8")
    request = Request(
        f"{base_url}/api/services/{domain}/{service}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise SystemExit("Home Assistant rejected the token.")
        raise SystemExit(f"Home Assistant HTTP error: {exc.code} {exc.reason}")
    except URLError as exc:
        raise SystemExit(f"Could not reach Home Assistant: {exc.reason}")
    except TimeoutError:
        raise SystemExit("Connection timed out.")

    if not payload:
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


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
    domain, service = resolve_action(args.entity_id, args.action)

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

