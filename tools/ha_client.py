"""Shared Home Assistant REST helpers for the prototype tools."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VERSION = "0.9.2"


SUPPORTED_ACTIONS = {
    "light": {"toggle", "turn_on", "turn_off"},
    "switch": {"toggle", "turn_on", "turn_off"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
}


def normalize_favorite(item: Any) -> dict[str, str]:
    if isinstance(item, str):
        entity_id = item.strip()
        if not entity_id:
            raise SystemExit("Favorite entity_id must not be empty.")
        return {"entity_id": entity_id, "label": "", "action": "auto"}

    if not isinstance(item, dict):
        raise SystemExit("Each favorite must be an entity_id string or an object.")

    entity_id = str(item.get("entity_id", "")).strip()
    label = str(item.get("label", "")).strip()
    action = str(item.get("action", "auto")).strip() or "auto"
    if not entity_id:
        raise SystemExit("Favorite object is missing entity_id.")
    return {"entity_id": entity_id, "label": label, "action": action}


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
    if not token:
        print("Warning: No token provided in config.")
    elif token == "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE":
        print("Warning: Placeholder token detected. Please update config.json.")
    if require_favorites and not isinstance(favorites, list):
        raise SystemExit("Config value 'favorites' must be a list.")
    
    domain_order = config.get("domain_order", [])
    if not isinstance(domain_order, list):
        print("Warning: Config value 'domain_order' must be a list. Resetting to default.")
        domain_order = []

    config["base_url"] = base_url
    config["token"] = token
    if isinstance(favorites, list):
        config["favorites"] = [normalize_favorite(item) for item in favorites]
    else:
        config["favorites"] = []
    config["domain_order"] = domain_order
    return config


def save_config(path: Path, config: dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        raise SystemExit(f"Could not save config: {exc}")


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


def get_domain_groups(states: list[dict[str, Any]], favorites: list[dict[str, Any]], user_domain_order: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Groups entities by domain and adds a virtual 'Favorites' domain at the top."""
    groups: dict[str, list[dict[str, Any]]] = {}
    
    # Map for quick lookup
    states_map = {s.get("entity_id"): s for s in states if s.get("entity_id")}
    
    # 1. Create Favorites group first so it appears at the top of the list
    fav_list = []
    for fav in favorites:
        eid = fav.get("entity_id")
        if eid in states_map:
            fav_list.append(states_map[eid])
    
    if fav_list:
        groups["favorites"] = fav_list # Use the order from the config directly for favorites, no re-sorting here

    # 2. Group remaining entities by domain
    # Sort all entities by their display name before grouping to ensure consistent order within domains
    sorted_states = sorted(states, key=lambda x: display_name(x.get("entity_id", ""), x).lower())
    
    all_domains_from_states = set()
    for state in sorted_states:
        domain = entity_domain(str(state.get("entity_id", "")))
        if domain:
            all_domains_from_states.add(domain)
            if domain not in groups:
                groups[domain] = []
            groups[domain].append(state)

    # Now, create the final ordered dictionary based on user_domain_order
    ordered_groups: dict[str, list[dict[str, Any]]] = {}
    
    # Always add 'favorites' first if it exists
    if "favorites" in groups:
        ordered_groups["favorites"] = groups["favorites"]

    # Add domains from user_domain_order
    for domain_name in user_domain_order:
        if domain_name != "favorites" and domain_name in groups: # Ensure favorites is not re-added
            ordered_groups[domain_name] = groups[domain_name]
    
    # Add any remaining domains (not in user_domain_order or favorites) alphabetically
    remaining_domains = sorted([d for d in all_domains_from_states if d not in ordered_groups])
    for domain_name in remaining_domains:
        ordered_groups[domain_name] = groups[domain_name]

    return ordered_groups


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def display_name(entity_id: str, state: dict[str, Any] | None) -> str:
    if state is None:
        return entity_id
    attributes = state.get("attributes")
    if isinstance(attributes, dict) and attributes.get("friendly_name"):
        return str(attributes["friendly_name"])
    return entity_id


def favorite_entity_id(favorite: str | dict[str, str]) -> str:
    if isinstance(favorite, dict):
        return favorite["entity_id"]
    return str(favorite)


def favorite_label(favorite: str | dict[str, str], state: dict[str, Any] | None) -> str:
    entity_id = favorite_entity_id(favorite)
    if isinstance(favorite, dict) and favorite.get("label"):
        return favorite["label"]
    return display_name(entity_id, state)


def favorite_action(favorite: str | dict[str, str]) -> str:
    if isinstance(favorite, dict):
        return favorite.get("action", "auto")
    return "auto"


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
    favorites: list[str | dict[str, str]],
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[str]:
    changes = []
    for favorite in favorites:
        entity_id = favorite_entity_id(favorite)
        before_item = before.get(entity_id)
        after_item = after.get(entity_id)
        before_state = before_item.get("state", "missing") if before_item is not None else "missing"
        after_state = after_item.get("state", "missing") if after_item is not None else "missing"
        if before_state != after_state:
            changes.append(f"{entity_id}: {before_state} -> {after_state}")
    return changes
