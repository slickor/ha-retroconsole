#!/usr/bin/env python3
"""Interactive terminal view for Home Assistant favorites."""

from __future__ import annotations

import argparse
import json
import os
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
    favorites = config.get("favorites", [])

    if not base_url:
        raise SystemExit("Missing config value: base_url")
    if not token or token == "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE":
        raise SystemExit("Missing config value: token")
    if not isinstance(favorites, list):
        raise SystemExit("Config value 'favorites' must be a list.")

    config["base_url"] = base_url
    config["token"] = token
    config["favorites"] = [str(item) for item in favorites]
    return config


def home_assistant_request(
    base_url: str,
    token: str,
    path: str,
    timeout: float,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> Any:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = Request(
        f"{base_url}{path}",
        data=data,
        method=method,
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


def fetch_states(base_url: str, token: str, timeout: float) -> dict[str, dict[str, Any]]:
    states = home_assistant_request(base_url, token, "/api/states", timeout)
    if not isinstance(states, list):
        raise SystemExit("Unexpected Home Assistant response: expected a list.")
    return {str(item.get("entity_id", "")): item for item in states}


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def display_name(entity_id: str, state: dict[str, Any] | None) -> str:
    if state is None:
        return entity_id
    attributes = state.get("attributes")
    if isinstance(attributes, dict) and attributes.get("friendly_name"):
        return str(attributes["friendly_name"])
    return entity_id


def resolve_action(entity_id: str) -> tuple[str, str] | None:
    domain = entity_domain(entity_id)
    if domain not in SUPPORTED_ACTIONS:
        return None
    service = "toggle" if "toggle" in SUPPORTED_ACTIONS[domain] else "turn_on"
    return domain, service


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_favorites(favorites: list[str], states: dict[str, dict[str, Any]]) -> None:
    print("Home Assistant Favorites")
    print()
    if not favorites:
        print("No favorites configured. Add entity_ids to config.json.")
        print()
        return

    for index, entity_id in enumerate(favorites, start=1):
        state = states.get(entity_id)
        value = state.get("state", "missing") if state is not None else "missing"
        action = resolve_action(entity_id)
        marker = " " if action else "-"
        print(f"{index:>2}. [{marker}] {display_name(entity_id, state):<32} {value:<12} {entity_id}")

    print()
    print("[number] run  r refresh  q quit")
    print("Entities marked '-' are read-only in this prototype.")


def run_loop(config: dict[str, Any], timeout: float) -> None:
    states = fetch_states(config["base_url"], config["token"], timeout)

    while True:
        clear_screen()
        print_favorites(config["favorites"], states)
        choice = input("> ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return
        if choice in {"r", "refresh", ""}:
            states = fetch_states(config["base_url"], config["token"], timeout)
            continue
        if not choice.isdigit():
            input("Unknown command. Press Enter to continue.")
            continue

        index = int(choice) - 1
        if index < 0 or index >= len(config["favorites"]):
            input("Invalid favorite number. Press Enter to continue.")
            continue

        entity_id = config["favorites"][index]
        action = resolve_action(entity_id)
        if action is None:
            input("This entity is read-only for now. Press Enter to continue.")
            continue

        domain, service = action
        home_assistant_request(
            config["base_url"],
            config["token"],
            f"/api/services/{domain}/{service}",
            timeout,
            method="POST",
            body={"entity_id": entity_id},
        )
        states = fetch_states(config["base_url"], config["token"], timeout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive Home Assistant favorites view.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    run_loop(config, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

