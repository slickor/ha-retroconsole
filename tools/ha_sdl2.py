import sys
import os
import time
import threading
import queue
import ctypes
sys.path.insert(0, os.path.dirname(__file__) + "/..")

import sdl2
import sdl2.ext
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as ttf

from ha_client import (
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

VERSION = "0.6.5"

# Farben (SDL2 RGB)
COLOR_BG = sdl2.SDL_Color(0, 0, 0, 255)
COLOR_TEXT = sdl2.SDL_Color(255, 255, 255, 255)
COLOR_TEXT_DIM = sdl2.SDL_Color(150, 150, 150, 255)
COLOR_HIGHLIGHT = sdl2.SDL_Color(255, 255, 0, 255)
COLOR_SUCCESS = sdl2.SDL_Color(0, 255, 100, 255)
COLOR_SELECTION_BG = sdl2.SDL_Color(50, 50, 50, 255)
COLOR_BORDER = sdl2.SDL_Color(128, 128, 128, 255)

class HASDL2App:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.states = {}
        self.favorites = self.config.get("favorites", [])
        self.entities = []
        self.selected = 0 # For main menu favorites
        self.mode = "main" # "main" or "favorites"
        self.favorites_editor_mode = "domains" # "domains" or "entities"
        self.selected_domain_index = 0 # For domain selection in favorites editor
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
        self.font = None
        self.font_small = None
        self.domain_icons = {}  # Cache for loaded textures
        self.entities_by_domain = {} # Grouped entities for favorites editor
        self.domain_list = [] # List of domains for favorites editor
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.game_controllers = []

    def init_sdl(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER)
        sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG)
        ttf.TTF_Init()
        self.window = sdl2.SDL_CreateWindow(
            b"Home Assistant - for retroconsoles", 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            self.width, self.height, sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        )
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
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
            font = ttf.TTF_OpenFont(candidate.encode("utf-8"), 24)
            if font:
                selected_font = candidate
                self.font = font
                break
        if not self.font:
            raise SystemExit("Could not load any font. Ensure assets/fonts/DejaVuSans.ttf exists or system fonts are available.")

        self.font_small = ttf.TTF_OpenFont(selected_font.encode("utf-8"), 16)
        if not self.font_small:
            raise SystemExit(f"Could not load small font from: {selected_font}")

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
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    if self.mode == "favorites":
                        if self.favorites_editor_mode == "entities":
                            self.favorites_editor_mode = "domains"
                            self.set_message("Select a domain")
                        else:
                            self.mode = "main"
                            self.set_message("Favorites editor closed")
                    else:
                        self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    if self.mode == "main":
                        self.selected = max(0, self.selected - 1)
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = max(0, self.selected_domain_index - 3)
                            current_row = self.selected_domain_index // 3
                            if current_row < self.domain_scroll:
                                self.domain_scroll = current_row
                        else:
                            self.selected_entity_in_domain_index = max(0, self.selected_entity_in_domain_index - 1)
                            if self.selected_entity_in_domain_index < self.picker_scroll:
                                self.picker_scroll = self.selected_entity_in_domain_index
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    if self.mode == "main":
                        self.selected = min(len(self.favorites) - 1, self.selected + 1)
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 3)
                            current_row = self.selected_domain_index // 3
                            if current_row >= self.domain_scroll + 2:
                                self.domain_scroll = current_row - 1
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
                        self.execute_action()
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
            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_B:  # B button (East) -> Back/Quit
                    if self.mode == "favorites":
                        if self.favorites_editor_mode == "entities":
                            self.favorites_editor_mode = "domains"
                            self.set_message("Select a domain")
                        else:
                            self.mode = "main"
                            self.set_message("Favorites editor closed")
                    else:
                        self.running = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    if self.mode == "main":
                        self.selected = max(0, self.selected - 1)
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = max(0, self.selected_domain_index - 3)
                            current_row = self.selected_domain_index // 3
                            if current_row < self.domain_scroll:
                                self.domain_scroll = current_row
                        else:
                            self.selected_entity_in_domain_index = max(0, self.selected_entity_in_domain_index - 1)
                            if self.selected_entity_in_domain_index < self.picker_scroll:
                                self.picker_scroll = self.selected_entity_in_domain_index
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    if self.mode == "main":
                        self.selected = min(len(self.favorites) - 1, self.selected + 1)
                    elif self.mode == "favorites":
                        if self.favorites_editor_mode == "domains":
                            self.selected_domain_index = min(len(self.domain_list) - 1, self.selected_domain_index + 3)
                            current_row = self.selected_domain_index // 3
                            if current_row >= self.domain_scroll + 2:
                                self.domain_scroll = current_row - 1
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
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:  # A button (South) -> Select/Execute
                    if self.mode == "main":
                        self.execute_action()
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
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_Y:  # Y button (North) -> Favorites
                    if self.mode == "main":
                        self.mode = "favorites"
                        self.load_entities()
                        self.set_message("Edit favorites")
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_X:  # X button (West) -> Refresh
                    self.load_data()
                    self.set_message("Refreshed")

    def render_text(self, text, x, y, color):
        if not self.font:
            return
        surface = ttf.TTF_RenderText_Solid(self.font, text.encode('utf-8'), color)
        if not surface:
            return
        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        if not texture:
            sdl2.SDL_FreeSurface(surface)
            return
        w, h = surface.contents.w, surface.contents.h
        dst = sdl2.SDL_Rect(x, y, w, h)
        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
        sdl2.SDL_FreeSurface(surface)
        sdl2.SDL_DestroyTexture(texture)

    def render_text_small(self, text, x, y, color):
        if not self.font_small:
            return
        surface = ttf.TTF_RenderText_Solid(self.font_small, text.encode('utf-8'), color)
        if not surface:
            return
        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
        if not texture:
            sdl2.SDL_FreeSurface(surface)
            return
        w, h = surface.contents.w, surface.contents.h
        dst = sdl2.SDL_Rect(x, y, w, h)
        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
        sdl2.SDL_FreeSurface(surface)
        sdl2.SDL_DestroyTexture(texture)

    def render_selection_bar(self, y, height=30):
        rect = sdl2.SDL_Rect(10, y - 2, self.width - 20, height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_SELECTION_BG.r, COLOR_SELECTION_BG.g, COLOR_SELECTION_BG.b, 255)
        sdl2.SDL_RenderFillRect(self.renderer, rect)

    def render(self):
        sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_BG.r, COLOR_BG.g, COLOR_BG.b, COLOR_BG.a)
        sdl2.SDL_RenderClear(self.renderer)

        # Header
        title = "Home Assistant - for retroconsoles" 
        if self.mode == "favorites":
            title = "Favorites Editor"
        self.render_text(title, 20, 20, COLOR_HIGHLIGHT)
        
        # Divider below header
        sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_BORDER.r, COLOR_BORDER.g, COLOR_BORDER.b, 255)
        sdl2.SDL_RenderDrawLine(self.renderer, 0, 55, self.width, 55)

        if self.mode == "main":
            self.render_main()
        else:
            self.render_favorites_editor()

        sdl2.SDL_RenderPresent(self.renderer)

    def render_main(self):
        y_offset = 60
        if not self.favorites:
            self.render_text("No favorites configured. Press Y to edit.", 20, y_offset, COLOR_TEXT)
            y_offset += 30
        for i, fav in enumerate(self.favorites):
            entity_id = favorite_entity_id(fav)
            state = self.states.get(entity_id, {})
            state_str = state.get('state', 'unknown')
            label = favorite_label(fav, state)
            domain = entity_domain(entity_id)
            
            self._render_favorite_item(i, fav, entity_id, state, state_str, label, domain, y_offset)
            y_offset += 30

        # Message above keybindings/version
        # Show message for 1 second (or 5 if it's an error)
        is_error = self.message.startswith("Error")
        display_time = 5.0 if is_error else 1.0
        if self.message and (time.time() - self.message_time < display_time):
            self.render_text_small(self.message, 20, self.height - 40, COLOR_TEXT_DIM if is_error else COLOR_TEXT)

        self.render_text_small("D-Pad: Navigate | A: Execute | Y: Favorites | X: Refresh | B: Exit", 20, self.height - 20, COLOR_TEXT)
        self.render_text_small(f"v.{VERSION}", self.width - 60, self.height - 20, COLOR_TEXT_DIM)

    def render_favorites_editor(self):
        if self.favorites_editor_mode == "domains":
            self._render_domain_selection()
        else: # self.favorites_editor_mode == "entities"
            self._render_entity_selection_for_domain()

        # Common footer for favorites editor
        if self.message and (time.time() - self.message_time < 1.0):
            self.render_text_small(self.message, 20, self.height - 40, COLOR_TEXT)

        if self.favorites_editor_mode == "domains":
            self.render_text_small("D-Pad: Navigate | A: Select domain | B: Back to main | X: Refresh", 20, self.height - 20, COLOR_TEXT)
        else: # entities mode
            self.render_text_small("D-Pad: Navigate | A: Toggle favorite | B: Back to domains | X: Refresh", 20, self.height - 20, COLOR_TEXT)

        self.render_text_small(f"v.{VERSION}", self.width - 60, self.height - 20, COLOR_TEXT_DIM)

    def _render_favorite_item(self, index, fav, entity_id, state, state_str, label, domain, y_pos):
        if index == self.selected:
            self.render_selection_bar(y_pos)
        
        color = COLOR_HIGHLIGHT if index == self.selected else COLOR_TEXT
        state_color = COLOR_SUCCESS if state_str == "on" else COLOR_TEXT_DIM
        
        icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
        icon_tex = self.domain_icons.get(icon_key)
        
        if icon_tex:
            if state_str == "on":
                if domain == "light":
                    sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_HIGHLIGHT.r, COLOR_HIGHLIGHT.g, COLOR_HIGHLIGHT.b)
                else:
                    sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_SUCCESS.r, COLOR_SUCCESS.g, COLOR_SUCCESS.b)
            else:
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)

            dst = sdl2.SDL_Rect(25, y_pos, 24, 24)
            sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)
            self.render_text(label, 60, y_pos, color)
        else:
            icon_text = self.get_domain_icon(entity_id)
            self.render_text(f"{icon_text} {label}", 25, y_pos, color)

        self.render_text_small(state_str, self.width - 100, y_pos + 4, state_color)

    def _render_domain_selection(self):
        y_start = 80
        x_start = 20
        icon_size = 80
        cols = 3
        
        if not self.domain_list:
            self.render_text("No domains with supported actions found.", x_start, y_start, COLOR_TEXT)
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
                sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_SELECTION_BG.r, COLOR_SELECTION_BG.g, COLOR_SELECTION_BG.b, 255)
                sdl2.SDL_RenderFillRect(self.renderer, selection_rect)
                sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_HIGHLIGHT.r, COLOR_HIGHLIGHT.g, COLOR_HIGHLIGHT.b, 255)
                # Draw a thicker border by rendering two rectangles
                sdl2.SDL_RenderDrawRect(self.renderer, selection_rect)
                inner_rect = sdl2.SDL_Rect(selection_rect.x + 1, selection_rect.y + 1, selection_rect.w - 2, selection_rect.h - 2)
                sdl2.SDL_RenderDrawRect(self.renderer, inner_rect)

            icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
            icon_tex = self.domain_icons.get(icon_key)
            if icon_tex:
                dst = sdl2.SDL_Rect(icon_x, icon_y, icon_size, icon_size)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            else:
                w, h = ctypes.c_int(), ctypes.c_int()
                ttf.TTF_SizeText(self.font, domain.encode('utf-8'), ctypes.byref(w), ctypes.byref(h))
                text_width, text_height = w.value, h.value
                self.render_text(domain, icon_x + (icon_size - text_width) // 2, icon_y + (icon_size - text_height) // 2, COLOR_TEXT)
            
            text_label = domain.capitalize()
            w_small, h_small = ctypes.c_int(), ctypes.c_int()
            ttf.TTF_SizeText(self.font_small, text_label.encode('utf-8'), ctypes.byref(w_small), ctypes.byref(h_small))
            text_width_small = w_small.value
            self.render_text_small(text_label, icon_x + (icon_size - text_width_small) // 2, text_y, COLOR_TEXT)

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
            self.render_text("No domains found.", 20, 70, COLOR_TEXT)
            return

        current_domain = self.domain_list[self.selected_domain_index]
        current_entities = self.entities_by_domain.get(current_domain, [])
        
        self.render_text(f"Domain: {current_domain.capitalize()}", 20, 70, COLOR_HIGHLIGHT)
        
        y = 100
        visible_rows = max((self.height - y - 60) // 28, 1)
        start = self.picker_scroll
        end = min(len(current_entities), start + visible_rows)
        
        favorite_ids = {favorite_entity_id(fav) for fav in self.favorites}

        if not current_entities:
            self.render_text("No entities in this domain.", 20, y, COLOR_TEXT)
            return

        for i in range(start, end):
            entity = current_entities[i]

            if i == self.selected_entity_in_domain_index:
                self.render_selection_bar(y, height=26)
                
            color = COLOR_HIGHLIGHT if i == self.selected_entity_in_domain_index else COLOR_TEXT
            domain = entity["domain"]
            state_str = entity["state"]
            
            # Render favorite marker icon
            favorite_icon_key = "binary_sensor_on" if entity["entity_id"] in favorite_ids else "binary_sensor_off"
            favorite_icon_tex = self.domain_icons.get(favorite_icon_key)
            if favorite_icon_tex:
                fav_dst = sdl2.SDL_Rect(15, y, 20, 20) # Position for favorite marker
                sdl2.SDL_RenderCopy(self.renderer, favorite_icon_tex, None, fav_dst)
            else:
                # Fallback if binary_sensor icons are not found (should not happen if assets are correct)
                marker = "*" if entity["entity_id"] in favorite_ids else " "
                self.render_text(f"[{marker}]", 15, y, color)

            # In picker, we prefer the 'on' icon as the representative version
            icon_key = f"{domain}_on" if f"{domain}_on" in self.domain_icons else domain
            icon_tex = self.domain_icons.get(icon_key)
            
            if icon_tex:
                # Apply color mod based on actual entity state in picker too
                if state_str == "on":
                    if domain == "light":
                        sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_HIGHLIGHT.r, COLOR_HIGHLIGHT.g, COLOR_HIGHLIGHT.b)
                    else:
                        sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_SUCCESS.r, COLOR_SUCCESS.g, COLOR_SUCCESS.b)
                else:
                    sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)

                dst = sdl2.SDL_Rect(45, y, 20, 20)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)
                self.render_text(entity['label'], 75, y, color)
            else:
                icon_text = self.get_domain_icon(entity["entity_id"])
                self.render_text(f"{icon_text} {entity['label']}", 45, y, color) # Adjusted x-position

            self.render_text_small(entity['state'], self.width - 100, y + 4, COLOR_TEXT_DIM)
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
        if self.font:
            ttf.TTF_CloseFont(self.font)
        if self.font_small:
            ttf.TTF_CloseFont(self.font_small)
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
                if self.mode == "favorites":
                    self.load_entities()
            elif task_result["type"] == "execute_action":
                new_states = task_result["result"]["new_states"]
                favorite = task_result["result"]["favorite"]
                before_states = self.states  # Capture states before update
                self.states = new_states
                changes = changed_favorites([favorite], before_states, self.states)
                self.set_message(f"Executed: {changes[0]}" if changes else "Executed")
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