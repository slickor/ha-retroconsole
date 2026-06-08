from __future__ import annotations

import pygame
import threading
import queue
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
    fetch_entity_history,
    load_config,
    refresh_after_action,
    resolve_action,
    save_config,
    VERSION,
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
    COLOR_TEXT,
    COLOR_TEXT_HIGHLIGHT,
    COLOR_INACTIVE,
    render_entity_picker,
    render_favorites,
    render_message,
    render_text,
    render_graph,
)

class HARetroApp:
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
        
        self.history_data = []
        self.graph_entity_id = ""
        self.graph_label = ""

        pygame.init()
        self.width = 640
        self.height = 480
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("HA RetroConsole")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.Font(None, 36)
        self.font_item = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 16)
        
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.pending_task_type = None

    def _start_background_task(self, task_type, target_func, *args, **kwargs):
        """Starts a function in a background thread and puts its result/error into the task_queue."""
        if self.current_task_thread and self.current_task_thread.is_alive():
            # A task is already running, ignore new task or handle as needed
            print(f"Warning: A background task ({self.pending_task_type}) is already running. Ignoring new task ({task_type}).")
            return

        self.pending_task_type = task_type
        # Capture task_type locally so the thread closure is not affected by
        # any future write to self.pending_task_type on the main thread.
        captured_task_type = task_type
        self.current_task_thread = threading.Thread(
            target=self._run_task_wrapper,
            args=(target_func, captured_task_type, args, kwargs),
        )
        self.current_task_thread.daemon = True  # Allow main program to exit even if thread is running
        self.current_task_thread.start()

    def _run_task_wrapper(self, target_func, task_type, args, kwargs):
        """Wrapper to execute target_func and put result/error into the queue."""
        try:
            result = target_func(*args, **kwargs)
            self.task_queue.put({"status": "success", "result": result, "type": task_type})
        except Exception as e:
            self.task_queue.put({"status": "error", "error": str(e), "type": task_type})

    def _fetch_states_background(self):
        """Fetches states in a background thread."""
        return fetch_states_map(
            self.config["base_url"],
            self.config["token"],
            self.timeout,
        )

    def _fetch_history_background(self, entity_id):
        return fetch_entity_history(
            self.config["base_url"],
            self.config["token"],
            entity_id,
            self.timeout,
            24
        )

    def load_states(self) -> None:
        self.message = "Connecting..."
        self.message_time = pygame.time.get_ticks()
        self._start_background_task("load_data", self._fetch_states_background)

    def save_config(self) -> None:
        if self.config_path is None:
            return
        save_config(self.config_path, self.config)

    def _execute_service_and_refresh_background(self, domain, service, entity_id, previous_state, before_states, favorites):
        """Executes a service call and refreshes states in a background thread."""
        call_service(
            self.config["base_url"],
            self.config["token"],
            domain,
            service,
            entity_id,
            self.timeout,
        )
        new_states = refresh_after_action(
            self.config["base_url"],
            self.config["token"],
            self.timeout,
            entity_id,
            previous_state,
        )
        # Pass necessary info back for UI update
        return {"new_states": new_states, "before_states": before_states, "favorites": favorites, "entity_id": entity_id}

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

    def _render_header(self, title: str) -> None:
        """Renders the standard app header with a title."""
        title_surface = self.font_title.render(title, True, COLOR_TEXT_HIGHLIGHT)
        self.screen.blit(title_surface, (20, 20))

    def render(self) -> None:
        self.screen.fill(COLOR_BG)

        if self.mode == "main":
            self._render_header("HA RetroConsole")
            self.render_main()
        elif self.mode == "favorites":
            self._render_header("Edit Favorites")
            self.render_picker()
        elif self.mode == "graph":
            self.render_graph_view()

        pygame.display.flip()

    def _render_footer(self, controls: list[tuple[str, str]]) -> None:
        """Renders common UI elements like the control hints, messages, and version number."""
        controls_y = self.height - 115
        pygame.draw.line(self.screen, COLOR_BORDER, (0, controls_y), (self.width, controls_y), 2)
        
        for i, (ctrl, pc) in enumerate(controls):
            y = controls_y + 12 + i * 22
            render_text(self.screen, self.font_small, ctrl, COLOR_TEXT, (20, y))
            render_text(self.screen, self.font_small, pc, COLOR_TEXT, (260, y))

        render_message(self.screen, self.font_small, self.message, self.width, controls_y + 50)

        version_surface = self.font_small.render(VERSION, True, COLOR_INACTIVE)
        self.screen.blit(version_surface, (self.width - 60, self.height - 25))

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
        
        self._render_footer([
            ("D-Pad: Navigate", "PC: Arrows"),
            ("A: Execute", "PC: Enter"),
            ("Y: Favorites", "PC: F"),
            ("X: Refresh", "PC: R"),
            ("B: Exit", "PC: Esc/B"),
        ])

    def render_picker(self) -> None:
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
        
        self._render_footer([
            ("D-Pad: Navigate", "PC: Arrows"),
            ("A: Toggle", "PC: Enter"),
            ("X: Refresh", "PC: R"),
            ("B: Back", "PC: Esc/B"),
        ])

    def render_graph_view(self) -> None:
        render_graph(
            self.screen,
            self.font_title,
            self.font_small,
            self.graph_label,
            self.history_data,
            self.width,
            self.height
        )
        self._render_footer([
            ("B: Back", "PC: Esc/B"),
        ])

    def handle_input(self) -> None:
        actions = poll_actions()

        for action in actions:
            self._dispatch_action(action)

    def _dispatch_action(self, action: int) -> None:
        """Dispatches an input action to the appropriate handler based on the current mode."""
        # Universal actions
        if action == ACTION_QUIT:
            self.running = False
            return
        if action == ACTION_REFRESH:
            self.load_states()
            self.message = "Refreshed"
            self.message_time = pygame.time.get_ticks()
            return

        # Mode-specific dispatch
        if self.mode == "main":
            self._handle_main_input(action)
        elif self.mode == "favorites":
            self._handle_picker_input(action)
        elif self.mode == "graph":
            if action == ACTION_BACK:
                self.mode = "main"

    def _handle_main_input(self, action: int) -> None:
        favorites = self.config.get("favorites", [])
        if action == ACTION_BACK:
            self.running = False
        elif action == ACTION_FAVORITES:
            self.mode = "favorites"
            self.load_entities()
            self.message = "Edit favorites"
            self.message_time = pygame.time.get_ticks()
        elif action == ACTION_UP and favorites:
            self.selected = (self.selected - 1) % len(favorites)
        elif action == ACTION_DOWN and favorites:
            self.selected = (self.selected + 1) % len(favorites)
        elif action == ACTION_SELECT:
            self.execute_action()

    def _handle_picker_input(self, action: int) -> None:
        if action == ACTION_BACK:
            self.mode = "main"
            self.message = "Favorites editor closed"
            self.message_time = pygame.time.get_ticks()
        elif action == ACTION_UP and self.entities:
            self.picker_selected = (self.picker_selected - 1) % len(self.entities)
        elif action == ACTION_DOWN and self.entities:
            self.picker_selected = (self.picker_selected + 1) % len(self.entities)
        elif action == ACTION_SELECT and self.entities:
            entity = self.entities[self.picker_selected]
            self.toggle_favorite(entity["entity_id"])
            self.load_entities()

    def execute_action(self) -> None:
        favorites = self.config.get("favorites", [])
        if not favorites or self.selected >= len(favorites):
            return

        favorite = favorites[self.selected]
        entity_id = favorite_entity_id(favorite)
        action = favorite_action(favorite)

        if entity_domain(entity_id) == "sensor":
            self.mode = "graph"
            self.graph_entity_id = entity_id
            self.graph_label = favorite_label(favorite, self.states.get(entity_id))
            self.history_data = []
            self.message = f"Loading graph for {entity_id}..."
            self.message_time = pygame.time.get_ticks()
            self._start_background_task("fetch_history", self._fetch_history_background, entity_id)
            return

        resolved = resolve_action(entity_id, action)
        if resolved is None:
            self.message = "Entity is read-only"
            self.message_time = pygame.time.get_ticks()
            return

        domain, service = resolved
        previous = self.states.get(entity_id)
        previous_state = str(previous.get("state", "")) if previous is not None else None
        
        self.message = f"Executing {service} on {entity_id}..."
        self.message_time = pygame.time.get_ticks()
        self._start_background_task(
            "execute_action",
            self._execute_service_and_refresh_background,
            domain, service, entity_id, previous_state, self.states, favorites
        )

    def run(self) -> None:
        self.load_states()

        while self.running:
            if self.auto_refresh_time > 0:
                elapsed = pygame.time.get_ticks() - self.auto_refresh_time
                if elapsed >= 2000:
                    self.load_states()
                    self.auto_refresh_time = 0
            
            # Process results from background tasks
            try:
                task_result = self.task_queue.get_nowait()
                self._process_task_result(task_result)
            except queue.Empty:
                pass  # No task results yet

            self.handle_input()
            self.render()
            self.clock.tick(30)

        pygame.quit()

    def _process_task_result(self, task_result):
        """Handles the result of a completed background task."""
        if task_result["status"] == "success":
            if task_result["type"] == "load_data":
                self.states = task_result["result"]
                self.message = "Connected"
                self.message_time = pygame.time.get_ticks()
                if self.mode == "favorites": # If in favorites editor, refresh entities list
                    self.load_entities()
            elif task_result["type"] == "execute_action":
                new_states = task_result["result"]["new_states"]
                before_states = task_result["result"]["before_states"]
                favorites = task_result["result"]["favorites"]

                self.states = new_states
                self.load_entities() # Refresh the grouped entities with new states if needed

                changes = changed_favorites(favorites, before_states, self.states)
                self.message = f"Done: {changes[0]}" if changes else "Executed"
                self.message_time = pygame.time.get_ticks()
                self.auto_refresh_time = pygame.time.get_ticks() # Keep auto-refresh for post-action
            elif task_result["type"] == "fetch_history":
                self.history_data = task_result["result"]
                self.message = "Graph loaded"
                self.message_time = pygame.time.get_ticks()
        else:  # status == "error"
            self.message = f"Error: {task_result['error']}"
            self.message_time = pygame.time.get_ticks()
        self.current_task_thread = None  # Task finished
        self.pending_task_type = None
