"""Shared Home Assistant REST helpers for the prototype tools."""

from __future__ import annotations

import json
import time
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


def load_config(path: Path, require_favorites: bool = False) -> dict[str, Any]:
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
    if require_favorites and not isinstance(favorites, list):
        raise SystemExit("Config value 'favorites' must be a list.")

    config["base_url"] = base_url
    config["token"] = token
    if isinstance(favorites, list):
        config["favorites"] = [str(item) for item in favorites]
    else:
        config["favorites"] = []
    return config


def request_json(
    base_url: str,
    token: str,
    path: str,
    timeout: float,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
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


def fetch_states_list(base_url: str, token: str, timeout: float) -> list[dict[str, Any]]:
    states = request_json(base_url, token, "/api/states", timeout)
    if not isinstance(states, list):
        raise SystemExit("Unexpected Home Assistant response: expected a list.")
    return states


def fetch_states_map(base_url: str, token: str, timeout: float) -> dict[str, dict[str, Any]]:
    return {str(item.get("entity_id", "")): item for item in fetch_states_list(base_url, token, timeout)}


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def display_name(entity_id: str, state: dict[str, Any] | None) -> str:
    if state is None:
        return entity_id
    attributes = state.get("attributes")
    if isinstance(attributes, dict) and attributes.get("friendly_name"):
        return str(attributes["friendly_name"])
    return entity_id


def resolve_action(entity_id: str, action: str = "auto") -> tuple[str, str] | None:
    domain = entity_domain(entity_id)
    if domain not in SUPPORTED_ACTIONS:
        return None

    if action == "auto":
        action = "toggle" if "toggle" in SUPPORTED_ACTIONS[domain] else "turn_on"

    if action not in SUPPORTED_ACTIONS[domain]:
        return None

    return domain, action


def call_service(
    base_url: str,
    token: str,
    domain: str,
    service: str,
    entity_id: str,
    timeout: float,
) -> Any:
    return request_json(
        base_url,
        token,
        f"/api/services/{domain}/{service}",
        timeout,
        method="POST",
        body={"entity_id": entity_id},
    )


def refresh_after_action(
    base_url: str,
    token: str,
    timeout: float,
    entity_id: str,
    previous_state: str | None,
) -> dict[str, dict[str, Any]]:
    latest_states = fetch_states_map(base_url, token, timeout)
    if previous_state not in {"on", "off"}:
        return latest_states

    for _ in range(8):
        latest = latest_states.get(entity_id)
        latest_state = str(latest.get("state", "")) if latest is not None else None
        if latest_state in {"on", "off"} and latest_state != previous_state:
            return latest_states
        time.sleep(0.25)
        latest_states = fetch_states_map(base_url, token, timeout)
    return latest_states


def changed_favorites(
    favorites: list[str],
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[str]:
    changes = []
    for entity_id in favorites:
        before_item = before.get(entity_id)
        after_item = after.get(entity_id)
        before_state = before_item.get("state", "missing") if before_item is not None else "missing"
        after_state = after_item.get("state", "missing") if after_item is not None else "missing"
        if before_state != after_state:
            changes.append(f"{entity_id}: {before_state} -> {after_state}")
    return changes

