import sys
import os
import time
import threading
import queue
sys.path.insert(0, os.path.dirname(__file__) + "/..")

import sdl2
import sdl2.ext
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as ttf
from retro_ui import RetroUI

from ha_client import (
    VERSION,
    SUPPORTED_ACTIONS,
    call_service,
    changed_favorites,
    display_name,
    entity_domain,
    favorite_action,
    favorite_entity_id,
    favorite_label,
    fetch_states_map,
    load_config,
    refresh_after_action,
    save_config,
    resolve_action,
)

# Controller Button Mapping Aliases (SDL Constants)
# A=0, B=1, X=2, Y=3, Back=4, Guide=5, Start=6
BTN_A = sdl2.SDL_CONTROLLER_BUTTON_A
BTN_B = sdl2.SDL_CONTROLLER_BUTTON_B
BTN_X = sdl2.SDL_CONTROLLER_BUTTON_X
BTN_Y = sdl2.SDL_CONTROLLER_BUTTON_Y

# Colors (SDL2 RGB)
COLOR_BG = sdl2.SDL_Color(0, 11, 21, 255)       # Dark Blue (#000B15)
COLOR_CYAN = sdl2.SDL_Color(0, 163, 255, 255)   # Cyan (#00A3FF)
COLOR_HA_BLUE = sdl2.SDL_Color(3, 169, 244, 255) # HA Blue (#03A9F4)
COLOR_YELLOW = sdl2.SDL_Color(238, 176, 0, 255) # Yellow (#EEB000)
COLOR_GREY = sdl2.SDL_Color(85, 85, 85, 255)    # Grey (#555555)
COLOR_TEXT = COLOR_CYAN
COLOR_TEXT_DIM = COLOR_GREY
COLOR_HIGHLIGHT = COLOR_CYAN

class HASDL2App:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.states = {}
        self.favorites = self.config.get("favorites", [])
        self.entities = []
        self.selected = 0 # For main menu favorites
        self.nav_index = 0 # Index for the left navigation column
        self.active_list = "domains" # Active column: "domains" or "entities"
        self.entity_index = 0 # Index for the middle entity list
        self.btn_tex_map = {
            BTN_A: "btn_a",
            BTN_B: "btn_b",
            BTN_X: "btn_x",
            BTN_Y: "btn_y"
        }
        self.mode = "main" # "main", "favorites", or "settings"
        self.favorites_editor_mode = "domains" # "domains" or "entities"
        self.selected_domain_index = 0 # For domain selection in favorites editor
        self.settings_selected_index = 0
        self.main_scroll_row = 0
        self.entity_scroll_row = 0 # Scroll position for main entity list
        self.setup_controls()
        self.domain_scroll = 0 # For domain grid scrolling
        self.picker_scroll = 0
        self.selected_entity_in_domain_index = 0 # For entity selection within a domain
        self.running = True
        self.message = "Loading..."
        self.message_time = 0
        self.width = 640
        self.height = 480
        self.window = None
        self.renderer = None
        self.ui = None
        self.domain_icons = {}  # Cache for loaded textures
        self.entities_by_domain = {} # Grouped entities for favorites editor
        self.domain_list = [] # List of domains for favorites editor
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.game_controllers = []

    def setup_controls(self):
        """Detects OS and sets up button mapping."""
        layout = self.config.get("control_layout", "auto")
        
        if layout == "auto":
            # Auto-detection
            if os.path.exists("/mnt/SDCARD/spruce"):
                layout = "spruce"
            else:
                layout = "muos"

        self.layout_type = layout
        # muOS/Default: Confirm=A (0), Cancel=B (1) | Spruce: Confirm=B (1), Cancel=A (0)
        self.controls = {"confirm": BTN_A, "cancel": BTN_B} if layout == "muos" else {"confirm": BTN_B, "cancel": BTN_A}

    def init_sdl(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER)
        sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG)
        ttf.TTF_Init()
        
        # On Windows we use windowed mode for more stable testing
        flags = sdl2.SDL_WINDOW_SHOWN
        if os.name != "nt":
            flags |= sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP

        self.window = sdl2.SDL_CreateWindow(
            b"Home Assistant - for retroconsoles", 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            self.width, self.height, flags
        )
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        if not self.renderer:
            print(f"Error: Could not create SDL renderer: {sdl2.SDL_GetError()}")
            return

        sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"1")
        
        # Set logical size to 640x480. SDL2 will handle scaling and letterboxing 
        # automatically on high-res screens like the TrimUI Smart Pro (720p).
        sdl2.SDL_RenderSetLogicalSize(self.renderer, self.width, self.height)
        
        # Cross-platform font candidates including relative asset path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_candidates = [
            os.path.join(script_dir, "..", "assets", "fonts", "DejaVuSans.ttf"),
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\verdana.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf"
        ]
        selected_font = None
        for candidate in font_candidates:
            if os.path.exists(candidate):
                selected_font = candidate
                break
        
        if not selected_font:
            raise SystemExit("Error: Could not load any font. Ensure assets/fonts/DejaVuSans.ttf exists.")

        # Initialize the RetroUI framework
        self.ui = RetroUI(self.renderer, selected_font)

        # Load domain icons (light.png, switch.png, etc.)
        icon_dir = os.path.join(script_dir, "..", "assets", "icons")
        domains = ["light", "switch", "scene", "script", "sensor", "binary_sensor", "climate"]
        suffixes = ["", "_on", "_off"]
        
        for domain in domains:
            for suffix in suffixes:
                icon_name = f"{domain}{suffix}"
                # We search for .png first, then fallback to .bmp
                icon_path = self._find_icon(icon_dir, icon_name)
                if os.path.exists(icon_path):
                    surface = sdlimage.IMG_Load(icon_path.encode('utf-8'))
                    if surface:
                        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                        if texture:
                            self.domain_icons[icon_name] = texture
                        sdl2.SDL_FreeSurface(surface)

        # Load button icons
        for btn in ["btn_a", "btn_b", "btn_x", "btn_y", "ha_logo"]:
            icon_path = self._find_icon(icon_dir, btn)
            if os.path.exists(icon_path):
                surface = sdlimage.IMG_Load(icon_path.encode('utf-8'))
                if surface:
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    if texture:
                        self.domain_icons[btn] = texture
                    sdl2.SDL_FreeSurface(surface)

        # Open game controllers
        for i in range(sdl2.SDL_NumJoysticks()):
            if sdl2.SDL_IsGameController(i):
                controller = sdl2.SDL_GameControllerOpen(i)
                if controller:
                    self.game_controllers.append(controller)
                    print(f"Opened game controller: {sdl2.SDL_GameControllerName(controller).decode('utf-8')}")

    def _start_background_task(self, task_type, target_func, *args, **kwargs):
        """Starts a function in a background thread and puts its result/error into the task_queue."""
        if self.current_task_thread and self.current_task_thread.is_alive():
            # A task is already running, ignore new task or handle as needed
            print(f"Warning: A background task ({self.pending_task_type}) is already running. Ignoring new task ({task_type}).")
            return

        self.pending_task_type = task_type
        self.current_task_thread = threading.Thread(target=self._run_task_wrapper, args=(target_func, args, kwargs))
        self.current_task_thread.daemon = True  # Allow main program to exit even if thread is running
        self.current_task_thread.start()

    def _execute_entity_action(self):
        """Executes the default action for the selected entity in the list."""
        if not self.domain_list or self.nav_index >= len(self.domain_list):
            return
        current_domain = self.domain_list[self.nav_index]
        entities = self.entities_by_domain.get(current_domain, [])
        if not entities or self.entity_index >= len(entities):
            return
            
        entity = entities[self.entity_index]
        entity_id = entity["entity_id"]
        domain = entity["domain"]
        state = self.states.get(entity_id, {})
        previous_state = str(state.get("state", ""))
        domain, service = resolve_action(entity_id, "auto") or (domain, "turn_on")

        self.set_message(f"Executing {service} on {entity['label']}...")
        self._start_background_task(
            "execute_action",
            self._execute_service_and_refresh_background,
            domain, service, entity_id, previous_state, None
        )

    def _run_task_wrapper(self, target_func, args, kwargs):
        """Wrapper to execute target_func and put result/error into the queue."""
        try:
            result = target_func(*args, **kwargs)
            self.task_queue.put({"status": "success", "result": result, "type": self.pending_task_type})
        except BaseException as e:
            self.task_queue.put({"status": "error", "error": str(e), "type": self.pending_task_type})

    def _find_icon(self, icon_dir, name):
        png_path = os.path.join(icon_dir, f"{name}.png")
        if os.path.exists(png_path):
            return png_path
        return os.path.join(icon_dir, f"{name}.jpg") # Fallback to JPG for screenshots

    def _fetch_states_background(self):
        """Fetches states in a background thread."""
        return fetch_states_map(
            self.config["base_url"],
            self.config["token"],
            timeout=10.0
        )

    def _execute_service_and_refresh_background(self, domain, service, entity_id, previous_state, favorite):
        """Executes a service call and refreshes states in a background thread."""
        call_service(
            self.config["base_url"],
            self.config["token"],
            domain,
            service,
            entity_id,
            timeout=10.0,
        )
        new_states = refresh_after_action(
            self.config["base_url"],
            self.config["token"],
            10.0,
            entity_id,
            previous_state,
        )
        return {"new_states": new_states, "favorite": favorite}

    def load_data(self):
        self.set_message("Loading...")
        self._start_background_task("load_data", self._fetch_states_background)

    def set_message(self, text):
        self.message = text
        self.message_time = time.time()

    def save_config(self):
        save_config(self.config_path, self.config)

    def load_entities(self):
        entities_by_domain = {}
        for entity_id, state in self.states.items():
            domain = entity_domain(entity_id)
            if domain not in SUPPORTED_ACTIONS:
                continue
            if domain not in entities_by_domain:
                entities_by_domain[domain] = []
            entities_by_domain[domain].append(
                {
                    "entity_id": entity_id,
                    "label": display_name(entity_id, state),
                    "state": str(state.get("state", "")),
                    "domain": domain,
                }
            )
        
        for domain in entities_by_domain:
            entities_by_domain[domain].sort(key=lambda item: (item["label"].lower(), item["entity_id"]))

        self.entities_by_domain = entities_by_domain
        self.domain_list = sorted(entities_by_domain.keys())
        self.selected_domain_index = 0
        self.domain_scroll = 0
        self.picker_scroll = 0
        self.selected_entity_in_domain_index = 0

    def get_domain_icon(self, entity_id):
        domain = entity_domain(entity_id)
        icons = {
            "light": "[L]",
            "switch": "[S]",
            "scene": "[Sce]",
            "script": "[Scr]",
            "sensor": "[#]",
            "binary_sensor": "[!]",
            "climate": "[T]"
        }
        return icons.get(domain, "[?]")

    def is_favorite(self, entity_id: str) -> bool:
        return any(favorite_entity_id(fav) == entity_id for fav in self.config.get("favorites", []))

    def toggle_favorite(self, entity_id: str) -> None:
        favorites = self.config.get("favorites", [])
        index = next((i for i, fav in enumerate(favorites) if favorite_entity_id(fav) == entity_id), None)
        if index is not None:
            del favorites[index]
            self.set_message("Favorite removed")
        else:
            favorites.append({"entity_id": entity_id, "label": "", "action": "auto"})
            self.set_message("Favorite added")
        self.config["favorites"] = favorites
        self.favorites = favorites
        self.save_config()

    def execute_action(self):
        if not self.favorites or self.selected >= len(self.favorites):
            return

        favorite = self.favorites[self.selected]
        entity_id = favorite_entity_id(favorite)
        action = favorite.get("action", "auto")

        resolved = resolve_action(entity_id, action)
        if resolved is None:
            self.set_message("Entity is read-only")
            return

        domain, service = resolved
        previous = self.states.get(entity_id)
        previous_state = str(previous.get("state", "")) if previous is not None else None

        self.set_message(f"Executing {service} on {entity_id}...")
        self._start_background_task(
            "execute_action",
            self._execute_service_and_refresh_background,
            domain, service, entity_id, previous_state, favorite
        )

    def handle_input(self):
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                # Keyboard logic remains mostly fixed as fallback
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    if self.mode == "favorites":
                        if self.favorites_editor_mode == "entities":
                            self.favorites_editor_mode = "domains"
                            self.set_message("Select a domain")
                        else:
                            self.mode = "main"
                            self.set_message("Favorites editor closed")
                    elif self.mode == "settings":
                        self.mode = "main"
                    else:
                        self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    if self.mode == "main":
                        self.active_list = "domains"
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.active_list = "entities"
                            self.entity_index = 0
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.nav_index = max(0, self.nav_index - 1)
                            self.entity_index = 0
                            self.entity_scroll_row = 0
                        else:
                            self.entity_index = max(0, self.entity_index - 1)
                            if self.entity_index < self.entity_scroll_row:
                                self.entity_scroll_row = self.entity_index
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = max(0, self.selected_domain_index - 3)
                            current_row = self.selected_domain_index // 3
                            if current_row < self.domain_scroll:
                                self.domain_scroll = current_row
                        elif self.mode == "settings":
                             self.settings_selected_index = max(0, self.settings_selected_index - 1)
                        else:
                            self.selected_entity_in_domain_index = max(0, self.selected_entity_in_domain_index - 1)
                            if self.selected_entity_in_domain_index < self.picker_scroll:
                                self.picker_scroll = self.selected_entity_in_domain_index
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            limit = len(self.domain_list) if self.domain_list else 1
                            self.nav_index = min(limit - 1, self.nav_index + 1)
                            self.entity_index = 0
                            self.entity_scroll_row = 0
                        else:
                            current_domain = self.domain_list[self.nav_index]
                            entities_count = len(self.entities_by_domain.get(current_domain, []))
                            self.entity_index = min(entities_count - 1, self.entity_index + 1)
                            visible_entities = 9
                            if self.entity_index >= self.entity_scroll_row + visible_entities:
                                self.entity_scroll_row = self.entity_index - visible_entities + 1
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 3)
                            current_row = self.selected_domain_index // 3
                            if current_row >= self.domain_scroll + 2:
                                self.domain_scroll = current_row - 1
                        elif self.mode == "settings":
                             self.settings_selected_index = min(1, self.settings_selected_index + 1)
                        else:
                            current_domain = self.domain_list[self.selected_domain_index]
                            entities_count = len(self.entities_by_domain.get(current_domain, []))
                            self.selected_entity_in_domain_index = min(entities_count - 1, self.selected_entity_in_domain_index + 1)
                        visible_rows = max((self.height - 90 - 60) // 28, 1)
                        if self.selected_entity_in_domain_index >= self.picker_scroll + visible_rows:
                            self.picker_scroll = self.selected_entity_in_domain_index - visible_rows + 1
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    if self.mode == "favorites" and self.favorites_editor_mode == "domains":
                        self.selected_domain_index = max(0, self.selected_domain_index - 1)
                        current_row = self.selected_domain_index // 3
                        if current_row < self.domain_scroll:
                            self.domain_scroll = current_row
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    if self.mode == "favorites" and self.favorites_editor_mode == "domains":
                        self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 1)
                        current_row = self.selected_domain_index // 3
                        if current_row >= self.domain_scroll + 2:
                            self.domain_scroll = current_row - 1
                elif event.key.keysym.sym in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
                    if self.mode == "main":
                        if self.active_list == "entities":
                            self._execute_entity_action()
                        else:
                            self.execute_action()
                    elif self.mode == "settings":
                        self._handle_settings_action()
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.favorites_editor_mode = "entities"
                            self.picker_scroll = 0
                            self.selected_entity_in_domain_index = 0
                        else:
                            current_domain = self.domain_list[self.selected_domain_index]
                            entities = self.entities_by_domain.get(current_domain, [])
                            if entities:
                                entity = entities[self.selected_entity_in_domain_index]
                                self.toggle_favorite(entity["entity_id"])
                elif event.key.keysym.sym == sdl2.SDLK_f:
                    if self.mode == "main":
                        self.mode = "favorites"
                        self.load_entities()
                        self.set_message("Edit favorites")
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    self.load_data()
                    self.set_message("Refreshed")
                elif event.key.keysym.sym == sdl2.SDLK_s:
                    self.mode = "settings"
            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                btn = event.cbutton.button
                if btn == self.controls["cancel"]:
                    if self.mode == "favorites":
                        if self.favorites_editor_mode == "entities":
                            self.favorites_editor_mode = "domains"
                            self.set_message("Select a domain")
                        else:
                            self.mode = "main"
                            self.set_message("Favorites editor closed")
                    elif self.mode == "settings":
                        self.mode = "main"
                    else:
                        self.running = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    if self.mode == "main":
                        self.active_list = "domains"
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.active_list = "entities"
                            self.entity_index = 0
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.nav_index = max(0, self.nav_index - 1)
                            self.entity_index = 0
                            self.entity_scroll_row = 0
                        else:
                            self.entity_index = max(0, self.entity_index - 1)
                            if self.entity_index < self.entity_scroll_row:
                                self.entity_scroll_row = self.entity_index
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = max(0, self.selected_domain_index - 3)
                            current_row = self.selected_domain_index // 3
                            if current_row < self.domain_scroll:
                                self.domain_scroll = current_row
                        elif self.mode == "settings":
                             self.settings_selected_index = max(0, self.settings_selected_index - 1)
                        else:
                            self.selected_entity_in_domain_index = max(0, self.selected_entity_in_domain_index - 1)
                            if self.selected_entity_in_domain_index < self.picker_scroll:
                                self.picker_scroll = self.selected_entity_in_domain_index
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    if self.mode == "main":
                        if self.active_list == "domains":
                            limit = len(self.domain_list) if self.domain_list else 1
                            self.nav_index = min(limit - 1, self.nav_index + 1)
                            self.entity_index = 0
                            self.entity_scroll_row = 0
                        else:
                            current_domain = self.domain_list[self.nav_index]
                            entities_count = len(self.entities_by_domain.get(current_domain, []))
                            self.entity_index = min(entities_count - 1, self.entity_index + 1)
                            visible_entities = 9
                            if self.entity_index >= self.entity_scroll_row + visible_entities:
                                self.entity_scroll_row = self.entity_index - visible_entities + 1
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 3)
                            current_row = self.selected_domain_index // 3
                            if current_row >= self.domain_scroll + 2:
                                self.domain_scroll = current_row - 1
                        elif self.mode == "settings":
                             self.settings_selected_index = min(1, self.settings_selected_index + 1)
                        else:
                            current_domain = self.domain_list[self.selected_domain_index]
                            entities_count = len(self.entities_by_domain.get(current_domain, []))
                            self.selected_entity_in_domain_index = min(entities_count - 1, self.selected_entity_in_domain_index + 1)
                        visible_rows = max((self.height - 90 - 60) // 28, 1)
                        if self.selected_entity_in_domain_index >= self.picker_scroll + visible_rows:
                            self.picker_scroll = self.selected_entity_in_domain_index - visible_rows + 1
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    if self.mode == "favorites" and self.favorites_editor_mode == "domains":
                        self.selected_domain_index = max(0, self.selected_domain_index - 1)
                        current_row = self.selected_domain_index // 3
                        if current_row < self.domain_scroll:
                            self.domain_scroll = current_row
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    if self.mode == "favorites" and self.favorites_editor_mode == "domains":
                        self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 1)
                        current_row = self.selected_domain_index // 3
                        if current_row >= self.domain_scroll + 2:
                            self.domain_scroll = current_row - 1
                elif btn == self.controls["confirm"]:
                    if self.mode == "main":
                        if self.active_list == "entities":
                            self._execute_entity_action()
                        else:
                            self.execute_action()
                    elif self.mode == "settings":
                        self._handle_settings_action()
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.favorites_editor_mode = "entities"
                            self.picker_scroll = 0
                            self.selected_entity_in_domain_index = 0
                        else:
                            current_domain = self.domain_list[self.selected_domain_index]
                            entities = self.entities_by_domain.get(current_domain, [])
                            if entities:
                                entity = entities[self.selected_entity_in_domain_index]
                                self.toggle_favorite(entity["entity_id"])
                elif btn == BTN_Y:  # Y button (North) -> Favorites
                    if self.mode == "main":
                        self.mode = "favorites"
                        self.load_entities()
                        self.set_message("Edit favorites")
                elif btn == BTN_X:  # X button (West) -> Refresh
                    self.load_data()
                    self.set_message("Refreshed")
                elif btn == sdl2.SDL_CONTROLLER_BUTTON_START:
                    self.mode = "settings"

    def _handle_settings_action(self):
        if self.settings_selected_index == 0:
            # Toggle layout
            new_layout = "spruce" if self.layout_type == "muos" else "muos"
            self.config["control_layout"] = new_layout
            self.setup_controls()
            self.save_config()
            self.set_message(f"Layout set to {new_layout.upper()}")
        else:
            self.mode = "main"
            self.set_message("Settings saved")

    def _render_button_icon(self, btn_id, x, y, size=20, color_mod=None):
        """Renders a graphical button icon from the loaded textures."""
        tex_name = self.btn_tex_map.get(btn_id)
        texture = self.domain_icons.get(tex_name)
        if texture:
            if color_mod:
                sdl2.SDL_SetTextureColorMod(texture, color_mod.r, color_mod.g, color_mod.b)
            dst = sdl2.SDL_Rect(x, y, size, size)
            sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
            if color_mod:
                sdl2.SDL_SetTextureColorMod(texture, 255, 255, 255)
            return size
        return 0

    def render(self):
        self.ui.clear_screen()
        if self.mode == "main":
            self.render_layout()
        elif self.mode == "settings":
            self.render_settings()
        else:
            self.render_favorites_editor()
        sdl2.SDL_RenderPresent(self.renderer)

    def render_layout(self):
        """Divides the screen into 5 zones (Header, Nav, Main, Info, Log)."""
        # 1. Top-Bar (Header) - Now a box and slightly larger
        self.ui.draw_retro_box(10, 5, 620, 55, "SYSTEM")

        # Logo and title
        logo_tex = self.domain_icons.get("ha_logo")
        logo_w = 0
        if logo_tex:
            logo_w = 28
            dst = sdl2.SDL_Rect(25, 18, logo_w, logo_w)
            sdl2.SDL_RenderCopy(self.renderer, logo_tex, None, dst)
            logo_w += 10 # spacing

        self.ui.draw_text("for retroconsoles", 25 + logo_w, 15, COLOR_HA_BLUE, large=True)

        # 2. Left column (Navigation) - Shifted down
        self.ui.draw_retro_box(10, 70, 190, 290, "DOMAINS")
        self.draw_menu(25, 100)

        # 3. Main area (Middle) - Shifted down
        self.ui.draw_retro_box(210, 70, 260, 290, "ENTITIES")
        self._render_entities_list(225, 100)

        # 4. Right column (Info boxes) - Shifted down
        self.ui.draw_retro_box(480, 70, 150, 140, "PREVIEW")
        # Placeholder for graphic/icon
        self.ui.draw_retro_box(480, 220, 150, 140, "STATS")
        self.ui.draw_text("CPU: 12%", 490, 250, "gray", small=True)
        self.ui.draw_text("RAM: 45MB", 490, 275, "gray", small=True)

        # 5. Bottom row (Console/Status) - Renamed and includes clock
        self.ui.draw_retro_box(10, 370, 620, 105, "Console")
        
        # Show message with timeout and error color logic
        is_error = self.message.startswith("Error")
        display_time = 5.0 if is_error else 1.0
        if self.message and (time.time() - self.message_time < display_time):
            msg_color = COLOR_TEXT_DIM if is_error else "white"
            self.ui.draw_text(self.message, 25, 395, msg_color, small=True)

        # Date moved inside the Console box
        self.ui.draw_text("STATUS: ONLINE // IP: 192.168.1.42", 25, 450, "gray", small=True)
        date_str = time.strftime("%Y-%m-%d %H:%M:%S")
        self.ui.draw_text(date_str, 450, 450, "gray", small=True)

    def draw_menu(self, x, y_start):
        """Draws the navigation menu with pointer and highlight."""
        if not self.domain_list:
            self.ui.draw_text("Loading...", x, y_start, "cyan")
            return

        for i, domain in enumerate(self.domain_list):
            y_pos = y_start + (i * 40)
            label = domain.capitalize()
            
            # Search for icon in self.domain_icons
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_w = 0
            if icon_tex:
                icon_w = 24
                # Render icon slightly vertically offset
                dst = sdl2.SDL_Rect(x, y_pos + 2, icon_w, icon_w)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                icon_w += 10 # Spacing to text
            
            if i == self.nav_index:
                # 1. Highlight background
                self.ui.draw_selection_highlight(x - 10, y_pos - 5, 170, 35)
                
                # 1.1 Border around selection (1px rounded, same color as pointer)
                self.ui.draw_rounded_rect(x - 10, y_pos - 5, 170, 35, "cyan")
                
                # 2. Selection triangle (pointer) - Only if domains list is active
                if self.active_list == "domains":
                    self.ui.draw_pointer(x - 18, y_pos + 4, width=12, height=18)
                
                # 3. Active text
                self.ui.draw_text(label, x + icon_w, y_pos + 5, "white")
            else:
                # Normal text
                self.ui.draw_text(label, x + icon_w, y_pos + 5, "cyan")

    def _render_entities_list(self, x, y_start):
        """Renders the list of entities for the currently selected domain."""
        if not self.domain_list or self.nav_index >= len(self.domain_list):
            self.ui.draw_text("Waiting for data...", x, y_start, "gray", small=True)
            return
            
        current_domain = self.domain_list[self.nav_index]
        entities = self.entities_by_domain.get(current_domain, [])
        visible_entities = 9
        start = self.entity_scroll_row
        end = min(len(entities), start + visible_entities)
        
        for i in range(start, end):
            entity = entities[i]
            y = y_start + ((i - start) * 28)
            
            # Selection visuals
            is_selected = (self.active_list == "entities" and i == self.entity_index)
            if is_selected:
                self.ui.draw_selection_highlight(x - 10, y - 3, 240, 24)
                self.ui.draw_rounded_rect(x - 10, y - 3, 240, 24, "cyan")
                self.ui.draw_pointer(x - 18, y + 3, width=12, height=18)
            
            # Icon
            domain = entity["domain"]
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_offset = 0
            
            # Live-Status abrufen (Snapshot in entity["state"] ist nach Aktionen veraltet)
            is_on = self.states.get(entity["entity_id"], {}).get("state") == "on"
            
            is_fav = self.is_favorite(entity["entity_id"])

            if icon_tex:
                icon_offset = 20
                
                # Icons je nach Status einfärben
                icon_color = COLOR_YELLOW if is_on else COLOR_GREY
                sdl2.SDL_SetTextureColorMod(icon_tex, icon_color.r, icon_color.g, icon_color.b)

                dst = sdl2.SDL_Rect(x, y + 2, icon_offset, icon_offset)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255) # Reset auf Standardweiß
                icon_offset += 8
                
            color = "yellow" if (is_fav or is_selected) else "white"
            
            self.ui.draw_text(entity['label'][:18], x + icon_offset, y + 2, color, small=True)

        # Scrollbar für die Entitäten-Liste
        if len(entities) > visible_entities:
            self.ui.draw_scrollbar(
                x + 235, y_start, 250, 
                self.entity_scroll_row, len(entities), visible_entities
            )

    def render_main(self):
        margin = 20
        cols = 2
        card_w = (self.width - (2 * margin) - 20) // cols
        card_h = 70
        
        if not self.favorites:
            self.ui.draw_text("No favorites configured. Press Y to edit.", 20, 80, COLOR_TEXT)
            return

        # Update scroll offset based on selection
        current_row = self.selected // cols
        if current_row < self.main_scroll_row:
            self.main_scroll_row = current_row
        elif current_row >= self.main_scroll_row + 4:
            self.main_scroll_row = current_row - 3

        for i, fav in enumerate(self.favorites):
            row = (i // cols) - self.main_scroll_row
            col = i % cols
            if row < 0 or row >= 5: continue # Only render visible rows

            x = margin + col * (card_w + 20)
            y = 70 + row * (card_h + 15)
            
            entity_id = favorite_entity_id(fav)
            state = self.states.get(entity_id, {})
            self._render_favorite_card(i, fav, entity_id, state, x, y, card_w, card_h)

        # Message above keybindings/version
        # Show message for 1 second (or 5 if it's an error)
        is_error = self.message.startswith("Error")
        display_time = 5.0 if is_error else 1.0
        if self.message and (time.time() - self.message_time < display_time):
            self.ui.draw_text(self.message, 20, self.height - 40, COLOR_TEXT_DIM if is_error else COLOR_TEXT, small=True)

        # Footer with icons
        self._render_footer_line()
        self.ui.draw_text(f"v.{VERSION}", self.width - 60, self.height - 20, COLOR_TEXT_DIM, small=True)

    def _render_footer_line(self):
        """Helper to render a consistent footer with graphical icons."""
        x = 20
        y = self.height - 22
        
        parts = [
            ("D-Pad: Navigate | ", None),
            ("", self.controls["confirm"]),
            (": Execute | ", None),
            ("", BTN_Y),
            (": Favorites | ", None),
            ("", BTN_X),
            (": Refresh | ", None),
            ("", self.controls["cancel"]),
            (": Exit", None)
        ]
        
        for text, btn_id in parts:
            if text:
                w, _ = self.ui.draw_text(text, x, y + 2, "cyan", small=True)
                x += w
            if btn_id is not None:
                x += self._render_button_icon(btn_id, x, y, size=18)

    def render_settings(self):
        y_offset = 80
        if self.settings_selected_index == 0:
            self.render_selection_bar(10, y_offset - 2, self.width - 20, 40)
        
        # Render Layout Option Piece by Piece
        color = COLOR_HIGHLIGHT if self.settings_selected_index == 0 else COLOR_TEXT
        text = f"Button Layout: {self.layout_type.upper()} ("
        self.ui.draw_text(text, 30, y_offset, color)
        
        text_w, _ = self.ui.get_text_size(text)
        icon_x = 30 + text_w
        icon_w = self._render_button_icon(self.controls["confirm"], icon_x, y_offset + 4, size=24)
        
        self.ui.draw_text(" = Confirm)", icon_x + icon_w, y_offset, color)
        
        # Back Option
        y_offset += 40
        if self.settings_selected_index == 1:
            self.render_selection_bar(10, y_offset - 2, self.width - 20, 40)
        color = COLOR_HIGHLIGHT if self.settings_selected_index == 1 else COLOR_TEXT
        self.ui.draw_text("Back to Main Menu", 30, y_offset, color)

        self.ui.draw_text("D-Pad: Select | Start: Apply/Back", 20, self.height - 20, COLOR_TEXT, small=True)
        self.ui.draw_text(f"v.{VERSION}", self.width - 60, self.height - 20, COLOR_TEXT_DIM, small=True)

    def render_favorites_editor(self):
        if self.favorites_editor_mode == "domains":
            self._render_domain_selection()
        else: # self.favorites_editor_mode == "entities"
            self._render_entity_selection_for_domain()

        # Common footer for favorites editor
        if self.message and (time.time() - self.message_time < 1.0):
            self.ui.draw_text(self.message, 20, self.height - 40, COLOR_TEXT, small=True)

        x = 20
        y = self.height - 22
        if self.favorites_editor_mode == "domains":
            msg = "D-Pad: Navigate | "
            w, _ = self.ui.draw_text(msg, x, y + 2, COLOR_TEXT, small=True)
            x += w
            x += self._render_button_icon(self.controls["confirm"], x, y, 18)
            msg = ": Select domain | "
            w, _ = self.ui.draw_text(msg, x, y + 2, COLOR_TEXT, small=True)
            x += w
            x += self._render_button_icon(self.controls["cancel"], x, y, 18)
            self.ui.draw_text(": Back", x, y + 2, COLOR_TEXT, small=True)
        else: # entities mode
            msg = "D-Pad: Navigate | "
            w, _ = self.ui.draw_text(msg, x, y + 2, COLOR_TEXT, small=True)
            x += w
            x += self._render_button_icon(self.controls["confirm"], x, y, 18)
            self.ui.draw_text(": Toggle Favorite", x, y + 2, COLOR_TEXT, small=True)

        self.ui.draw_text(f"v.{VERSION}", self.width - 60, self.height - 20, COLOR_TEXT_DIM, small=True)

    def _render_favorite_card(self, index, fav, entity_id, state, x, y, w, h):
        selected = (index == self.selected)
        state_str = state.get('state', 'unknown')
        label = favorite_label(fav, state)
        domain = entity_domain(entity_id)
        color_key = "yellow" if selected else "cyan"

        # Use the cyber box with the entity domain as title
        # If 'selected', draw a yellow box
        self.ui.draw_retro_box(x, y, w, h, title=domain.upper(), color=color_key)
        
        state_color = COLOR_YELLOW if state_str == "on" else COLOR_GREY

        # Icon
        icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
        icon_tex = self.domain_icons.get(icon_key)
        if icon_tex:
            # Apply color to icon
            sdl2.SDL_SetTextureColorMod(icon_tex, state_color.r, state_color.g, state_color.b)
            dst = sdl2.SDL_Rect(x + 10, y + (h - 32) // 2, 32, 32)
            sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)
            self.ui.draw_text(label, x + 50, y + 15, color_key, small=True)
        else:
            self.ui.draw_text(label, x + 10, y + 15, color_key, small=True)

        self.ui.draw_text(state_str.upper(), x + 50, y + 38, "gray" if state_str != "on" else "yellow", small=True)

    def _render_domain_selection(self):
        y_start = 80
        x_start = 20
        icon_size = 80
        cols = 3
        
        if not self.domain_list:
            self.ui.draw_text("No domains with supported actions found.", x_start, y_start, COLOR_TEXT)
            return

        total_rows = (len(self.domain_list) + cols - 1) // cols
        start_index = self.domain_scroll * cols
        end_index = min(len(self.domain_list), start_index + 6) # Render 2 rows (6 items)

        for i in range(start_index, end_index):
            domain = self.domain_list[i]
            row = (i // cols) - self.domain_scroll
            col = i % cols
            
            cell_width = (self.width - 2 * x_start) // cols
            cell_height = icon_size + 45
            
            x_center_of_cell = x_start + col * cell_width + cell_width // 2
            y_center_of_cell = y_start + row * cell_height + cell_height // 2

            icon_x = x_center_of_cell - icon_size // 2
            icon_y = y_center_of_cell - icon_size // 2 - 10

            text_y = icon_y + icon_size + 8
            
            if i == self.selected_domain_index:
                selection_rect_padding = 15
                selection_rect = sdl2.SDL_Rect(
                    icon_x - selection_rect_padding, 
                    icon_y - selection_rect_padding, 
                    icon_size + 2 * selection_rect_padding, 
                    icon_size + 2 * selection_rect_padding + 25
                )
                sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 30, 60, 255)
                sdl2.SDL_RenderFillRect(self.renderer, selection_rect)
                
                # Rounded selection frame
                self.ui.draw_rounded_rect(selection_rect.x, selection_rect.y, selection_rect.w, selection_rect.h, COLOR_HIGHLIGHT)
                self.ui.draw_rounded_rect(selection_rect.x + 1, selection_rect.y + 1, selection_rect.w - 2, selection_rect.h - 2, COLOR_HIGHLIGHT)

            icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
            icon_tex = self.domain_icons.get(icon_key)
            if icon_tex:
                dst = sdl2.SDL_Rect(icon_x, icon_y, icon_size, icon_size)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            else:
                w, h = self.ui.get_text_size(domain)
                self.ui.draw_text(domain, icon_x + (icon_size - w) // 2, icon_y + (icon_size - h) // 2, COLOR_TEXT)
            
            text_label = domain.capitalize()
            w_small, _ = self.ui.get_text_size(text_label, small=True)
            self.ui.draw_text(text_label, icon_x + (icon_size - w_small) // 2, text_y, COLOR_TEXT, small=True)

        # Draw Scrollbar
        if total_rows > 2:
            scrollbar_x = self.width - 15
            scrollbar_y_top = 80
            scrollbar_h = 250
            
            # Background
            sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
            sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(scrollbar_x, scrollbar_y_top, 5, scrollbar_h))
            
            # Handle
            handle_h = max(30, int(scrollbar_h * (2 / total_rows)))
            scroll_progress = self.domain_scroll / (total_rows - 2)
            handle_y = scrollbar_y_top + int((scrollbar_h - handle_h) * scroll_progress)
            sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_HIGHLIGHT.r, COLOR_HIGHLIGHT.g, COLOR_HIGHLIGHT.b, 255)
            sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(scrollbar_x, handle_y, 5, handle_h))

    def _render_entity_selection_for_domain(self):
        if not self.domain_list:
            self.ui.draw_text("No domains found.", 20, 70, COLOR_TEXT)
            return

        current_domain = self.domain_list[self.selected_domain_index]
        current_entities = self.entities_by_domain.get(current_domain, [])
        
        self.ui.draw_text(f"Domain: {current_domain.capitalize()}", 20, 70, COLOR_HIGHLIGHT)
        
        y = 100
        visible_rows = max((self.height - y - 60) // 28, 1)
        start = self.picker_scroll
        end = min(len(current_entities), start + visible_rows)
        
        favorite_ids = {favorite_entity_id(fav) for fav in self.favorites}

        if not current_entities:
            self.ui.draw_text("No entities in this domain.", 20, y, COLOR_TEXT)
            return

        for i in range(start, end):
            entity = current_entities[i]

            if i == self.selected_entity_in_domain_index:
                self.render_selection_bar(10, y - 2, self.width - 20, 26)
                
            color = COLOR_HIGHLIGHT if i == self.selected_entity_in_domain_index else COLOR_TEXT
            domain = entity["domain"]
            # Live-Status für den Favoriten-Editor abrufen
            state_str = self.states.get(entity["entity_id"], {}).get("state", "unknown")
            
            # Render favorite marker icon
            favorite_icon_key = "binary_sensor_on" if entity["entity_id"] in favorite_ids else "binary_sensor_off"
            favorite_icon_tex = self.domain_icons.get(favorite_icon_key)
            if favorite_icon_tex:
                fav_dst = sdl2.SDL_Rect(15, y, 20, 20) # Position for favorite marker
                sdl2.SDL_RenderCopy(self.renderer, favorite_icon_tex, None, fav_dst)
            else:
                # Fallback if binary_sensor icons are not found (should not happen if assets are correct)
                marker = "*" if entity["entity_id"] in favorite_ids else " "
                self.ui.draw_text(f"[{marker}]", 15, y, color)

            # In picker, we prefer the 'on' icon as the representative version
            icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
            icon_tex = self.domain_icons.get(icon_key)
            
            if icon_tex:
                # Apply color mod based on actual entity state in picker too
                if state_str == "on":
                    if domain == "light":
                        sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 0)
                else:
                    sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)

                dst = sdl2.SDL_Rect(45, y, 20, 20)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)
                self.ui.draw_text(entity['label'], 75, y, color)
            else:
                icon_text = self.get_domain_icon(entity["entity_id"])
                self.ui.draw_text(f"{icon_text} {entity['label']}", 45, y, color) # Adjusted x-position

            self.ui.draw_text(entity['state'], self.width - 100, y + 4, COLOR_TEXT_DIM, small=True)
            y += 28

    def run(self):
        self.init_sdl()
        self.load_data()

        # Process initial load_data result immediately if available
        try:
            task_result = self.task_queue.get_nowait()
            self.current_task_thread = None
            self.pending_task_type = None
            if task_result["status"] == "success" and task_result["type"] == "load_data":
                self.states = task_result["result"]
                self.set_message("Connected")
                if self.mode == "favorites":
                    self.load_entities()
            elif task_result["status"] == "error":
                self.set_message(f"Error: {task_result['error']}")
        except queue.Empty:
            pass

        while self.running:
            self.handle_input()

            # Process results from background tasks
            try:
                task_result = self.task_queue.get_nowait()
                self.current_task_thread = None  # Task finished
                self.pending_task_type = None
                self._process_task_result(task_result)
            except queue.Empty:
                pass  # No task results yet

            self.render()
            sdl2.SDL_Delay(16)
        self.cleanup()

    def cleanup(self):
        if self.ui:
            self.ui.cleanup()
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
        for tex in self.domain_icons.values():
            sdl2.SDL_DestroyTexture(tex)
        for controller in self.game_controllers:
            sdl2.SDL_GameControllerClose(controller)
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        ttf.TTF_Quit()
        sdlimage.IMG_Quit()
        sdl2.SDL_Quit()

    def _process_task_result(self, task_result):
        """Handles the result of a completed background task."""
        if task_result["status"] == "success":
            if task_result["type"] == "load_data":
                self.states = task_result["result"]
                self.set_message("Connected")
                self.load_entities()
            elif task_result["type"] == "execute_action":
                new_states = task_result["result"]["new_states"]
                favorite = task_result["result"]["favorite"]
                before_states = self.states  # Capture states before update
                self.states = new_states
                if favorite:
                    changes = changed_favorites([favorite], before_states, self.states)
                    self.set_message(f"Executed: {changes[0]}" if changes else "Executed")
                else:
                    self.set_message("Executed")
        else:  # status == "error"
            self.set_message(f"Error: {task_result['error']}")

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    
    config_path = Path(args.config)
    app = HASDL2App(config_path)
    app.run()