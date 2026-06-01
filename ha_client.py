"""Shared Home Assistant REST helpers for the prototype tools."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
 
VERSION = "0.30.0"


SUPPORTED_ACTIONS = {
    "light": {"toggle", "turn_on", "turn_off"},
    "switch": {"toggle", "turn_on", "turn_off"},
    "scene": {"turn_on"},
    "script": {"turn_on"},
    "climate": {"turn_on", "turn_off"},
    "media_player": {"toggle", "media_play_pause", "media_stop"},
    "cover": {"toggle", "open_cover", "close_cover"},
    "fan": {"toggle", "turn_on", "turn_off"},
    "input_boolean": {"toggle", "turn_on", "turn_off"},
    "lock": {"lock", "unlock"},
}

class HAClientError(Exception):
    """Base exception for Home Assistant client errors."""
    pass


def normalize_favorite(item: Any) -> Dict[str, str]:
    if isinstance(item, str):
        entity_id = item.strip()
        if not entity_id:
            raise HAClientError("Favorite entity_id must not be empty.")
        return {"entity_id": entity_id, "label": "", "action": "auto"}

    if not isinstance(item, dict):
        raise HAClientError("Each favorite must be an entity_id string or an object.")

    entity_id = str(item.get("entity_id", "")).strip()
    label = str(item.get("label", "")).strip()
    action = str(item.get("action", "auto")).strip() or "auto"
    if not entity_id:
        raise HAClientError("Favorite object is missing entity_id.")
    return {"entity_id": entity_id, "label": label, "action": action}


def load_config(path: Path, require_favorites: bool = False) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError:
        raise HAClientError(f"Config not found: {path}")
    except json.JSONDecodeError as exc:
        raise HAClientError(f"Config is not valid JSON: {exc}")

    base_url = str(config.get("base_url", "")).strip().rstrip("/")
    alternative_url = str(config.get("alternative_url", "")).strip().rstrip("/")
    token = str(config.get("token", "")).strip()
    favorites = config.get("favorites", [])

    if not base_url:
        raise HAClientError("Missing config value: base_url")
    if not token:
        print("Warning: No token provided in config.")
    elif token == "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE":
        print("Warning: Placeholder token detected. Please update config.json.")
    if require_favorites and not isinstance(favorites, list):
        raise HAClientError("Config value 'favorites' must be a list.")

    config["base_url"] = base_url
    config["alternative_url"] = alternative_url
    config["token"] = token
    if isinstance(favorites, list):
        config["favorites"] = [normalize_favorite(item) for item in favorites]
    else:
        config["favorites"] = []
    return config


def save_config(path: Path, config: Dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        raise HAClientError(f"Could not save config: {exc}")


def check_connectivity(base_url: str, token: str, timeout: float = 5.0) -> bool:
    """Returns True if the given Home Assistant URL is reachable and responds."""
    try:
        request = Request(
            f"{base_url}/api/",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def resolve_active_url(config: Dict[str, Any], timeout: float = 5.0) -> Tuple[str, str]:
    """Resolves the best available server URL.

    Tries the primary base_url first. If it is unreachable and an
    alternative_url is configured, falls back to that instead.

    Returns a tuple of (active_url, url_type) where url_type is
    one of 'primary' or 'alternative'.
    """
    base_url = config.get("base_url", "")
    alternative_url = config.get("alternative_url", "")
    token = config.get("token", "")

    if check_connectivity(base_url, token, timeout):
        return base_url, "primary"

    if alternative_url and check_connectivity(alternative_url, token, timeout):
        return alternative_url, "alternative"

    # Neither URL worked – return primary anyway so caller can handle the error
    return base_url, "primary"


def request_json(
    base_url: str,
    token: str,
    path: str,
    timeout: float,
    method: str = "GET",
    body: Optional[Dict[str, Any]] = None,
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
            raise HAClientError("Home Assistant rejected the token.")
        raise HAClientError(f"Home Assistant HTTP error: {exc.code} {exc.reason}")
    except URLError as exc:
        raise HAClientError(f"Could not reach Home Assistant: {exc.reason}")
    except TimeoutError:
        raise HAClientError("Connection timed out.")

    if not payload:
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload


def fetch_states_list(base_url: str, token: str, timeout: float) -> List[Dict[str, Any]]:
    states = request_json(base_url, token, "/api/states", timeout)
    if not isinstance(states, list):
        raise HAClientError("Unexpected Home Assistant response: expected a list.")
    return states


def fetch_states_map(base_url: str, token: str, timeout: float) -> Dict[str, Dict[str, Any]]:
    return {str(item.get("entity_id", "")): item for item in fetch_states_list(base_url, token, timeout)}


def get_domain_groups(states: List[Dict[str, Any]], favorites: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Groups entities by domain and adds a virtual 'Favorites' domain at the top."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    
    # Map for quick lookup
    states_map = {s.get("entity_id"): s for s in states if s.get("entity_id")}
    
    # 1. Create Favorites group first so it appears at the top of the list
    fav_list = []
    for fav in favorites:
        eid = favorite_entity_id(fav)
        if eid in states_map:
            fav_list.append(states_map[eid])

    if fav_list:
        groups["favorites"] = fav_list

    # 2. Collect all other entities and group them by domain
    other_groups: Dict[str, List[Dict[str, Any]]] = {}
    for state in states:
        eid = str(state.get("entity_id", ""))
        domain = entity_domain(eid)
        if domain and domain != "favorites":
            if domain not in other_groups:
                other_groups[domain] = []
            other_groups[domain].append(state)

    # 3. Sort domains alphabetically and sort entities within those domains by display name
    for domain in sorted(other_groups.keys()):
        entities = other_groups[domain]
        # Sort entities by their friendly name (display_name)
        entities.sort(key=lambda s: display_name(str(s.get("entity_id", "")), s).lower())
        groups[domain] = entities

    return groups


def entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def display_name(entity_id: str, state: Optional[Dict[str, Any]]) -> str:
    if state is None:
        return entity_id
    attributes = state.get("attributes")
    if isinstance(attributes, dict) and attributes.get("friendly_name"):
        return str(attributes["friendly_name"])
    return entity_id


def get_state_with_unit(state_obj: Dict[str, Any]) -> str:
    """Returns the state string appended with its unit of measurement if available."""
    state = str(state_obj.get("state", "unknown"))
    attributes = state_obj.get("attributes", {})
    unit = attributes.get("unit_of_measurement")
    if unit:
        return f"{state} {unit}"
    return state


def favorite_entity_id(favorite: Union[str, Dict[str, str]]) -> str:
    if isinstance(favorite, dict):
        return favorite["entity_id"]
    return str(favorite)


def favorite_label(favorite: Union[str, Dict[str, str]], state: Optional[Dict[str, Any]]) -> str:
    entity_id = favorite_entity_id(favorite)
    if isinstance(favorite, dict) and favorite.get("label"):
        return favorite["label"]
    return display_name(entity_id, state)


def favorite_action(favorite: Union[str, Dict[str, str]]) -> str:
    if isinstance(favorite, dict):
        return favorite.get("action", "auto")
    return "auto"


def resolve_action(entity_id: str, action: str = "auto") -> Optional[Tuple]:
    domain = entity_domain(entity_id)
    if domain not in SUPPORTED_ACTIONS:
        return None

    if action == "auto":
        action = "toggle" if "toggle" in SUPPORTED_ACTIONS[domain] else "turn_on"

    if action not in SUPPORTED_ACTIONS[domain]:
        return None

    return domain, action


def fetch_camera_snapshot(base_url: str, token: str, entity_id: str, timeout: float) -> bytes:
    """Fetches a JPEG snapshot from a camera entity."""
    request = Request(
        f"{base_url}/api/camera_proxy/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception:
        return b""


def call_service(
    base_url: str,
    token: str,
    domain: str,
    service: str,
    entity_id: str,
    timeout: float,
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    body = {"entity_id": entity_id}
    if data:
        body.update(data)
    return request_json(
        base_url,
        token,
        f"/api/services/{domain}/{service}",
        timeout,
        method="POST",
        body=body,
    )


def refresh_after_action(
    base_url: str,
    token: str,
    timeout: float,
    entity_id: str,
    previous_state: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    latest_states = fetch_states_map(base_url, token, timeout)
    if previous_state not in {"on", "off"}:
        return latest_states

    for _ in range(8):
        latest = latest_states.get(entity_id)
        latest_state = str(latest.get("state", "")) if latest is not None else None
        if latest_state in {"on", "off"} and latest_state != previous_state:
            return latest_states
        time.sleep(0.1)
        latest_states = fetch_states_map(base_url, token, timeout)
    return latest_states


def changed_favorites(
    favorites: List[Union[str, Dict[str, str]]],
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> List[str]:
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

def get_websocket_url(base_url: str) -> str:
    """Converts a standard HA base URL to a WebSocket URL."""
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_url}/api/websocket"

class HAWebSocketMessage:
    """Helper to create standard Home Assistant WebSocket messages."""
    
    @staticmethod
    def auth(token: str) -> str:
        return json.dumps({
            "type": "auth",
            "access_token": token
        })

    @staticmethod
    def subscribe_events() -> str:
        return json.dumps({
            "id": 1,
            "type": "subscribe_events",
            "event_type": "state_changed"
        })

    @staticmethod
    def get_states(request_id: int) -> str:
        """Initial fetch of all states via WebSocket."""
        return json.dumps({
            "id": request_id,
            "type": "get_states"
        })
