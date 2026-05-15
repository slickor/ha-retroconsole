#!/usr/bin/env python3
"""Interactive terminal view for Home Assistant favorites."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from ha_client import (
    call_service,
    changed_favorites,
    favorite_action,
    favorite_entity_id,
    favorite_label,
    fetch_states_map,
    load_config,
    refresh_after_action,
    resolve_action,
)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_favorites(favorites: list[str | dict[str, str]], states: dict[str, dict[str, Any]]) -> None:
    print("Home Assistant Favorites")
    print("HA RetroConsole")
    print()
    if not favorites:
        print("No favorites configured. Add entity_ids to config.json.")
        print()
        return

    for index, favorite in enumerate(favorites, start=1):
        entity_id = favorite_entity_id(favorite)
        state = states.get(entity_id)
        value = state.get("state", "missing") if state is not None else "missing"
        action = resolve_action(entity_id, favorite_action(favorite))
        marker = " " if action else "-"
        print(f"{index:>2}. [{marker}] {favorite_label(favorite, state):<32} {value:<12} {entity_id}")

    print()
    print("[number] run  r refresh  q quit")
    print("Entities marked '-' are read-only in this prototype.")


def run_loop(config: dict[str, Any], timeout: float) -> None:
    states = fetch_states_map(config["base_url"], config["token"], timeout)

    while True:
        clear_screen()
        print_favorites(config["favorites"], states)
        choice = input("> ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return
        if choice in {"r", "refresh", ""}:
            states = fetch_states_map(config["base_url"], config["token"], timeout)
            continue
        if not choice.isdigit():
            input("Unknown command. Press Enter to continue.")
            continue

        index = int(choice) - 1
        if index < 0 or index >= len(config["favorites"]):
            input("Invalid favorite number. Press Enter to continue.")
            continue

        favorite = config["favorites"][index]
        entity_id = favorite_entity_id(favorite)
        action = resolve_action(entity_id, favorite_action(favorite))
        if action is None:
            input("This entity is read-only for now. Press Enter to continue.")
            continue

        domain, service = action
        previous = states.get(entity_id)
        previous_state = str(previous.get("state", "")) if previous is not None else None
        before_states = states
        call_service(
            config["base_url"],
            config["token"],
            domain,
            service,
            entity_id,
            timeout,
        )
        states = refresh_after_action(
            config["base_url"],
            config["token"],
            timeout,
            entity_id,
            previous_state,
        )
        changes = changed_favorites(config["favorites"], before_states, states)
        if changes:
            print()
            print("Changed favorites:")
            for change in changes:
                print(f"  {change}")
            input("Press Enter to continue.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive Home Assistant favorites view.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config), require_favorites=True)
    run_loop(config, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
