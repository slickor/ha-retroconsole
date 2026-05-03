#!/usr/bin/env python3
"""Small Home Assistant connectivity check with no external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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


def fetch_states(base_url: str, token: str, timeout: float) -> list[dict[str, Any]]:
    request = Request(
        f"{base_url}/api/states",
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

    try:
        states = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Home Assistant returned invalid JSON: {exc}")

    if not isinstance(states, list):
        raise SystemExit("Unexpected Home Assistant response: expected a list.")

    return states


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else "unknown"


def display_name(entity: dict[str, Any]) -> str:
    entity_id = str(entity.get("entity_id", "unknown"))
    attributes = entity.get("attributes")
    if isinstance(attributes, dict):
        friendly_name = attributes.get("friendly_name")
        if friendly_name:
            return str(friendly_name)
    return entity_id


def print_summary(
    states: list[dict[str, Any]],
    favorites: list[str],
    domain_filter: set[str],
    search: str,
    limit: int,
) -> None:
    domains = Counter(entity_domain(str(item.get("entity_id", ""))) for item in states)
    print(f"Connected. Loaded {len(states)} entities.")
    print()
    print("Top domains:")
    for domain, count in domains.most_common(12):
        print(f"  {domain}: {count}")

    if favorites:
        print()
        print("Favorites:")
        by_id = {str(item.get("entity_id", "")): item for item in states}
        for entity_id in favorites:
            entity = by_id.get(entity_id)
            if entity is None:
                print(f"  {entity_id}: not found")
                continue
            print(f"  {entity_id}: {entity.get('state', 'unknown')} ({display_name(entity)})")

    print()
    print("Entity candidates:")
    controllable = {"light", "switch", "scene", "script"}
    shown = 0
    for entity in states:
        entity_id = str(entity.get("entity_id", ""))
        domain = entity_domain(entity_id)
        name = display_name(entity)
        if domain_filter and domain not in domain_filter:
            continue
        if not domain_filter and domain not in controllable:
            continue
        if search and search not in f"{entity_id} {name}".lower():
            continue
        print(f"  {entity_id}: {entity.get('state', 'unknown')} ({name})")
        shown += 1
        if shown >= limit:
            break
    if shown == 0:
        print("  none found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Home Assistant REST connectivity.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="Only show entities from this domain. Can be used more than once.",
    )
    parser.add_argument("--search", default="", help="Only show entities matching this text.")
    parser.add_argument("--limit", default=10, type=int, help="Maximum number of entities to show.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    states = fetch_states(config["base_url"], config["token"], args.timeout)
    favorites = config.get("favorites", [])
    if not isinstance(favorites, list):
        favorites = []
    domain_filter = {str(item).strip() for item in args.domain if str(item).strip()}
    search = str(args.search).strip().lower()
    print_summary(states, [str(item) for item in favorites], domain_filter, search, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
