import sys
import os
import time
import threading
import socket
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
    get_domain_groups,
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
COLOR_BG = sdl2.SDL_Color(10, 10, 15, 255)      # Beispiel: Etwas helleres Midnight Blue
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
        self.settings_selected_index = 0
        self.entity_scroll_row = 0 # Scroll position for main entity list
        self.setup_controls()
        self.ip_address = self._get_ip_address()
        self.running = True
        self.selection_start_time = time.time()
        self.visible_entities = 13 # Number of entities visible in the list
        self.fav_flash_time = 0
        self.reorder_mode = False
        self.log_entries = [] # List of (timestamp, text, color)
        self.log_scroll = 0
        self.trigger_l_pressed = False
        self.trigger_r_pressed = False
        self.width = 640
        self.height = 480
        self.window = None
        self.renderer = None
        self.ui = None
        self.domain_icons = {} # Cache for loaded textures
        self.entities_by_domain = {} # Cached grouped entities
        self.domain_list = [] # List of domains for favorites editor
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.game_controllers = []
        self.last_y_label = ""
        self.controls_flash_time = 0

    def _get_system_stats(self):
        """Fetches real CPU MHz and Free RAM on Linux devices."""
        cpu_mhz = "N/A"
        free_mem = "N/A"
        
        # Get CPU Frequency (Linux)
        freq_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        if os.path.exists(freq_path):
            with open(freq_path, "r") as f:
                cpu_mhz = f"{int(f.read().strip()) // 1000} MHz"
        
        # Get Free Memory (Linux)
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemFree" in line:
                        # Convert kB to MB
                        free_mem = f"{int(line.split()[1]) // 1024} MB"
                        break
        return cpu_mhz, free_mem

    def _get_ip_address(self):
        """Dynamically retrieves the local IP address."""
        try:
            # We don't actually need to connect, but this identifies the local interface used for routing
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

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
            os.path.join(script_dir, "..", "assets", "fonts", "m5x7.ttf"),
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
        domains = ["favorites", "light", "switch", "scene", "script", "sensor", "binary_sensor", "climate", "settings"]
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
        entity_id = entity.get("entity_id", "")
        domain = entity_domain(entity_id)
        previous_state = str(entity.get("state", ""))
        domain, service = resolve_action(entity_id, "auto") or (domain, "turn_on")

        label = display_name(entity_id, entity)
        self.set_message(f"Executing {service} on {label}...")
        self.fav_flash_time = time.time()
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
        self.ip_address = self._get_ip_address()
        self._start_background_task("load_data", self._fetch_states_background)

    def set_message(self, text, color="white"):
        """Adds a message to the persistent log."""
        timestamp = time.strftime("%H:%M:%S")
        # Auto-detect error color
        if text.startswith("Error"):
            color = COLOR_GREY # or a specific error color if defined
            
        self.log_entries.append((timestamp, text, color))
        # Keep log size manageable
        if len(self.log_entries) > 100: # Increased log history
            self.log_entries.pop(0)
        # Auto-scroll to bottom
        self.log_scroll = max(0, len(self.log_entries) - 5)

    def save_config(self):
        save_config(self.config_path, self.config)

    def load_entities(self):
        # Filter states to only include those with supported actions
        all_states = list(self.states.values())
        supported_states = [s for s in all_states if entity_domain(s.get("entity_id", "")) in SUPPORTED_ACTIONS]

        # Use the grouping logic from ha_client which includes the "Favorites" domain
        domain_order = self.config.get("domain_order", [])
        self.entities_by_domain = get_domain_groups(supported_states, self.favorites, domain_order)
        self.domain_list = list(self.entities_by_domain.keys())
        self.domain_list.append("settings") # Add settings as a fixed entry at the end
        
        # Safety: Ensure nav_index remains valid after data reload
        if self.domain_list:
            self.nav_index = min(self.nav_index, len(self.domain_list) - 1)
        else:
            self.nav_index = 0

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
        self.load_data() # Refresh all states and then domain groups
        self.fav_flash_time = time.time()

    def handle_input(self):
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                # Keyboard logic remains mostly fixed as fallback
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    self.selection_start_time = time.time()
                    if self.mode == "settings":
                        self.mode = "main"
                        self.reorder_mode = False # Exit reorder mode when leaving settings
                    else:
                        self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        self.active_list = "domains"
                        self.reorder_mode = False
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.active_list = "entities"
                            self.entity_index = 0
                            self.reorder_mode = False # Exit reorder mode when changing active list
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            if self.reorder_mode and self.nav_index > 0:
                                # Don't move things above Favorites if it's first
                                start_idx = 1 if self.domain_list[0] == "favorites" else 0
                                if self.nav_index > start_idx:
                                    idx = self.nav_index
                                    d1, d2 = self.domain_list[idx], self.domain_list[idx-1]
                                    
                                    # Update persistent order
                                    order = [d for d in self.domain_list if d != "favorites"]
                                    p_idx = order.index(d1)
                                    order[p_idx], order[p_idx-1] = order[p_idx-1], order[p_idx]
                                    
                                    self.config["domain_order"] = order
                                    self.save_config()
                                    self.load_entities()
                                    self.nav_index -= 1
                            else:
                                self.nav_index = max(0, self.nav_index - 1)
                                self.entity_index = 0
                                self.entity_scroll_row = 0
                                self.reorder_mode = False
                        else:
                            if self.reorder_mode:
                                if self.entity_index > 0:
                                    idx = self.entity_index
                                    favs = self.config.get("favorites", [])
                                    favs[idx], favs[idx-1] = favs[idx-1], favs[idx]
                                    self.config["favorites"] = favs
                                    self.favorites = favs
                                    self.save_config()
                                    self.load_entities()
                                    self.entity_index -= 1
                                    if self.entity_index < self.entity_scroll_row:
                                        self.entity_scroll_row = self.entity_index
                            else:
                                self.entity_index = max(0, self.entity_index - 1)
                            self.entity_scroll_row = min(self.entity_scroll_row, self.entity_index)
                    elif self.mode == "settings":
                        self.settings_selected_index = max(0, self.settings_selected_index - 1)
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            if self.reorder_mode and self.nav_index < len(self.domain_list) - 1:
                                start_idx = 0
                                if self.nav_index >= start_idx and self.domain_list[self.nav_index] not in ["favorites", "settings"]:
                                    idx = self.nav_index
                                    d1, d2 = self.domain_list[idx], self.domain_list[idx+1]
                                    if d2 != "settings": # Don't swap with settings
                                        order = [d for d in self.domain_list if d not in ["favorites", "settings"]]
                                        p_idx = order.index(d1)
                                        order[p_idx], order[p_idx+1] = order[p_idx+1], order[p_idx]
                                        self.config["domain_order"] = order
                                        self.save_config()
                                        self.load_entities()
                                        self.nav_index += 1
                            else:
                                limit = len(self.domain_list) if self.domain_list else 1
                                self.nav_index = min(limit - 1, self.nav_index + 1)
                                self.entity_index = 0
                                self.entity_scroll_row = 0
                                self.reorder_mode = False
                        else:
                            current_domain = self.domain_list[self.nav_index]
                            if self.reorder_mode:
                                favs = self.config.get("favorites", [])
                                if self.entity_index < len(favs) - 1:
                                    idx = self.entity_index
                                    favs[idx], favs[idx+1] = favs[idx+1], favs[idx]
                                    self.config["favorites"] = favs
                                    self.favorites = favs
                                    self.save_config()
                                    self.load_entities()
                                    self.entity_index += 1
                                    if self.entity_index >= self.entity_scroll_row + self.visible_entities:
                                        self.entity_scroll_row = self.entity_index - self.visible_entities + 1
                            else:
                                entities_count = len(self.entities_by_domain.get(current_domain, []))
                                if self.entity_index >= self.entity_scroll_row + self.visible_entities:
                                    self.entity_scroll_row = self.entity_index - self.visible_entities + 1
                    elif self.mode == "settings":
                        self.settings_selected_index = min(2, self.settings_selected_index + 1)
                elif event.key.keysym.sym == sdl2.SDLK_PAGEUP:
                    self.selection_start_time = time.time()
                    if self.mode == "main" and self.active_list == "entities":
                        self.entity_index = max(0, self.entity_index - (self.visible_entities - 1))
                        if self.entity_index < self.entity_scroll_row:
                            self.entity_scroll_row = self.entity_index
                elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN:
                    self.selection_start_time = time.time()
                    if self.mode == "main" and self.active_list == "entities" and self.nav_index < len(self.domain_list):
                        current_domain = self.domain_list[self.nav_index]
                        count = len(self.entities_by_domain.get(current_domain, []))
                        self.entity_index = min(max(0, count - 1), self.entity_index + (self.visible_entities - 1))
                        if self.entity_index >= self.entity_scroll_row + (self.visible_entities - 1):
                            self.entity_scroll_row = min(max(0, count - self.visible_entities), self.entity_index - self.visible_entities + 1)
                elif event.key.keysym.sym in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
                    if self.mode == "main":
                        if self.active_list == "entities":
                            self._execute_entity_action()
                        elif self.nav_index < len(self.domain_list):
                            if self.domain_list[self.nav_index] == "settings":
                                self.mode = "settings"
                                self.settings_selected_index = 0
                            else:
                                self.reorder_mode = False
                    elif self.mode == "settings":
                        self._handle_settings_action()
                elif event.key.keysym.sym == sdl2.SDLK_f:
                    if self.mode == "main" and self.nav_index < len(self.domain_list):
                        current_domain = self.domain_list[self.nav_index]
                        if self.active_list == "domains":
                            if current_domain != "settings":
                                self.reorder_mode = not self.reorder_mode
                                self.set_message("Domain reorder " + ("on" if self.reorder_mode else "off"))
                        elif self.active_list == "entities":
                            if current_domain.lower() == "favorites":
                                self.reorder_mode = not self.reorder_mode
                                self.set_message("Reorder mode " + ("on" if self.reorder_mode else "off"))
                            else:
                                entities = self.entities_by_domain.get(current_domain, [])
                                if entities and self.entity_index < len(entities):
                                    self.toggle_favorite(entities[self.entity_index]["entity_id"])
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    self.load_data()
                    self.set_message("Refreshed")
                elif event.key.keysym.sym == sdl2.SDLK_s:
                    self.mode = "settings"
                    self.reorder_mode = False # Exit reorder mode when entering settings
            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                btn = event.cbutton.button
                self.selection_start_time = time.time()
                if btn == self.controls["cancel"]:
                    if self.mode == "settings":
                        self.mode = "main"
                        self.reorder_mode = False
                    else:
                        self.running = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        self.active_list = "domains"
                        self.reorder_mode = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            self.active_list = "entities"
                            self.entity_index = 0
                            self.reorder_mode = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            if self.reorder_mode and self.nav_index > 0 and self.domain_list[self.nav_index] != "settings":
                                start_idx = 1 if self.domain_list[0] == "favorites" else 0
                                if self.nav_index > start_idx:
                                    idx = self.nav_index
                                    d1 = self.domain_list[idx]
                                    order = [d for d in self.domain_list if d not in ["favorites", "settings"]]
                                    p_idx = order.index(d1)
                                    order[p_idx], order[p_idx-1] = order[p_idx-1], order[p_idx]
                                    self.config["domain_order"] = order
                                    self.save_config()
                                    self.load_entities()
                                    self.nav_index -= 1
                            else:
                                self.nav_index = max(0, self.nav_index - 1)
                                self.entity_index = 0
                                self.entity_scroll_row = 0
                                self.reorder_mode = False
                        else:
                            if self.reorder_mode:
                                if self.entity_index > 0:
                                    idx = self.entity_index
                                    favs = self.config.get("favorites", [])
                                    favs[idx], favs[idx-1] = favs[idx-1], favs[idx]
                                    self.config["favorites"] = favs
                                    self.favorites = favs
                                    self.save_config()
                                    self.load_entities()
                                    self.entity_index -= 1
                                    if self.entity_index < self.entity_scroll_row:
                                        self.entity_scroll_row = self.entity_index
                            else:
                                self.entity_index = max(0, self.entity_index - 1)
                            self.entity_scroll_row = min(self.entity_scroll_row, self.entity_index)
                    elif self.mode == "settings":
                        self.settings_selected_index = max(0, self.settings_selected_index - 1)
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    self.selection_start_time = time.time()
                    if self.mode == "main":
                        if self.active_list == "domains":
                            if self.reorder_mode and self.nav_index < len(self.domain_list) - 1:
                                if self.domain_list[self.nav_index] != "favorites":
                                    idx = self.nav_index
                                    d1 = self.domain_list[idx]
                                    order = [d for d in self.domain_list if d != "favorites"]
                                    p_idx = order.index(d1)
                                    order[p_idx], order[p_idx+1] = order[p_idx+1], order[p_idx]
                                    self.config["domain_order"] = order
                                    self.save_config()
                                    self.load_entities()
                                    self.nav_index += 1
                            else:
                                limit = len(self.domain_list) if self.domain_list else 1
                                self.nav_index = min(limit - 1, self.nav_index + 1)
                                self.entity_index = 0
                                self.entity_scroll_row = 0
                                self.reorder_mode = False
                        else:
                            current_domain = self.domain_list[self.nav_index]
                            if self.reorder_mode:
                                favs = self.config.get("favorites", [])
                                if self.entity_index < len(favs) - 1:
                                    idx = self.entity_index
                                    favs[idx], favs[idx+1] = favs[idx+1], favs[idx]
                                    self.config["favorites"] = favs
                                    self.favorites = favs
                                    self.save_config()
                                    self.load_entities()
                                    self.entity_index += 1
                                    if self.entity_index >= self.entity_scroll_row + self.visible_entities:
                                        self.entity_scroll_row = self.entity_index - self.visible_entities + 1
                            else:
                                entities_count = len(self.entities_by_domain.get(current_domain, []))
                                if self.entity_index >= self.entity_scroll_row + self.visible_entities:
                                    self.entity_scroll_row = self.entity_index - self.visible_entities + 1
                    elif self.mode == "settings":
                        self.settings_selected_index = min(2, self.settings_selected_index + 1)
                elif btn == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                    # L1: Page Up in entities list
                    if self.mode == "main" and self.active_list == "entities":
                        self.entity_index = max(0, self.entity_index - (self.visible_entities - 1))
                        self.entity_scroll_row = min(self.entity_scroll_row, self.entity_index)
                elif btn == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                    # R1: Page Down in entities list
                    if self.mode == "main" and self.active_list == "entities" and self.nav_index < len(self.domain_list):
                        current_domain = self.domain_list[self.nav_index]
                        count = len(self.entities_by_domain.get(current_domain, []))
                        self.entity_index = min(max(0, count - 1), self.entity_index + (self.visible_entities - 1))
                        if self.entity_index >= self.entity_scroll_row + (self.visible_entities - 1):
                            self.entity_scroll_row = min(max(0, count - self.visible_entities), self.entity_index - self.visible_entities + 1)
                elif btn == self.controls["confirm"]:
                    if self.mode == "main":
                        self.reorder_mode = False
                        if self.active_list == "entities":
                            self._execute_entity_action()
                        elif self.nav_index < len(self.domain_list):
                            if self.domain_list[self.nav_index] == "settings":
                                self.mode = "settings"
                                self.settings_selected_index = 0
                    elif self.mode == "settings":
                        self._handle_settings_action()
                elif btn == BTN_Y:  # Y button (North) -> Favorites
                    if self.mode == "main" and self.nav_index < len(self.domain_list):
                        current_domain = self.domain_list[self.nav_index]
                        if self.active_list == "domains":
                            if current_domain != "settings":
                                self.reorder_mode = not self.reorder_mode
                                self.set_message("Domain reorder " + ("on" if self.reorder_mode else "off"))
                        elif self.active_list == "entities":
                            if current_domain.lower() == "favorites":
                                self.reorder_mode = not self.reorder_mode
                                self.set_message("Reorder mode " + ("on" if self.reorder_mode else "off"))
                            else:
                                entities = self.entities_by_domain.get(current_domain, [])
                                if entities and self.entity_index < len(entities):
                                    self.toggle_favorite(entities[self.entity_index]["entity_id"])
                elif btn == BTN_X:  # X button (West) -> Refresh
                    self.load_data()
                    self.set_message("Refreshed")
                elif btn == sdl2.SDL_CONTROLLER_BUTTON_START:
                    self.mode = "settings"
                    self.reorder_mode = False
            elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
                # Handle L2/R2 Triggers for Log Scrolling
                axis = event.caxis.axis
                value = event.caxis.value # -32768 to 32767
                threshold = 16000
                
                if axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT:
                    if value > threshold and not self.trigger_l_pressed:
                        self.log_scroll = max(0, self.log_scroll - 1)
                        self.trigger_l_pressed = True
                    elif value < threshold:
                        self.trigger_l_pressed = False
                        
                elif axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
                    if value > threshold and not self.trigger_r_pressed:
                        self.log_scroll = min(max(0, len(self.log_entries) - 5), self.log_scroll + 1)
                        self.trigger_r_pressed = True
                    elif value < threshold:
                        self.trigger_r_pressed = False

    def _handle_settings_action(self):
        if self.settings_selected_index == 0:
            # Toggle layout
            new_layout = "spruce" if self.layout_type == "muos" else "muos"
            self.config["control_layout"] = new_layout
            self.setup_controls()
            self.save_config()
            self.set_message(f"Layout set to {new_layout.upper()}")
        elif self.settings_selected_index == 1:
            if "domain_order" in self.config:
                del self.config["domain_order"]
                self.save_config()
                self.load_entities()
                self.set_message("Domain order reset")
            else:
                self.set_message("Order already default")
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
        sdl2.SDL_RenderPresent(self.renderer)

    def render_layout(self):
        """Divides the screen into 5 zones (Header, Nav, Main, Info, Log)."""
        # 1. Header Area - Redesigned (Floating style with Scanlines)
        
        # Scanline effect behind the logo/title area for extra retro vibe
        self.ui.draw_scanlines(0, 5, 640, 85, spacing=3)

        # Double-Bar Separator (Industrial Style)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, 95, 640, 1)) # Primary Bar
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, 98, 640, 1)) # Secondary Accented Bar

        # Logo and title
        logo_tex = self.domain_icons.get("ha_logo")
        line1 = "HOME ASSISTANT"
        line2 = "for retro consoles"
        
        # Berechne die Breite beider Zeilen für die Zentrierung
        tw1, _ = self.ui.get_text_size(line1, xl=True)
        tw2, _ = self.ui.get_text_size(line2, large=True)
        text_block_width = max(tw1, tw2)
        
        logo_w = 65 if logo_tex else 0
        spacing = 30 if logo_tex else 0
        total_width = logo_w + spacing + text_block_width
        start_x = (640 - total_width) // 2

        if logo_tex:
            sdl2.SDL_RenderCopy(self.renderer, logo_tex, None, sdl2.SDL_Rect(start_x, 15, 65, 65))
            start_x += logo_w + spacing

        self.ui.draw_text(line1, start_x, 8, "white", xl=True)
        self.ui.draw_text(line2, start_x, 52, "cyan", large=True)

        # 2. Left column (Navigation) - Start at Y=105
        self.ui.draw_retro_box(10, 105, 190, 265, "CATEGORIES")
        self.draw_menu(25, 118)

        # 3. Main area (Middle) - Start at Y=105
        if self.mode == "settings":
            self.ui.draw_retro_box(210, 105, 260, 265, "SETTINGS")
            self._render_settings_list(225, 118)
        else:
            self.ui.draw_retro_box(210, 105, 260, 265, "ENTITIES")
            self._render_entities_list(225, 118)

        # 4. Right column (Info boxes) - Start at Y=105
        self.ui.draw_retro_box(480, 105, 150, 130, "CONTROLS")
        
        # Render Shortcuts in Info Box
        y_short = 122
        
        # Contextual label for Y button
        is_fav_cat = False
        is_domains = self.active_list == "domains"
        if not is_domains and self.domain_list and self.nav_index < len(self.domain_list):
            if self.domain_list[self.nav_index].lower() == "favorites":
                is_fav_cat = True

        if is_domains:
            if self.domain_list and self.nav_index < len(self.domain_list) and self.domain_list[self.nav_index] == "settings":
                y_label = "Favorite"
            elif self.domain_list:
                y_label = "Reorder Categories" if self.reorder_mode else "Sort Mode"
            else:
                y_label = "Favorite"
        else:
            y_label = "Reorder" if is_fav_cat else "Favorite"

        # Trigger flash if the control label has changed
        if y_label != self.last_y_label:
            self.controls_flash_time = time.time()
            self.last_y_label = y_label

        is_ctrl_flashing = (time.time() - self.controls_flash_time < 0.4)

        shortcuts = [
            (self.controls["confirm"], "Confirm"),
            (self.controls["cancel"], "Back"),
            (BTN_Y, y_label),
            (BTN_X, "Refresh")
        ]
        for btn, label in shortcuts:
            # Apply red flash effect if the control just changed
            is_new = (label == y_label and is_ctrl_flashing)
            text_col = "red" if is_new else "white"
            icon_mod = self.ui.colors["red"] if is_new else None

            self._render_button_icon(btn, 490, y_short, size=20, color_mod=icon_mod)
            self.ui.draw_text(label, 515, y_short + 2, text_col, small=True)
            y_short += 24

        self.ui.draw_retro_box(480, 240, 150, 130, "STATUS")
        
        cpu_mhz, free_ram = self._get_system_stats()
        server_status = "Connected" if self.states else "Disconnected"
        current_time = time.strftime("%H:%M:%S")

        # Render Status Details
        y_status = 253
        for label, val in [
            ("Time: ", current_time),
            ("IP: ", self.ip_address),
            ("Server: ", server_status),
            ("CPU: ", cpu_mhz),
            ("RAM: ", free_ram),
            ("Ver: ", VERSION)
        ]:
            tw, _ = self.ui.draw_text(label, 490, y_status, "cyan", small=True)
            self.ui.draw_text(str(val), 490 + tw, y_status, "white", small=True)
            y_status += 18

        # 5. Bottom row (Console/Status) - Start at Y=380
        self.ui.draw_retro_box(10, 380, 620, 95, "Console")
        
        # Render log entries
        log_y = 390 # Start position for the first log line
        visible_logs = 5 # Number of log lines to display
        start = self.log_scroll
        end = min(len(self.log_entries), start + visible_logs)
        
        for i in range(start, end):
            ts, txt, col = self.log_entries[i]
            # Draw timestamp in dim color, text in its color
            tw, _ = self.ui.draw_text(f"[{ts}] ", 25, log_y, COLOR_TEXT_DIM, small=True)
            self.ui.draw_text(txt, 25 + tw, log_y, col, small=True)
            log_y += 15

    def draw_menu(self, x, y_start):
        """Draws the navigation menu with pointer and highlight."""
        if not self.domain_list:
            self.ui.draw_text("Loading...", x, y_start, "cyan")
            return

        for i, domain in enumerate(self.domain_list):
            y_pos = y_start + (i * 30)
            label = domain.capitalize() if domain != "settings" else "Settings"
            
            # Search for icon in self.domain_icons (handles regular domains and settings)
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
                base_color = "red" if self.active_list == "domains" and self.reorder_mode and domain != "settings" else "cyan"
                self.ui.draw_selection_highlight(x - 10, y_pos - 3, 170, 30)
                
                # 1.1 Border around selection (1px rounded, same color as pointer)
                self.ui.draw_rounded_rect(x - 10, y_pos - 3, 170, 30, base_color)
                
                # 2. Selection triangle (pointer) - Only if domains list is active
                if self.active_list == "domains":
                    self.ui.draw_pointer(x - 21, y_pos + 10, width=15, height=18, color=base_color)
                
                # 3. Active text
                self.ui.draw_text(label, x + icon_w, y_pos, "white")
            else:
                # Normal text
                self.ui.draw_text(label, x + icon_w, y_pos, "cyan")

    def _render_entities_list(self, x, y_start):
        """Renders the list of entities for the currently selected domain."""
        if not self.domain_list or self.nav_index >= len(self.domain_list):
            self.ui.draw_text("Waiting for data...", x, y_start, "gray", small=True)
            return
            
        current_domain = self.domain_list[self.nav_index]
        if current_domain == "settings":
            self.ui.draw_text("Switch to Settings column", x, y_start, "cyan", small=True)
            return

        entities = self.entities_by_domain.get(current_domain, [])
        start = self.entity_scroll_row
        end = min(len(entities), start + self.visible_entities)
        
        for i in range(start, end):
            entity = entities[i]
            y = y_start + ((i - start) * 20)
            
            # Selection visuals
            is_selected = (self.active_list == "entities" and i == self.entity_index)
            if is_selected:
                # Visual feedback flash (0.15 seconds in white)
                is_flashing = (time.time() - self.fav_flash_time < 0.15)
                base_color = "red" if self.reorder_mode else "cyan"
                flash_color = "white" if is_flashing else base_color
                self.ui.draw_selection_highlight(x - 10, y - 1, 230, 20)
                self.ui.draw_rounded_rect(x - 10, y - 1, 230, 20, flash_color)
                self.ui.draw_pointer(x - 21, y + 2, width=15, height=18, color=flash_color)
            
            # Icon
            entity_id = entity.get("entity_id", "")
            domain = entity_domain(entity_id)
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_offset = 0
            
            # Live-Status abrufen
            is_on = entity.get("state") == "on"
            
            is_fav = self.is_favorite(entity_id)

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
            # Text color: Yellow for favorites, Cyan for selection, White for others
            if is_fav:
                color = "yellow"
            elif is_selected:
                color = "cyan"
            else:
                color = "white"
            
            label = display_name(entity_id, entity)
            max_chars = 18
            display_label = label
            
            # Auto-scroll logic if selected and name is too long
            if is_selected and self.active_list == "entities" and len(label) > max_chars:
                elapsed = time.time() - self.selection_start_time
                if elapsed > 1.0:
                    scroll_speed = 6 # Characters per second
                    scroll_pos = int((elapsed - 1.0) * scroll_speed) % (len(label) + 4)
                    padded_label = label + "    "
                    display_label = (padded_label + padded_label)[scroll_pos : scroll_pos + max_chars]
                else:
                    display_label = label[:max_chars]
            else:
                display_label = label[:max_chars]

            self.ui.draw_text(display_label, x + icon_offset, y + 2, color)

        # Scrollbar für die Entitäten-Liste
        if len(entities) > self.visible_entities:
            self.ui.draw_scrollbar(
                x + 235, y_start, 245, 
                self.entity_scroll_row, len(entities), self.visible_entities
            )

    def _render_settings_list(self, x, y_start):
        options = [
            f"Layout: {self.layout_type.upper()}",
            "Reset Category Order",
            "Back to Main Menu"
        ]
        for i, opt in enumerate(options):
            y = y_start + (i * 30)
            is_selected = (self.settings_selected_index == i)
            if is_selected:
                self.ui.draw_selection_highlight(x - 10, y - 3, 230, 28)
                self.ui.draw_rounded_rect(x - 10, y - 3, 230, 28, "cyan")
                self.ui.draw_pointer(x - 21, y + 5, width=15, height=18, color="cyan")
                self.ui.draw_text(opt, x, y, "white")
            else:
                self.ui.draw_text(opt, x, y, "cyan")


    def _print_controls(self):
        confirm = "A" if self.layout_type == "muos" else "B"
        cancel = "B" if self.layout_type == "muos" else "A"
        print(f"\n--- HA RetroConsole v{VERSION} ---")
        print(f"D-Pad / Arrows:      Navigate Lists & Focus")
        print(f"{confirm} / Enter:           Action / Toggle Entity")
        print(f"{cancel} / Escape:          Back / Exit Application")
        print(f"X / R:               Refresh All States")
        print(f"Y / F:               Toggle Favorite / Reorder Mode")
        print(f"L1 / R1:             Page Up / Page Down")
        print(f"L2 / R2:             Scroll Console Log (Bottom)")
        print(f"Start / S:           Open Settings")
        print("-" * 45 + "\n")

    def run(self):
        self.init_sdl()
        self._print_controls()
        self.load_data()

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
                self.load_entities() # Refresh the grouped entities with new states
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