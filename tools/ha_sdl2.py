import sys
import os
import time
import threading
import socket
import queue
import ctypes
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
    get_state_with_unit,
    get_domain_groups,
    favorite_action,
    favorite_entity_id,
    favorite_label,
    fetch_states_map,
    load_config,
    refresh_after_action,
    save_config,
    resolve_action,
    fetch_camera_snapshot,
)

# Controller Button Mapping Aliases (SDL Constants)
# A=0, B=1, X=2, Y=3, Back=4, Guide=5, Start=6
BTN_A = sdl2.SDL_CONTROLLER_BUTTON_A
BTN_B = sdl2.SDL_CONTROLLER_BUTTON_B
BTN_X = sdl2.SDL_CONTROLLER_BUTTON_X
BTN_Y = sdl2.SDL_CONTROLLER_BUTTON_Y

# Colors (SDL2 RGB)
COLOR_BG = sdl2.SDL_Color(10, 10, 15, 255)      # Example: Slightly lighter Midnight Blue
COLOR_CYAN = sdl2.SDL_Color(0, 163, 255, 255)   # Cyan (#00A3FF)
COLOR_HA_BLUE = sdl2.SDL_Color(3, 169, 244, 255) # HA Blue (#03A9F4)
COLOR_YELLOW = sdl2.SDL_Color(238, 176, 0, 255) # Yellow (#EEB000)
COLOR_GREY = sdl2.SDL_Color(85, 85, 85, 255)    # Grey (#555555)
COLOR_TEXT = COLOR_CYAN
COLOR_TEXT_DIM = COLOR_GREY
COLOR_HIGHLIGHT = COLOR_CYAN

# Domains that are allowed to be shown in the UI even if they have no actions
VIEWABLE_DOMAINS = [
    "light", 
    "switch", 
    "sensor", 
    "binary_sensor", 
    "climate", 
    "scene", 
    "script", 
    "media_player", 
    "cover", 
    "fan", 
    "lock", 
    "input_boolean",
    "camera"
]

# Mapping of internal keys to original Remix Icon filenames
ICON_MAP = {
    "favorites": "star-s-fill",
    "light": "lightbulb-line",
    "light_on": "lightbulb-fill",
    "switch": "toggle-line",
    "switch_on": "toggle-fill",
    "scene": "magic-line",
    "script": "terminal-box-line",
    "sensor": "dashboard-3-line",
    "binary_sensor": "checkbox-blank-circle-line",
    "binary_sensor_on": "checkbox-circle-fill",
    "binary_sensor_off": "checkbox-blank-circle-line",
    "climate": "thermometer-line",
    "settings": "settings-3-line",
    "categories": "stack-line",
    "brightness": "sun-line",
    "media_player": "film-line",
    "cover": "layout-row-fill",
    "fan": "fan-line",
    "lock": "lock-line",
    "input_boolean": "input-cursor-move",
    "camera": "video-on-line"
}

class HASDL2App:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.states = {}
        self.favorites = self.config.get("favorites", [])
        self.nav_index = 0 # Index for the left navigation column
        self.active_list = "domains" # Active column: "domains" or "entities"
        self.reorder_mode = False # True if currently reordering a favorite
        self.cat_scroll_row = 0 # Scroll position for categories list
        self.settings_scroll_row = 0 # Scroll position for settings lists
        self.entity_index = 0 # Index for the middle entity list
        self.settings_index = 0 # Index for settings options
        self.settings_active = False # True if middle column shows settings
        self.settings_view = "menu" # "menu", "categories", or "brightness"
        self.mode = "main" # "main", "favorites", or "settings"
        self.settings_selected_index = 0
        self.entity_scroll_row = 0 # Scroll position for main entity list
        self.setup_controls()
        self.ip_address = self._get_ip_address()
        self.running = True
        self.selection_start_time = time.time()
        self.fav_flash_time = 0
        self.log_entries = [] # List of (timestamp, text, color)
        self.btn_flash_times = {} # Map of btn_id -> timestamp for visual feedback
        self.log_scroll = 0
        self.trigger_l_pressed = False
        self.trigger_r_pressed = False
        self.width = 640
        self.height = 480

        # Layout Constants
        self.margin = 10
        self.header_h = 105
        self.footer_y = 380
        self.col1_w = 190
        self.col2_w = 260
        self.col3_w = 150
        self.col2_x = self.margin + self.col1_w + self.margin
        self.col3_x = self.col2_x + self.col2_w + self.margin

        self.window = None
        self.renderer = None
        self.ui = None
        self.domain_icons = {} # Cache for loaded textures
        self.entities_by_domain = {} # Cached grouped entities
        self.domain_list = [] # List of domains for favorites editor
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.game_controllers = []
        self.prev_btn_y_label = ""
        self.camera_tex = None
        self.last_camera_eid = None
        self.btn_y_flash_time = 0

        # Brightness Control Setup
        self.backlight_path = self._find_backlight_path()
        self.current_brightness = self._get_brightness()

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

    def _find_backlight_path(self):
        """Locates the system backlight brightness file."""
        base_path = "/sys/class/backlight"
        if os.path.exists(base_path):
            dirs = os.listdir(base_path)
            if dirs:
                # Often 'backlight' or 'panel' on handhelds
                return os.path.join(base_path, dirs[0], "brightness")
        return None

    def _get_brightness(self):
        """Reads the current system brightness (0-255 or 0-100)."""
        if self.backlight_path and os.path.exists(self.backlight_path):
            try:
                with open(self.backlight_path, "r") as f:
                    return int(f.read().strip())
            except: pass
        return 100

    def _set_brightness(self, value):
        """Writes brightness to system file."""
        if self.backlight_path:
            try:
                # Note: This usually requires write permissions to the sysfs file
                # On muOS/PortMaster, the launcher script or sudo might be needed
                with open(self.backlight_path, "w") as f:
                    f.write(str(value))
                self.current_brightness = value
                return True
            except Exception as e:
                self.set_message(f"Brightness Error: {str(e)[:20]}")
        return False

    def setup_controls(self):
        """Detects OS and sets up button mapping."""
        layout = self.config.get("control_layout", "auto")
        
        if layout == "auto":
            # Auto-detection
            # Spruce uses /mnt/SDCARD/spruce, Knulli/Batocera uses /userdata
            if os.path.exists("/mnt/SDCARD/spruce") or os.path.exists("/userdata/system"):
                layout = "spruce" # Nintendo Style: B=Confirm, A=Cancel
            else:
                layout = "muos" # Xbox Style: A=Confirm, B=Cancel

        self.layout_type = layout
        # muOS/Default: Confirm=A (0), Cancel=B (1) | Spruce: Confirm=B (1), Cancel=A (0)
        self.controls = {"confirm": BTN_A, "cancel": BTN_B} if layout == "muos" else {"confirm": BTN_B, "cancel": BTN_A}

        confirm_label = "A" if self.controls["confirm"] == BTN_A else "B"
        cancel_label = "B" if self.controls["cancel"] == BTN_B else "A"
        print(f"DEBUG: Control layout: {layout.upper()} (Confirm={confirm_label}, Cancel={cancel_label})")

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
            raise SystemExit("Error: Could not load any font. Ensure assets/fonts/m5x7.ttf exists.")

        # Initialize the RetroUI framework
        self.ui = RetroUI(self.renderer, selected_font)

        # Load domain icons (light.png, switch.png, etc.)
        icon_dir = os.path.join(script_dir, "..", "assets", "icons")
        
        for internal_name, remix_filename in ICON_MAP.items():
            icon_path = self._find_icon(icon_dir, remix_filename)
            if os.path.exists(icon_path):
                surface = sdlimage.IMG_Load(icon_path.encode('utf-8'))
                if surface:
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    if texture:
                        # We still store it under the internal name for the rest of the app
                        self.domain_icons[internal_name] = texture
                    sdl2.SDL_FreeSurface(surface)

        # Load main assets
        for btn in ["ha_logo"]:
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

    def _fetch_camera_snapshot_background(self, entity_id):
        """Fetches camera snapshot in a background thread."""
        return fetch_camera_snapshot(
            self.config["base_url"],
            self.config["token"],
            entity_id,
            timeout=5.0
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
        hidden = self.config.get("hidden_domains", [])
        
        # Filter by domains we want to see and domains that are not hidden in settings
        supported_states = [
            s for s in all_states 
            if (domain := entity_domain(s.get("entity_id", ""))) in VIEWABLE_DOMAINS 
            and domain not in hidden
        ]

        # Use the grouping logic from ha_client which includes the "Favorites" domain
        self.entities_by_domain = get_domain_groups(supported_states, self.favorites)
        self.domain_list = list(self.entities_by_domain.keys())

        # Handle custom domain sorting from config
        domain_order = self.config.get("domain_order", [])
        if domain_order:
            self.domain_list.sort(key=lambda d: domain_order.index(d) if d in domain_order else 999)
        
        # Safety: Ensure nav_index remains valid after data reload
        if self.domain_list:
            self.nav_index = min(self.nav_index, len(self.domain_list) - 1)
            # Keep category scroll row in check
            visible_cats = 7
            if self.nav_index < self.cat_scroll_row:
                self.cat_scroll_row = self.nav_index
            elif self.nav_index >= self.cat_scroll_row + visible_cats:
                self.cat_scroll_row = self.nav_index - visible_cats + 1
            self.cat_scroll_row = max(0, min(self.cat_scroll_row, max(0, len(self.domain_list) - visible_cats)))
        else:
            self.nav_index = 0
            self.cat_scroll_row = 0

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
        self.load_entities() # Refresh domain groups to update 'favorites' virtual domain
        self.fav_flash_time = time.time()

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
        self.fav_flash_time = time.time()
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
                continue
            self._dispatch_event(event)

    def _dispatch_event(self, event):
        """Routes SDL events to specific handlers."""
        if event.type == sdl2.SDL_KEYDOWN:
            self._handle_keydown(event.key.keysym.sym)
        elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
            self._handle_controller_button(event.cbutton.button)
        elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
            self._handle_axis_motion(event.caxis.axis, event.caxis.value)

    def _handle_keydown(self, key):
        self.selection_start_time = time.time()

        # Handle fullscreen mode inputs
        if self.mode == "camera_fullscreen":
            if key in {sdl2.SDLK_ESCAPE, sdl2.SDLK_b}:
                self._go_back()
            return

        # Global keys
        if key == sdl2.SDLK_r:
            self.load_data()
            self.btn_flash_times[BTN_X] = time.time()
            self.set_message("Refreshed")
            return
        if key == sdl2.SDLK_s:
            self.mode = "settings"
            self.btn_flash_times["START"] = time.time()
            return

        # Map keys to visual buttons for flashing
        key_map = {
            sdl2.SDLK_RETURN: self.controls["confirm"],
            sdl2.SDLK_KP_ENTER: self.controls["confirm"],
            sdl2.SDLK_ESCAPE: self.controls["cancel"],
            sdl2.SDLK_b: self.controls["cancel"],
            sdl2.SDLK_f: BTN_Y,
            sdl2.SDLK_PAGEUP: "L1",
            sdl2.SDLK_PAGEDOWN: "R1"
        }
        if key in key_map:
            self.btn_flash_times[key_map[key]] = time.time()

        if self.mode == "main":
            self._handle_main_keydown(key)
        elif self.mode == "settings":
            self._handle_settings_keydown(key)

    def _handle_controller_button(self, btn):

        # Handle fullscreen mode inputs
        if self.mode == "camera_fullscreen":
            if btn == self.controls["cancel"]:
                self._go_back()
            return

        # Global buttons
        if btn == BTN_X:
            self.load_data()
            self.btn_flash_times[BTN_X] = time.time()
            self.set_message("Refreshed")
            return
        if btn == sdl2.SDL_CONTROLLER_BUTTON_START:
            self.mode = "settings"
            self.btn_flash_times["START"] = time.time()
            return

        # Map shoulder buttons to strings for flashing
        btn_map = {
            sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: "L1",
            sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: "R1"
        }
        self.btn_flash_times[btn_map.get(btn, btn)] = time.time()

        if self.mode == "main":
            self._handle_main_controller(btn)
        elif self.mode == "settings":
            self._handle_settings_controller(btn)

    def _handle_axis_motion(self, axis, value):
        """Handles trigger axis movement for log scrolling."""
        threshold = 16000
        if axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT:
            if value > threshold and not self.trigger_l_pressed:
                self.btn_flash_times["L2"] = time.time()
                self.log_scroll = max(0, self.log_scroll - 1)
                self.trigger_l_pressed = True
            elif value < threshold:
                self.trigger_l_pressed = False
        elif axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
            if value > threshold and not self.trigger_r_pressed:
                self.btn_flash_times["R2"] = time.time()
                self.log_scroll = min(max(0, len(self.log_entries) - 5), self.log_scroll + 1)
                self.trigger_r_pressed = True
            elif value < threshold:
                self.trigger_r_pressed = False

    def _go_back(self):
        """Smart back navigation logic for menus and sub-menus."""
        if self.mode == "camera_fullscreen":
            self.mode = "main"
        elif self.mode == "settings":
            self.mode = "main"
        elif self.settings_active:
            if self.settings_view != "menu":
                self.settings_view = "menu"
                self.settings_index = 0
            else:
                self.settings_active = False
                self.active_list = "settings"
        elif self.active_list == "entities":
            self.active_list = "domains"
        else:
            self.running = False

    def _handle_main_keydown(self, key):
        if key == sdl2.SDLK_ESCAPE:
            self._go_back()
        elif key == sdl2.SDLK_b:
            self._go_back()
        elif key == sdl2.SDLK_LEFT:
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(-10)
                    else:
                        self._go_back()
                else:
                    self.active_list = "domains"
        elif key == sdl2.SDLK_RIGHT:
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(10)
                    elif self.settings_view == "menu":
                        self._handle_confirm()
            else:
                self._enter_entities()
        elif key == sdl2.SDLK_UP:
            self._nav_up()
        elif key == sdl2.SDLK_DOWN:
            self._nav_down()
        elif key == sdl2.SDLK_PAGEUP:
            self._page_up()
        elif key == sdl2.SDLK_PAGEDOWN:
            self._page_down()
        elif key in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
            self._handle_confirm()
        elif key == sdl2.SDLK_f:
            self._handle_reorder_toggle()

    def _handle_main_controller(self, btn):
        if btn == self.controls["cancel"]:
            self._go_back()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(-10)
                    else:
                        self._go_back()
                else:
                    self.active_list = "domains"
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(10)
                    elif self.settings_view == "menu":
                        self._handle_confirm()
            else:
                self._enter_entities()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
            self._nav_up()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
            self._nav_down()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
            self._page_up()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
            self._page_down()
        elif btn == self.controls["confirm"]:
            self._handle_confirm()
        elif btn == BTN_Y:
            self._handle_reorder_toggle()

    def _handle_brightness_adjust(self, delta):
        """Adjusts the system brightness by a given delta."""
        new_val = max(0, min(100, self.current_brightness + delta))
        self._set_brightness(new_val)

    def _handle_settings_keydown(self, key):
        if key == sdl2.SDLK_ESCAPE:
            self.mode = "main"
        elif key == sdl2.SDLK_UP:
            self.settings_selected_index = max(0, self.settings_selected_index - 1)
        elif key == sdl2.SDLK_DOWN:
            self.settings_selected_index = min(1, self.settings_selected_index + 1)
        elif key in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
            self._handle_settings_action()

    def _handle_settings_controller(self, btn):
        if btn == self.controls["cancel"]:
            self.mode = "main"
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
            self.settings_selected_index = max(0, self.settings_selected_index - 1)
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
            self.settings_selected_index = min(1, self.settings_selected_index + 1)
        elif btn == self.controls["confirm"]:
            self._handle_settings_action()

    def _handle_settings_action(self):
        """Action handler for the dedicated settings mode."""
        if self.settings_selected_index == 1: # 'Back' option
            self.mode = "main"

    def _enter_entities(self):
        if self.active_list in ["domains", "settings"]:
            if self.active_list == "settings":
                self.settings_active = True
                self.settings_view = "menu"
            self.active_list = "entities"
            self.entity_index = 0
            self.entity_scroll_row = 0
            self._update_selection_context()

    def _nav_up(self):
        if self.reorder_mode:
            if self.active_list == "entities":
                if self.entity_index > 0:
                    favs = self.config["favorites"]
                    favs[self.entity_index], favs[self.entity_index - 1] = \
                        favs[self.entity_index - 1], favs[self.entity_index]
                    self.entity_index -= 1
                    if self.entity_index < self.entity_scroll_row:
                        self.entity_scroll_row = self.entity_index
                    self.load_entities()
            elif self.active_list == "domains":
                if self.nav_index > 0:
                    self.domain_list[self.nav_index], self.domain_list[self.nav_index - 1] = \
                        self.domain_list[self.nav_index - 1], self.domain_list[self.nav_index]
                    self.nav_index -= 1
                    if self.nav_index < self.cat_scroll_row:
                        self.cat_scroll_row = self.nav_index
            return

        if self.active_list == "entities" and self.settings_active:
            if self.settings_view == "menu":
                self.settings_index = max(0, self.settings_index - 1)
            else:
                self.settings_index = max(0, self.settings_index - 1)
                if self.settings_view == "categories" and self.settings_index < self.settings_scroll_row:
                    self.settings_scroll_row = self.settings_index
            return

        if self.active_list == "domains":
            self.nav_index = max(0, self.nav_index - 1)
            if self.nav_index < self.cat_scroll_row:
                self.cat_scroll_row = self.nav_index
            self.entity_index = 0
            self.entity_scroll_row = 0
            self._update_selection_context()
        elif self.active_list == "settings":
            self.active_list = "domains"
            self.settings_active = False
            self.nav_index = len(self.domain_list) - 1
            visible_cats = 7
            if self.nav_index >= self.cat_scroll_row + visible_cats:
                self.cat_scroll_row = self.nav_index - visible_cats + 1
            self._update_selection_context()
        else:
            self.entity_index = max(0, self.entity_index - 1)
            if self.entity_index < self.entity_scroll_row:
                self.entity_scroll_row = self.entity_index
            self._update_selection_context()

    def _nav_down(self):
        if self.reorder_mode:
            if self.active_list == "entities":
                favs = self.config["favorites"]
                if self.entity_index < len(favs) - 1:
                    favs[self.entity_index], favs[self.entity_index + 1] = \
                        favs[self.entity_index + 1], favs[self.entity_index]
                    self.entity_index += 1
                    visible_entities = 9
                    if self.entity_index >= self.entity_scroll_row + visible_entities:
                        self.entity_scroll_row = self.entity_index - visible_entities + 1
                    self.load_entities()
            elif self.active_list == "domains":
                if self.nav_index < len(self.domain_list) - 1:
                    self.domain_list[self.nav_index], self.domain_list[self.nav_index + 1] = \
                        self.domain_list[self.nav_index + 1], self.domain_list[self.nav_index]
                    self.nav_index += 1
                    visible_cats = 7
                    if self.nav_index >= self.cat_scroll_row + visible_cats:
                        self.cat_scroll_row = self.nav_index - visible_cats + 1
            return

        if self.active_list == "entities" and self.settings_active:
            if self.settings_view == "menu":
                self.settings_index = min(1, self.settings_index + 1) # 1 = limit for 2 menu items
            else:
                self.settings_index = min(len(VIEWABLE_DOMAINS) - 1, self.settings_index + 1)
                if self.settings_view == "categories":
                    visible_settings = 8
                    if self.settings_index >= self.settings_scroll_row + visible_settings:
                        self.settings_scroll_row = self.settings_index - visible_settings + 1
            return

        if self.active_list == "domains":
            if self.nav_index < len(self.domain_list) - 1:
                self.nav_index += 1
                visible_cats = 7
                if self.nav_index >= self.cat_scroll_row + visible_cats:
                    self.cat_scroll_row = self.nav_index - visible_cats + 1
                self.entity_index = 0
                self.entity_scroll_row = 0
                self._update_selection_context()
            else:
                self.active_list = "settings"
                self.settings_active = True
                self._update_selection_context()
        elif self.active_list == "settings":
            pass # Bottom of left column
        else:
            current_domain = self.domain_list[self.nav_index]
            entities_count = len(self.entities_by_domain.get(current_domain, []))
            self.entity_index = min(entities_count - 1, self.entity_index + 1)
            visible_entities = 9
            if self.entity_index >= self.entity_scroll_row + visible_entities:
                self.entity_scroll_row = self.entity_index - visible_entities + 1
            self._update_selection_context()

    def _page_up(self):
        if self.active_list == "entities":
            self.entity_index = max(0, self.entity_index - 8)
            if self.entity_index < self.entity_scroll_row:
                self.entity_scroll_row = self.entity_index
            self._update_selection_context()

    def _page_down(self):
        if self.active_list == "entities" and self.nav_index < len(self.domain_list):
            current_domain = self.domain_list[self.nav_index]
            count = len(self.entities_by_domain.get(current_domain, []))
            self.entity_index = min(max(0, count - 1), self.entity_index + 8)
            if self.entity_index >= self.entity_scroll_row + 8:
                self.entity_scroll_row = min(max(0, count - 8), self.entity_index - 7)
            self._update_selection_context()

    def _handle_confirm(self):
        if self.settings_active and self.active_list == "entities":
            if self.settings_view == "menu":
                if self.settings_index == 0:
                    self.settings_view = "categories"
                    self.settings_index = 0
                    self.settings_scroll_row = 0
                elif self.settings_index == 1:
                    self.settings_view = "brightness"
                    self.current_brightness = self._get_brightness()
            else:
                self._handle_reorder_toggle() # Reusing toggle logic for settings checkbox
        elif self.active_list == "entities":
            current_domain = self.domain_list[self.nav_index]
            entities = self.entities_by_domain.get(current_domain, [])
            if entities and self.entity_index < len(entities):
                entity = entities[self.entity_index]
                if entity_domain(entity["entity_id"]) == "camera":
                    if self.camera_tex:
                        self.mode = "camera_fullscreen"
                    else:
                        self.set_message("Camera snapshot loading...", color="yellow")
                    return
            self._execute_entity_action()
        else:
            self._enter_entities()

    def _handle_reorder_toggle(self):
        """Logic to switch between regular favorite toggle and reordering."""
        if self.mode != "main" or not self.domain_list:
            return
            
        # Handle settings category toggle if settings panel is active
        if self.active_list == "entities" and self.settings_active:
            self._handle_settings_toggle()
            return

        current_domain = self.domain_list[self.nav_index]
        if self.active_list == "entities":
            entities = self.entities_by_domain.get(current_domain, [])
            if not entities or self.entity_index >= len(entities):
                return

            if current_domain == "favorites":
                # Toggle reorder mode
                self.reorder_mode = not self.reorder_mode
                if not self.reorder_mode:
                    self.save_config()
                    self.set_message("New order saved")
                else:
                    self.set_message("Sorting: Use D-Pad to move")
            else:
                entities = self.entities_by_domain.get(current_domain, [])
                if entities and self.entity_index < len(entities):
                    self.toggle_favorite(entities[self.entity_index]["entity_id"])
        elif self.active_list == "domains":
            # Category reordering toggle
            self.reorder_mode = not self.reorder_mode
            if not self.reorder_mode:
                self.config["domain_order"] = list(self.domain_list)
                self.save_config()
                self.set_message("Category order saved")
            else:
                self.set_message("Sorting Categories: Use D-Pad")
        else:
            self._handle_settings_toggle()

    def _handle_settings_toggle(self):
        """Toggle domain visibility in settings."""
        hidden = self.config.get("hidden_domains", [])
        domain = VIEWABLE_DOMAINS[self.settings_index]
        if domain in hidden:
            hidden.remove(domain)
        else:
            hidden.append(domain)
        self.config["hidden_domains"] = hidden
        self.save_config()
        self.load_entities()

    def _update_selection_context(self):
        """Updates contextual logic (marquee timer, camera previews) when selection changes."""
        self.selection_start_time = time.time()
        
        # Clear camera preview if not focused on an entity
        if self.active_list != "entities" or not self.domain_list or self.settings_active:
            if self.camera_tex:
                sdl2.SDL_DestroyTexture(self.camera_tex)
                self.camera_tex = None
            self.last_camera_eid = None
            return

        current_domain = self.domain_list[self.nav_index]
        entities = self.entities_by_domain.get(current_domain, [])
        if not entities or self.entity_index >= len(entities):
            return

        entity = entities[self.entity_index]
        eid = entity.get("entity_id", "")
        
        if entity_domain(eid) == "camera":
            # Trigger fetch only if the selected camera has changed
            if eid != self.last_camera_eid:
                self.last_camera_eid = eid
                if self.camera_tex:
                    sdl2.SDL_DestroyTexture(self.camera_tex)
                    self.camera_tex = None
                self._start_background_task("fetch_camera", self._fetch_camera_snapshot_background, eid)
        else:
            # Not a camera, cleanup any existing preview texture
            self.last_camera_eid = None
            if self.camera_tex:
                sdl2.SDL_DestroyTexture(self.camera_tex)
                self.camera_tex = None

    def _render_button_icon(self, btn_val, x, y, size=15, color="white"):
        """Renders a procedural button icon (white circle/box with black text)."""
        if isinstance(btn_val, int):
            label = {BTN_A: "A", BTN_B: "B", BTN_X: "X", BTN_Y: "Y"}.get(btn_val, "?")
        else:
            label = str(btn_val)

        # Check if button should flash due to recent input
        is_flashing = (time.time() - self.btn_flash_times.get(btn_val, 0) < 0.12)
        box_color = "cyan" if is_flashing else color

        tw, th = self.ui.get_text_size(label, small=True)

        # To achieve a consistent 2px padding on all sides, the box dimensions 
        # must be exactly text size + 4px (2px on each side).
        width = tw + 4
        height = th + 4

        # For single characters, maintain a square appearance.
        if len(label) == 1:
            side = max(width, height)
            # Ensure the difference is even for pixel-perfect centering
            if (side - tw) % 2 != 0: side += 1
            width = height = side

        self.ui.draw_rounded_rect(x, y, width, height, box_color)
        self.ui.draw_text(label, x + (width - tw) // 2, y + (height - th) // 2, "black", small=True)
        return width

    def _draw_global_scanlines(self):
        """Draws scanlines across the entire physical screen, filling letterbox/pillarbox areas."""
        real_w, real_h = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetRendererOutputSize(self.renderer, ctypes.byref(real_w), ctypes.byref(real_h))
        
        # Calculate the scaling factor to map logical Y coordinates (95, 98)
        # to the actual physical resolution.
        scale_y = real_h.value / float(self.height)

        # Temporarily disable logical scaling to access the full display buffer
        sdl2.SDL_RenderSetLogicalSize(self.renderer, 0, 0)
        self.ui.draw_scanlines(0, 0, real_w.value, real_h.value, spacing=3)
        
        # Draw the double-bar separator across the entire physical width (real_w).
        # This ensures it is drawn to the very edge on 16:9 devices.
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, int(95 * scale_y), real_w.value, 1))
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, int(98 * scale_y), real_w.value, 1))
        
        # Restore logical 4:3 scaling
        sdl2.SDL_RenderSetLogicalSize(self.renderer, self.width, self.height)

    def render(self):
        self.ui.clear_screen()
        
        if self.mode == "camera_fullscreen":
            self.render_camera_fullscreen()
        else:
            # Draw global background effects first (outside the 640x480 box)
            self._draw_global_scanlines()
            
            if self.mode == "main":
                self.render_layout()
            elif self.mode == "settings":
                self.render_settings()

        sdl2.SDL_RenderPresent(self.renderer)

    def render_camera_fullscreen(self):
        """Renders the selected camera snapshot in fullscreen."""
        if not self.camera_tex:
            self.mode = "main"
            return

        # Query texture dimensions to calculate aspect ratio
        tw, th = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_QueryTexture(self.camera_tex, None, None, ctypes.byref(tw), ctypes.byref(th))
        tex_w, tex_h = float(tw.value), float(th.value)
        
        if tex_w <= 0 or tex_h <= 0:
            return

        # Calculate best fit for logical resolution while maintaining aspect ratio
        scale = min(float(self.width) / tex_w, float(self.height) / tex_h)
        render_w, render_h = int(tex_w * scale), int(tex_h * scale)
        dst_x = int((self.width - render_w) / 2)
        dst_y = int((self.height - render_h) / 2)

        dst_rect = sdl2.SDL_Rect(dst_x, dst_y, render_w, render_h)
        sdl2.SDL_RenderCopy(self.renderer, self.camera_tex, None, dst_rect)

    def render_layout(self):
        """Divides the screen into 5 zones (Header, Nav, Main, Info, Log)."""
        # Double-Bar Separator (Industrial Style)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, 95, 640, 1)) # Primary Bar
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, 98, 640, 1)) # Secondary Accented Bar

        # Logo and title
        logo_tex = self.domain_icons.get("ha_logo")
        line1 = "HOME ASSISTANT"
        line2 = "for retro consoles"
        
        # Calculate width of both lines for centering
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

        # 2. Left column (Navigation) - Categories at top, Settings at bottom
        cat_box_h = 210
        self.ui.draw_retro_box(self.margin, self.header_h, self.col1_w, cat_box_h, "CATEGORIES")
        self.draw_menu(self.margin + 15, self.header_h + 13)

        set_box_y = self.header_h + cat_box_h + 5
        self.ui.draw_retro_box(self.margin, set_box_y, self.col1_w, 50, "SETTINGS")
        self._render_settings_entry(self.margin + 15, set_box_y + 13)

        # 3. Main area (Middle) - Start at Y=105
        box_title = "SETTINGS" if self.settings_active else "ENTITIES"
        self.ui.draw_retro_box(self.col2_x, self.header_h, self.col2_w, 265, box_title)
        
        if self.settings_active:
            self._render_settings_panel(self.col2_x + 15, self.header_h + 13)
        else:
            self._render_entities_list(self.col2_x + 15, self.header_h + 13)

        # 4. Right column (Controls box) - Height increased to 192 (uniform distribution)
        self.ui.draw_retro_box(self.col3_x, self.header_h, self.col3_w, 192, "CONTROLS")
        
        # Control shortcuts
        y_info = self.header_h + 16
        
        # Determine Y button label contextually
        btn_y_label = "Favorite"
        if self.active_list == "domains":
            btn_y_label = "Sort Item"
        elif self.active_list == "entities" and self.domain_list:
            current_domain = self.domain_list[self.nav_index]
            if current_domain == "favorites":
                btn_y_label = "Confirm" if self.reorder_mode else "Sort Item"
        elif self.active_list == "settings":
            btn_y_label = ""
            
        btn_x = self.col3_x + 10
        text_x = btn_x + 22

        # Confirm & Back
        self._render_button_icon(self.controls["confirm"], btn_x, y_info, size=15)
        self.ui.draw_text("Confirm", text_x, y_info + 1, "white", small=True)
        self._render_button_icon(self.controls["cancel"], btn_x, y_info + 22, size=15)
        self.ui.draw_text("Back", text_x, y_info + 23, "white", small=True)

        # Detect label change (for Sort Item flash) and trigger flash
        if btn_y_label != self.prev_btn_y_label:
            self.btn_y_flash_time = time.time()
            self.prev_btn_y_label = btn_y_label

        is_flashing = (time.time() - self.btn_y_flash_time < 0.4)
        btn_y_color = "yellow" if is_flashing else "white"
        if btn_y_label:
            self._render_button_icon(BTN_Y, btn_x, y_info + 44, size=15, color=btn_y_color)
            self.ui.draw_text(btn_y_label, text_x, y_info + 45, btn_y_color, small=True)

        # Refresh
        self._render_button_icon(BTN_X, btn_x, y_info + 66, size=15)
        self.ui.draw_text("Refresh", text_x, y_info + 67, "white", small=True)

        # Page Up/Down (L1/R1)
        self._render_button_icon("L1", btn_x, y_info + 88, size=15)
        self._render_button_icon("R1", btn_x + 22, y_info + 88, size=15)
        self.ui.draw_text("Page Up/Down", btn_x + 45, y_info + 89, "white", small=True)

        # Log Up/Down (L2/R2)
        self._render_button_icon("L2", btn_x, y_info + 110, size=15)
        self._render_button_icon("R2", btn_x + 22, y_info + 110, size=15)
        self.ui.draw_text("Log Up/Down", btn_x + 45, y_info + 111, "white", small=True)

        # Exit (START)
        icon_w = self._render_button_icon("START", btn_x, y_info + 134, size=15)
        self.ui.draw_text("Exit", btn_x + icon_w + 5, y_info + 135, "white", small=True)

        # Infos Box (formerly Status)
        self.ui.draw_retro_box(self.col3_x, 302, self.col3_w, 173, "INFOS")
        
        cpu_mhz, free_ram = self._get_system_stats()
        server_status = "Connected" if self.states else "Disconnected"
        current_time = time.strftime("%H:%M:%S")

        # Render Status Details
        y_status = 302 + 13
        for label, val in [
            ("Time: ", current_time),
            ("IP: ", self.ip_address),
            ("Server: ", server_status),
            ("CPU: ", cpu_mhz),
            ("RAM: ", free_ram),
            ("Ver: ", VERSION)
        ]:
            tw, _ = self.ui.draw_text(label, btn_x, y_status, "cyan", small=True)
            self.ui.draw_text(str(val), btn_x + tw, y_status, "white", small=True)
            y_status += 18

        # 5. Bottom row (Console & Status)
        # Console - Horizontally shortened
        self.ui.draw_retro_box(self.margin, self.footer_y, 320, 95, "Console")

        # New Status box at the bottom
        status_x = 340 # Starts roughly in the middle of the entities box
        self.ui.draw_retro_box(status_x, self.footer_y, 130, 95, "Status")

        # Display selected entity status in the new Status box
        selected_entity = None
        if self.domain_list and self.nav_index < len(self.domain_list):
            curr_dom = self.domain_list[self.nav_index]
            ents = self.entities_by_domain.get(curr_dom, [])
            if self.entity_index < len(ents):
                selected_entity = ents[self.entity_index]

        if selected_entity and not self.settings_active:
            eid = selected_entity.get("entity_id", "")
            dom = entity_domain(eid)
            
            # Determine icon
            icon_tex = self.domain_icons.get(dom) or self.domain_icons.get(f"{dom}_on")
            
            # Determine state text with custom formatting
            if dom == "binary_sensor":
                st_text = selected_entity.get("state", "unknown").upper()
            elif dom == "sensor":
                st_text = get_state_with_unit(selected_entity)
            else:
                st_text = selected_entity.get("state", "unknown").capitalize()

            # Center icon and text
            box_center_x = status_x + 65
            if dom == "camera" and self.camera_tex:
                # Render camera snapshot centered in the status box (approx 16:9)
                dst = sdl2.SDL_Rect(box_center_x - 50, self.footer_y + 12, 100, 56)
                sdl2.SDL_RenderCopy(self.renderer, self.camera_tex, None, dst)
            elif icon_tex:
                is_on = selected_entity.get("state") == "on"
                icon_color = COLOR_YELLOW if is_on else COLOR_GREY
                sdl2.SDL_SetTextureColorMod(icon_tex, icon_color.r, icon_color.g, icon_color.b)
                # 48x48 centered icon (+50% size increase)
                dst = sdl2.SDL_Rect(box_center_x - 24, self.footer_y + 12, 48, 48)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)

            # Split text into max 2 lines of 15 chars each
            status_lines = []
            if len(st_text) <= 15:
                status_lines.append(st_text)
            else:
                status_lines.append(st_text[:15])
                if len(st_text) <= 30:
                    status_lines.append(st_text[15:])
                else:
                    status_lines.append(st_text[15:27] + "...")

            # Render text lines centered below the icon
            y_text = self.footer_y + 62
            for line in status_lines:
                lw, _ = self.ui.get_text_size(line, small=True)
                self.ui.draw_text(line, box_center_x - (lw // 2), y_text, "white", small=True)
                y_text += 15
        
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

    def _render_settings_entry(self, x, y_pos):
        """Renders the settings icon and text in its separate box."""
        icon_tex = self.domain_icons.get("settings")
        icon_w = 24
        if icon_tex:
            dst = sdl2.SDL_Rect(x, y_pos + 1, icon_w, icon_w)
            sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            icon_w += 10
        
        if self.active_list == "settings":
            # Selection logic for settings box
            highlight_w = self.col1_w - 20
            self.ui.draw_selection_highlight(x - 10, y_pos - 3, highlight_w, 30, color="cyan")
            self.ui.draw_rounded_rect(x - 10, y_pos - 3, highlight_w, 30, "cyan")
            self.ui.draw_pointer(x - 21, y_pos + 3, width=15, height=18, color="cyan")
            self.ui.draw_text("Settings", x + icon_w, y_pos + 2, "white")
        else:
            self.ui.draw_text("Settings", x + icon_w, y_pos + 2, "cyan")

    def _render_settings_panel(self, x, y):
        """Renders the domain visibility settings."""
        highlight_w = self.col2_w - 30

        if self.settings_view == "menu":
            menu_items = [("Visible Categories", "categories"), ("Display Brightness", "brightness")]
            for i, (label, icon_key) in enumerate(menu_items):
                color = "white"
                is_selected = (self.active_list == "entities" and self.settings_index == i)
                
                icon_tex = self.domain_icons.get(icon_key)
                if icon_tex:
                    dst = sdl2.SDL_Rect(x, y + (i * 28) + 2, 24, 24)
                    sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)

                if is_selected:
                    color = "cyan"
                    self.ui.draw_selection_highlight(x - 10, y + (i * 28) - 3, highlight_w, 28, color="cyan")
                    self.ui.draw_rounded_rect(x - 10, y + (i * 28) - 3, highlight_w, 28, "cyan")
                    self.ui.draw_pointer(x - 21, y + (i * 28) + 2, width=15, height=18, color="cyan")
                
                self.ui.draw_text(label, x + 34, y + (i * 28) + 2, color)

        elif self.settings_view == "categories":
            self.ui.draw_text("Visible Categories:", x, y, "cyan")
            y_list_start = y + 30
            hidden = self.config.get("hidden_domains", [])
            
            visible_settings = 8
            start = self.settings_scroll_row
            end = min(len(VIEWABLE_DOMAINS), start + visible_settings)

            for i in range(start, end):
                domain = VIEWABLE_DOMAINS[i]
                y_list = y_list_start + ((i - start) * 28)
                is_hidden = domain in hidden
                
                is_selected = (self.active_list == "entities" and i == self.settings_index)
                color = "white"
                if is_selected:
                    color = "cyan"
                    self.ui.draw_selection_highlight(x - 10, y_list - 3, highlight_w, 28, color="cyan")
                    self.ui.draw_rounded_rect(x - 10, y_list - 3, highlight_w, 28, "cyan")
                    self.ui.draw_pointer(x - 21, y_list + 2, width=15, height=18, color="cyan")

                # Render status icon (on/off checkbox style)
                status_icon_name = "binary_sensor_off" if is_hidden else "binary_sensor_on"
                status_tex = self.domain_icons.get(status_icon_name)
                icon_size = 20
                
                if status_tex:
                    # Apply color: Yellow for active/on, Grey for inactive/off
                    icon_color = COLOR_YELLOW if not is_hidden else COLOR_GREY
                    sdl2.SDL_SetTextureColorMod(status_tex, icon_color.r, icon_color.g, icon_color.b)
                    
                    dst = sdl2.SDL_Rect(x, y_list + 2, icon_size, icon_size)
                    sdl2.SDL_RenderCopy(self.renderer, status_tex, None, dst)
                    sdl2.SDL_SetTextureColorMod(status_tex, 255, 255, 255) # Reset
                
                self.ui.draw_text(domain.replace("_", "-").capitalize(), x + icon_size + 8, y_list + 2, color, small=True)
            
            # Scrollbar for the settings list
            if len(VIEWABLE_DOMAINS) > visible_settings:
                self.ui.draw_scrollbar(
                    x + highlight_w + 5, self.header_h + 5, 255,
                    self.settings_scroll_row, len(VIEWABLE_DOMAINS), visible_settings
                )
        
        elif self.settings_view == "brightness":
            self.ui.draw_text("Display Brightness:", x, y, "cyan")
            y_bar = y + 50
            # Draw a simple bar
            bar_w = highlight_w - 40
            self.ui.draw_rounded_rect(x, y_bar, bar_w, 20, "white")
            # Fill bar based on brightness
            fill_w = int((self.current_brightness / 100.0) * (bar_w - 6))
            sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
            sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x + 3, y_bar + 3, fill_w, 14))
            
            self.ui.draw_text(f"{self.current_brightness}%", x + bar_w + 10, y_bar, "white")
            self.ui.draw_text("Use D-Pad Left/Right", x, y_bar + 40, "gray", small=True)

    def draw_menu(self, x, y_start):
        """Draws the navigation menu with pointer and highlight."""
        if not self.domain_list:
            self.ui.draw_text("Loading...", x, y_start, "cyan")
            return

        for i, domain in enumerate(self.domain_list):
            y_pos = y_start + (i * 28)
        visible_cats = 7
        start = self.cat_scroll_row
        end = min(len(self.domain_list), start + visible_cats)

        for i in range(start, end):
            domain = self.domain_list[i]
            y_pos = y_start + ((i - start) * 28)
            label = domain.replace("_", "-").capitalize()
            
            # Search for icon in self.domain_icons
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_w = 0
            if icon_tex:
                icon_w = 24
                # Render icon slightly vertically offset
                dst = sdl2.SDL_Rect(x, y_pos + 1, icon_w, icon_w) # Icon 1 pixel higher
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                icon_w += 10 # Spacing to text
            
            if self.active_list == "domains" and i == self.nav_index:
                # 1. Highlight background
                highlight_w = self.col1_w - 20
                highlight_color = "red" if (self.reorder_mode and self.active_list == "domains") else "cyan"
                
                self.ui.draw_selection_highlight(x - 10, y_pos, highlight_w, 28, color=highlight_color)
                
                # 1.1 Border around selection (1px rounded, same color as pointer)
                self.ui.draw_rounded_rect(x - 10, y_pos, highlight_w, 28, highlight_color)
                
                # 2. Selection triangle (pointer) - Only if domains list is active
                if self.active_list == "domains":
                    self.ui.draw_pointer(x - 21, y_pos + 6, width=15, height=18, color=highlight_color)
                
                # 3. Active text
                self.ui.draw_text(label, x + icon_w, y_pos + 2, "white") # Text 2 pixels lower
            else:
                # Normal text
                self.ui.draw_text(label, x + icon_w, y_pos + 2, "cyan") # Text 2 pixels lower

        # Scrollbar for the categories list
        if len(self.domain_list) > visible_cats:
            self.ui.draw_scrollbar(
                self.margin + self.col1_w - 6, self.header_h + 5, 200,
                self.cat_scroll_row, len(self.domain_list), visible_cats
            )

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
            highlight_w = self.col2_w - 30
            is_selected = (self.active_list == "entities" and i == self.entity_index)
            if is_selected:
                if self.reorder_mode:
                    # Red highlight for reorder mode
                    flash_color = "red"
                else:
                    # Visual feedback flash (0.15 seconds in white)
                    is_flashing = (time.time() - self.fav_flash_time < 0.15)
                    flash_color = "white" if is_flashing else "cyan"
                
                self.ui.draw_selection_highlight(x - 10, y - 3, highlight_w, 28, color=flash_color)
                self.ui.draw_rounded_rect(x - 10, y - 3, highlight_w, 28, flash_color)
                self.ui.draw_pointer(x - 21, y + 2, width=15, height=18, color=flash_color)
            
            # Icon
            entity_id = entity.get("entity_id", "")
            domain = entity_domain(entity_id)
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_offset = 0
            
            # Fetch live status
            is_on = entity.get("state") == "on"
            
            is_fav = self.is_favorite(entity_id)

            if icon_tex:
                icon_offset = 20
                
                # Color icons based on status
                icon_color = COLOR_YELLOW if is_on else COLOR_GREY
                sdl2.SDL_SetTextureColorMod(icon_tex, icon_color.r, icon_color.g, icon_color.b)

                dst = sdl2.SDL_Rect(x, y + 2, icon_offset, icon_offset)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255) # Reset to standard white
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

        # Scrollbar for the entities list
        if len(entities) > visible_entities:
            self.ui.draw_scrollbar(
                x + highlight_w + 5, self.header_h + 5, 255, 
                self.entity_scroll_row, len(entities), visible_entities
            )

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


    def run(self):
        self.init_sdl()
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
        if self.camera_tex:
            sdl2.SDL_DestroyTexture(self.camera_tex)
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
                self._update_selection_context()
            elif task_result["type"] == "fetch_camera":
                img_data = task_result["result"]
                if img_data:
                    # Convert raw bytes to SDL texture
                    rw = sdl2.SDL_RWFromMem(img_data, len(img_data))
                    # IMG_Load_RW with 1 as second param closes the RW automatically
                    surface = sdlimage.IMG_Load_RW(rw, 1)
                    if surface:
                        self.camera_tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                        sdl2.SDL_FreeSurface(surface)
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

    print(f"\n[HA RetroConsole v{VERSION}]")
    print("-" * 50)
    print("CONTROLS (Handheld / PC):")
    print("D-Pad / Arrows      : Navigate")
    print("A / Enter           : Execute Action / Select")
    print("B / Esc / B-Key     : Back / Exit")
    print("X / R-Key           : Refresh States")
    print("Y / F-Key           : Sort Items / Toggle Favorite")
    print("L1, R1 / PageUp, Dn : Page Up/Down (Entities)")
    print("L2, R2              : Scroll Console Log")
    print("Start / S-Key       : Open App Settings")
    print("-" * 50 + "\n")

    app.run()