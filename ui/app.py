from __future__ import annotations

import pygame
from pathlib import Path
from typing import Any

from ha_client import (
    call_service,
    changed_favorites,
    display_name,
    entity_domain,
    favorite_action,
    favorite_entity_id,
    fetch_states_map,
    load_config,
    refresh_after_action,
    save_config,
    SUPPORTED_ACTIONS,
)
from ui.input import (
    ACTION_BACK,
    ACTION_FAVORITES,
    ACTION_REFRESH,
    ACTION_SELECT,
    ACTION_UP,
    ACTION_DOWN,
    ACTION_QUIT,
    poll_actions,
)
from ui.widgets import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT,
    COLOR_TEXT_HIGHLIGHT,
    COLOR_INACTIVE,
    render_controls,
    render_entity_picker,
    render_favorites,
    render_message,
    render_text,
)


class HAPortPilot:
    def __init__(self, config: dict[str, Any], timeout: float = 10.0, config_path: Path | None = None):
        self.config = config
        self.timeout = timeout
        self.config_path = config_path
        self.states: dict[str, dict[str, Any]] = {}
        self.selected = 0
        self.entities: list[dict[str, str]] = []
        self.picker_selected = 0
        self.mode = "main"
        self.message = "Connecting..."
        self.message_time = 0
        self.auto_refresh_time = 0
        self.running = True

        pygame.init()
        self.width = 640
        self.height = 480
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("HA PortPilot")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.Font(None, 36)
        self.font_item = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 16)

    def load_states(self) -> None:
        try:
            self.states = fetch_states_map(
                self.config["base_url"],
                self.config["token"],
                self.timeout,
            )
            self.message = "Connected"
            self.message_time = pygame.time.get_ticks()
            if self.mode == "favorites":
                self.load_entities()
        except Exception as e:
            self.message = f"Error: {str(e)}"
            self.message_time = pygame.time.get_ticks()

    def save_config(self) -> None:
        if self.config_path is None:
            return
        save_config(self.config_path, self.config)

    def load_entities(self) -> None:
        entities: list[dict[str, str]] = []
        for entity_id, state in self.states.items():
            domain = entity_domain(entity_id)
            if domain not in SUPPORTED_ACTIONS:
                continue
            entities.append(
                {
                    "entity_id": entity_id,
                    "label": display_name(entity_id, state),
                    "state": str(state.get("state", "")),
                    "domain": domain,
                }
            )
        entities.sort(key=lambda item: (item["domain"], item["label"].lower(), item["entity_id"]))
        self.entities = entities
        self.picker_selected = 0

    def is_favorite(self, entity_id: str) -> bool:
        return any(favorite_entity_id(fav) == entity_id for fav in self.config.get("favorites", []))

    def toggle_favorite(self, entity_id: str) -> None:
        favorites = self.config.get("favorites", [])
        index = next((i for i, fav in enumerate(favorites) if favorite_entity_id(fav) == entity_id), None)
        if index is not None:
            del favorites[index]
            self.message = "Favorite removed"
        else:
            favorites.append({"entity_id": entity_id, "label": "", "action": "auto"})
            self.message = "Favorite added"
        self.config["favorites"] = favorites
        self.save_config()
        self.message_time = pygame.time.get_ticks()

    def render(self) -> None:
        self.screen.fill(COLOR_BG)
        title_surface = self.font_title.render("HA PortPilot", True, COLOR_TEXT_HIGHLIGHT)
        self.screen.blit(title_surface, (20, 20))

        if self.mode == "main":
            self.render_main()
        else:
            self.render_picker()

        pygame.display.flip()

    def render_main(self) -> None:
        favorites = self.config.get("favorites", [])
        render_favorites(
            self.screen,
            self.font_item,
            self.font_small,
            favorites,
            self.states,
            self.selected,
            self.width,
        )

        controls_y = self.height - 115
        pygame.draw.line(self.screen, COLOR_BORDER, (0, controls_y), (self.width, controls_y), 2)
        controls = [
            ("D-Pad: Navigate", "PC: Arrows"),
            ("A: Execute", "PC: Enter"),
            ("Y: Favorites", "PC: F"),
            ("X: Refresh", "PC: R"),
            ("B: Exit", "PC: Esc/B"),
        ]
        for i, (ctrl, pc) in enumerate(controls):
            y = controls_y + 12 + i * 22
            render_text(self.screen, self.font_small, ctrl, COLOR_TEXT, (20, y))
            render_text(self.screen, self.font_small, pc, COLOR_TEXT, (260, y))

        render_message(self.screen, self.font_small, self.message, self.width, controls_y + 50)

    def render_picker(self) -> None:
        title_surface = self.font_title.render("Edit Favorites", True, COLOR_TEXT_HIGHLIGHT)
        self.screen.blit(title_surface, (20, 20))

        favorite_ids = {favorite_entity_id(fav) for fav in self.config.get("favorites", [])}
        render_entity_picker(
            self.screen,
            self.font_item,
            self.font_small,
            self.entities,
            self.picker_selected,
            favorite_ids,
            self.width,
        )

        controls_y = self.height - 115
        pygame.draw.line(self.screen, COLOR_BORDER, (0, controls_y), (self.width, controls_y), 2)
        controls = [
            ("D-Pad: Navigate", "PC: Arrows"),
            ("A: Toggle", "PC: Enter"),
            ("X: Refresh", "PC: R"),
            ("B: Back", "PC: Esc/B"),
        ]
        for i, (ctrl, pc) in enumerate(controls):
            y = controls_y + 12 + i * 22
            render_text(self.screen, self.font_small, ctrl, COLOR_TEXT, (20, y))
            render_text(self.screen, self.font_small, pc, COLOR_TEXT, (260, y))

        render_message(self.screen, self.font_small, self.message, self.width, controls_y + 50)

    def handle_input(self) -> None:
        actions = poll_actions()

        favorites = self.config.get("favorites", [])
        active_list_length = len(favorites) if self.mode == "main" else len(self.entities)

        for action in actions:
            if action == ACTION_QUIT:
                self.running = False
                return
            if action == ACTION_BACK:
                if self.mode == "favorites":
                    self.mode = "main"
                    self.message = "Favorites editor closed"
                    self.message_time = pygame.time.get_ticks()
                    return
                self.running = False
                return
            if action == ACTION_REFRESH:
                self.load_states()
                self.message = "Refreshed"
                self.message_time = pygame.time.get_ticks()
                return
            if action == ACTION_FAVORITES and self.mode == "main":
                self.mode = "favorites"
                self.load_entities()
                self.message = "Edit favorites"
                self.message_time = pygame.time.get_ticks()
                return
            if action == ACTION_UP and active_list_length:
                if self.mode == "main":
                    self.selected = (self.selected - 1) % active_list_length
                else:
                    self.picker_selected = (self.picker_selected - 1) % active_list_length
                return
            if action == ACTION_DOWN and active_list_length:
                if self.mode == "main":
                    self.selected = (self.selected + 1) % active_list_length
                else:
                    self.picker_selected = (self.picker_selected + 1) % active_list_length
                return
            if action == ACTION_SELECT:
                if self.mode == "main":
                    self.execute_action()
                else:
                    if self.entities:
                        entity = self.entities[self.picker_selected]
                        self.toggle_favorite(entity["entity_id"])
                        self.load_entities()
                return

    def execute_action(self) -> None:
        favorites = self.config.get("favorites", [])
        if not favorites or self.selected >= len(favorites):
            return

        favorite = favorites[self.selected]
        entity_id = favorite_entity_id(favorite)
        action = favorite_action(favorite)

        from ha_client import resolve_action

        resolved = resolve_action(entity_id, action)
        if resolved is None:
            self.message = "Entity is read-only"
            self.message_time = pygame.time.get_ticks()
            return

        domain, service = resolved
        previous = self.states.get(entity_id)
        previous_state = str(previous.get("state", "")) if previous is not None else None
        before_states = self.states

        try:
            call_service(
                self.config["base_url"],
                self.config["token"],
                domain,
                service,
                entity_id,
                self.timeout,
            )

            self.states = refresh_after_action(
                self.config["base_url"],
                self.config["token"],
                self.timeout,
                entity_id,
                previous_state,
            )

            changes = changed_favorites(favorites, before_states, self.states)
            self.message = f"Done: {changes[0]}" if changes else "Executed"
            self.message_time = pygame.time.get_ticks()
            self.auto_refresh_time = pygame.time.get_ticks()

        except Exception as e:
            self.message = f"Error: {str(e)[:40]}"
            self.message_time = pygame.time.get_ticks()

    def run(self) -> None:
        self.load_states()

        while self.running:
            if self.auto_refresh_time > 0:
                elapsed = pygame.time.get_ticks() - self.auto_refresh_time
                if elapsed >= 2000:
                    self.load_states()
                    self.auto_refresh_time = 0

            self.handle_input()
            self.render()
            self.clock.tick(30)

        pygame.quit()
