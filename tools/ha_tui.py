#!/usr/bin/env python3
"""Keyboard-driven Home Assistant favorites UI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

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


def fit_message(changes: list[str]) -> str:
    if not changes:
        return "No visible favorite state changed yet."
    if len(changes) == 1:
        return f"Changed {changes[0]}"
    return f"Changed {len(changes)} favorites: " + "; ".join(changes[:2])


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def fit_text(value: str, width: int) -> str:
    if len(value) <= width:
        return value.ljust(width)
    if width <= 1:
        return value[:width]
    return value[: width - 1] + "~"


def render(
    favorites: list[str | dict[str, str]],
    states: dict[str, dict[str, Any]],
    selected: int,
    message: str,
) -> None:
    clear_screen()
    width = 58
    print("+" + "-" * width + "+")
    print("|" + " HA RETROCONSOLE".center(width) + "|")
    print("|" + " Favorites".center(width) + "|")

    if not favorites:
        print("|" + " No favorites configured. Add entity_ids to config.json.".ljust(width) + "|")
    else:
        visible_rows = 9
        start = max(0, min(selected - visible_rows + 1, len(favorites) - visible_rows))
        end = min(len(favorites), start + visible_rows)
        for index in range(start, end):
            favorite = favorites[index]
            entity_id = favorite_entity_id(favorite)
            state = states.get(entity_id)
            name = favorite_label(favorite, state)
            value = state.get("state", "missing") if state is not None else "missing"
            action = resolve_action(entity_id, favorite_action(favorite))
            prefix = ">" if index == selected else " "
            marker = "A" if action else "-"
            row = f" {prefix} {fit_text(name, 27)} {fit_text(value.upper(), 10)} [{marker}] "
            print("|" + row.ljust(width) + "|")

        for _ in range(visible_rows - (end - start)):
            print("|" + "".ljust(width) + "|")

    print("|" + "".ljust(width) + "|")
    print("|" + " D-Pad select   A run   X refresh   B quit".center(width) + "|")
    print("|" + " PC: arrows     Enter   R           Q".center(width) + "|")
    if message:
        print("|" + fit_text(" " + message, width) + "|")
    else:
        print("|" + "".ljust(width) + "|")
    print("+" + "-" * width + "+")


def read_key() -> str:
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()
        if key in {"\x00", "\xe0"}:
            second = msvcrt.getwch()
            if second == "H":
                return "up"
            if second == "P":
                return "down"
            return "unknown"
        if key == "\r":
            return "enter"
        return key.lower()

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        if key == "\x1b":
            sequence = sys.stdin.read(2)
            if sequence == "[A":
                return "up"
            if sequence == "[B":
                return "down"
            return "unknown"
        if key in {"\r", "\n"}:
            return "enter"
        return key.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def run_loop(config: dict[str, Any], timeout: float) -> None:
    states = fetch_states_map(config["base_url"], config["token"], timeout)
    selected = 0
    message = "Connected."

    while True:
        favorites = config["favorites"]
        if favorites:
            selected = max(0, min(selected, len(favorites) - 1))
        render(favorites, states, selected, message)
        key = read_key()
        message = ""

        if key in {"q", "b", "\x1b"}:
            return
        if key in {"r", "x", "refresh"}:
            states = fetch_states_map(config["base_url"], config["token"], timeout)
            message = "Refreshed."
            continue
        if key == "up" and favorites:
            selected = (selected - 1) % len(favorites)
            continue
        if key == "down" and favorites:
            selected = (selected + 1) % len(favorites)
            continue
        if key != "enter" or not favorites:
            continue

        favorite = favorites[selected]
        entity_id = favorite_entity_id(favorite)
        action = resolve_action(entity_id, favorite_action(favorite))
        if action is None:
            message = "This entity is read-only for now."
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
        changes = changed_favorites(favorites, before_states, states)
        message = fit_message(changes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keyboard-driven Home Assistant favorites UI.")
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
