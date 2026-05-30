import sys
import os
import time
import math
import threading
import socket
import queue
import ctypes

# Wrapper to add timestamps to all console output
class TimestampLogger:
    def __init__(self, stream):
        self.stream = stream
        self.at_start_of_line = True
    def write(self, data):
        for line in data.splitlines(keepends=True):
            if self.at_start_of_line and line.strip():
                self.stream.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ")
            self.stream.write(line)
            self.at_start_of_line = line.endswith('\n')
    def flush(self):
        self.stream.flush()

sys.stdout = TimestampLogger(sys.stdout)
sys.stderr = TimestampLogger(sys.stderr)

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
    resolve_active_url,
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
    "camera": "video-on-line",
    "wifi_0": "signal-wifi-line",
    "wifi_1": "signal-wifi-1-line",
    "wifi_2": "signal-wifi-2-line",
    "wifi_3": "signal-wifi-3-line",
    "wifi_4": "wifi-line",
    "wifi_err": "signal-wifi-error-line"
}

class HASDL2App:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.edit_buffer = ""
        self.edit_cursor = 0
        self.edit_target_key = None # "base_url" or "alternative_url"
        self.kb_row = 0
        self.kb_col = 0
        self.kb_shift = False
        self.kb_layouts = [
            [ # Layout 0: Lowercase & Numbers
                "1234567890",
                "qwertzuiop",
                "asdfghjkl:",
                "yxcvbnm,;.",
                "/-_&?#@+~", # Removed = from here as it's in Shift+0
                ["Shift", "Space", "BS", "Save", "Cancel"]
            ],
            [ # Layout 1: Uppercase & Symbols
                '!"§$%&/()=',
                "QWERTZUIOP",
                "ASDFGHJKL;",
                "YXCVBNM<>|",
                r"{}[]\*' `^", # Re-added space for better symbol alignment
                ["Shift", "Space", "BS", "Save", "Cancel"]
            ]
        ]
        self.kb_layout = self.kb_layouts[0]
        self.active_url = self.config.get("base_url", "")
        self.url_type = "primary"
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
        self.details_scroll_row = 0 # Scroll position for details box
        self.mode = "main" # "main", "favorites", or "settings"
        self.settings_selected_index = 0
        self.api_error_active = False # New: Controls visibility of the API error overlay
        self.api_error_message = ""   # New: Error message to display
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
        self.confirm_exit = False # New state for exit confirmation
        self.exit_overlay_active = False # New: Controls visibility of the exit overlay
        self.exit_overlay_message = ""   # New: Message for the exit overlay
        self.trigger_r_pressed = False
        self.axis_r_y_pressed = False # For vertical scrolling in details

        self.width = 640
        self.height = 480 # Fixed GUI size

        # Layout Constants
        self.margin = 12
        self.header_h = 56 # Header height increased by 10px
        self.h_gap = 12
        self.v_gap = 12
        self.console_h = 76
        self.controls_bar_h = 26
        self.SCROLLBAR_WIDTH = 4
        
        # Calculate main_area_h based on 480 total height (header + gaps + console + controls)
        self.main_area_h = 480 - self.header_h - self.console_h - self.controls_bar_h - (2 * self.v_gap)

        self.col1_w = 172  # 10 pixels wider
        self.col2_w = 228

        # X-Positions with 3px distance to screen edge (h_gap)
        self.col1_x = self.h_gap
        self.col2_x = self.col1_x + self.col1_w + self.h_gap
        self.col3_x = self.col2_x + self.col2_w + self.h_gap
        self.col3_w = 640 - self.col3_x - self.h_gap  # Remaining width to the right edge

        self.main_y = self.header_h + self.v_gap
        self.console_y = self.main_y + self.main_area_h + self.v_gap
        self.controls_bar_y = self.console_y + self.console_h

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
        self.last_sync_time = "Never" # Tracking for the sync indicator
        self.flash_colors = ["yellow", "blue", "white", "green", "red", "magenta"]
        self.camera_tex = None
        self.last_auto_refresh_time = time.time() # For periodic background refresh
        self.last_camera_eid = None
        self.btn_y_flash_time = 0

        # Brightness Control Setup
        self.backlight_path = self._find_backlight_path()
        self.current_brightness = self._get_brightness()

    def _render_details_box(self, x, y, width, height):
        """Renders detailed attributes of the currently selected entity."""
        filtered_attrs = self._get_selected_entity_attributes()
        selected_entity = self._get_selected_entity()

        if selected_entity:
            entity_id = selected_entity.get("entity_id", "")
            state = selected_entity.get("state", "unknown")

            item_h = 15
            # Available height for attributes (header area uses approx 53px)
            visible_attrs = (height - 60) // item_h
            
            if len(filtered_attrs) > visible_attrs:
                self.details_scroll_row = max(0, min(self.details_scroll_row, len(filtered_attrs) - visible_attrs))
            else:
                self.details_scroll_row = 0

            content_area_width = width
            # Draw ID line
            id_label_text = "ID: "
            id_label_tw, _ = self.ui.get_text_size(id_label_text, small=True)
            display_entity_id = self.ui.truncate_text(entity_id, content_area_width - id_label_tw, small=True)
            self.ui.draw_text(f"{id_label_text}{display_entity_id}", x, y, "cyan", small=True)
            y += 18

            # Draw Status line
            state_label_text = "State: "
            state_label_tw, _ = self.ui.get_text_size(state_label_text, small=True)
            display_state = self.ui.truncate_text(state, content_area_width - state_label_tw, small=True)
            self.ui.draw_text(f"{state_label_text}{display_state}", x, y, "white", small=True)
            y += 20
            
            self.ui.draw_text("Attributes:", x, y, "cyan", small=True)
            y += 15
            
            list_top = y # save list starting point for the scrollbar
            
            start = self.details_scroll_row
            end = min(len(filtered_attrs), start + visible_attrs)

            key_col_w = int(width * 0.66) # 66% for label
            val_col_x = x + key_col_w + 5 # 5px gap between label and value

            for i in range(start, end):
                label, val_str = filtered_attrs[i]
                
                # Truncate label and value for their respective columns
                display_label = self.ui.truncate_text(f"{label}:", key_col_w, small=True)
                display_val = self.ui.truncate_text(val_str, content_area_width - key_col_w - 5, small=True)

                self.ui.draw_text(display_label, x, y, "gray", small=True)
                self.ui.draw_text(display_val, val_col_x, y, "white", small=True)
                y += item_h

            # Scrollbar for details
            if len(filtered_attrs) > visible_attrs:
                self.ui.draw_scrollbar(
                    int(self.col3_x + self.col3_w - self.SCROLLBAR_WIDTH - 4), 
                    list_top, 
                    visible_attrs * item_h,
                    self.details_scroll_row, len(filtered_attrs), visible_attrs
                )
        else:
            self.ui.draw_text("Select an entity to see details...", x, y, "gray", small=True)

    def _render_system_infos_box(self, x, y):
        """Renders system statistics in a compact grid."""
        small_gap = 5 # Gap between label and value
        line_height = 16
        content_width = self.col3_w - 2 * self.margin
        half_content_width = content_width // 2
        current_y = y

        cpu_mhz, free_ram, wifi = self._get_system_stats()
        current_time = time.strftime("%H:%M:%S")
        
        items = [
            ("Time:", current_time),
            ("CPU:", cpu_mhz),
            ("RAM:", free_ram),
            ("Ver:", VERSION),
            ("Srv:", "Online" if self.states else "Offline"),
            ("Sync:", self.last_sync_time)
        ]
        
        for i in range(0, len(items), 2):
            # Column 1
            label1, val1 = items[i]
            label1_tw, _ = self.ui.get_text_size(label1, small=True)
            val1_max_width = half_content_width - label1_tw - small_gap
            display_val1 = self.ui.truncate_text(val1, val1_max_width, small=True)
            self.ui.draw_text(label1, x, current_y, "cyan", small=True)
            self.ui.draw_text(display_val1, x + label1_tw + small_gap, current_y, "white", small=True)

            # Column 2 (if exists)
            if i + 1 < len(items):
                label2, val2 = items[i+1]
                label2_tw, _ = self.ui.get_text_size(label2, small=True)
                val2_max_width = half_content_width - label2_tw - small_gap
                display_val2 = self.ui.truncate_text(val2, val2_max_width, small=True)
                self.ui.draw_text(label2, x + half_content_width, current_y, "cyan", small=True)
                self.ui.draw_text(display_val2, x + half_content_width + label2_tw + small_gap, current_y, "white", small=True)
            
            current_y += line_height

        # IP address on its own line
        ip_label_text = "IP:"
        ip_label_tw, _ = self.ui.get_text_size(ip_label_text, small=True)

        # Determine WiFi icon based on strength percentage
        wifi_icon_key = "wifi_err"
        if wifi != "N/A":
            try:
                val = int(wifi.replace("%", ""))
                if val >= 76: wifi_icon_key = "wifi_4"
                elif val >= 51: wifi_icon_key = "wifi_3"
                elif val >= 26: wifi_icon_key = "wifi_2"
                elif val >= 1: wifi_icon_key = "wifi_1"
                else: wifi_icon_key = "wifi_0"
            except:
                pass

        wifi_info = f" ({wifi})" if wifi != "N/A" else ""
        ip_full_val = f"{self.ip_address}{wifi_info}"
        
        icon_size = 16
        ip_value_max_width = content_width - ip_label_tw - small_gap - icon_size - 4
        display_ip = self.ui.truncate_text(ip_full_val, ip_value_max_width, small=True)

        self.ui.draw_text(ip_label_text, x, current_y, "cyan", small=True)
        tw_val, _ = self.ui.draw_text(display_ip, x + ip_label_tw + small_gap, current_y, "white", small=True)

        # Render the WiFi icon next to the IP/Strength text
        wifi_tex = self.domain_icons.get(wifi_icon_key)
        if wifi_tex:
            dst = sdl2.SDL_Rect(int(x + ip_label_tw + small_gap + tw_val + 4), int(current_y), icon_size, icon_size)
            sdl2.SDL_RenderCopy(self.renderer, wifi_tex, None, dst)

    def _render_console_log(self, x, y):
        """Renders the last two entries of the log."""
        logs = self.log_entries[-4:]
        for ts, txt, col in logs:
            tw, _ = self.ui.draw_text(f"[{ts}] ", x, y, COLOR_TEXT_DIM, small=True)
            self.ui.draw_text(txt, x + tw, y, col, small=True)
            y += 15

    def _render_controls_bar(self, x, y):
        """Renders gamepad controls in a single horizontal row at the bottom."""
        btn_y_label = "Favorite"
        if self.active_list == "domains":
            btn_y_label = "Sort Item"
        elif self.active_list == "entities" and self.domain_list:
            current_domain = self.domain_list[self.nav_index]
            if current_domain == "favorites":
                btn_y_label = "Confirm" if self.reorder_mode else "Sort Item"

        controls = [
            (self.controls["confirm"], "Confirm"),
            (self.controls["cancel"], "Back"),
            (BTN_Y, btn_y_label),
            (BTN_X, "Refresh"),
            ("L1/R1", "Page"),
            ("START", "Settings")
        ]
        
        total_w = 0
        gap = self.margin + 5
        items_data = []
        
        for btn, label in controls:
            if not label: continue
            # Replicate _render_button_icon width logic (updated for +1px front padding)
            btn_str = {BTN_A: "A", BTN_B: "B", BTN_X: "X", BTN_Y: "Y"}.get(btn, str(btn))
            itw, ith = self.ui.get_text_size(btn_str, small=True)
            bw = itw + 5
            if len(btn_str) == 1:
                side = max(bw, ith + 4)
                bw = side
            
            tw, _ = self.ui.get_text_size(label, small=True)
            item_w = bw + 4 + tw
            items_data.append((btn, label, bw))
            total_w += item_w
        
        total_w += (len(items_data) - 1) * gap
        cur_x = (self.width - total_w) // 2

        for btn, label, bw in items_data:
            self._render_button_icon(btn, cur_x, y + 5, size=15)
            self.ui.draw_text(label, cur_x + bw + 4, y + 6, "white", small=True)
            cur_x += bw + 4 + self.ui.get_text_size(label, small=True)[0] + gap

    def _render_preview_box(self, x, y, width, height):
        """Renders a visual preview (icon or camera snapshot) of the selected entity."""
        selected_entity = None
        if self.domain_list and self.nav_index < len(self.domain_list):
            curr_dom = self.domain_list[self.nav_index]
            ents = self.entities_by_domain.get(curr_dom, [])
            if self.entity_index < len(ents):
                selected_entity = ents[self.entity_index]

        if not selected_entity or self.settings_active:
            return

        eid = selected_entity.get("entity_id", "")
        dom = entity_domain(eid)
        state = selected_entity.get("state", "unknown")
        is_on = state == "on"

        # 1. Camera Snapshot
        if dom == "camera" and self.camera_tex:
            tw, th = ctypes.c_int(), ctypes.c_int()
            sdl2.SDL_QueryTexture(self.camera_tex, None, None, ctypes.byref(tw), ctypes.byref(th))
            if tw.value > 0 and th.value > 0:
                scale = min(float(width) / tw.value, float(height) / th.value)
                rw, rh = int(tw.value * scale), int(th.value * scale)
                dst = sdl2.SDL_Rect(int(x + (width - rw) // 2), int(y + (height - rh) // 2), rw, rh)
                sdl2.SDL_RenderCopy(self.renderer, self.camera_tex, None, dst)
            return

        # 2. Domain Icons (Status-colored)
        icon_variant = f"{dom}_on" if is_on else f"{dom}_off"
        icon_tex = self.domain_icons.get(icon_variant) or self.domain_icons.get(dom)
        if icon_tex:
            size = min(width, height, 64)
            dst = sdl2.SDL_Rect(int(x + (width - size) // 2), int(y + (height - size) // 2), size, size)
            color = COLOR_YELLOW if is_on else COLOR_GREY
            sdl2.SDL_SetTextureColorMod(icon_tex, color.r, color.g, color.b)
            sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255) # Reset

    def _get_system_stats(self):
        """Fetches real CPU MHz, Free RAM and WiFi strength on Linux devices."""
        cpu_mhz = "N/A"
        free_mem = "N/A"
        wifi_strength = "N/A"
        
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

        # Get WiFi Strength (Linux)
        # Method 1: Parse /proc/net/wireless (Standard)
        if os.path.exists("/proc/net/wireless"):
            try:
                with open("/proc/net/wireless", "r") as f:
                    for line in f:
                        if ":" in line and not line.strip().startswith("Inter"):
                            parts = line.split(":")[1].split()
                            if len(parts) >= 2:
                                # Skip status (parts[0]) and take quality (parts[1])
                                q = parts[1].rstrip('.')
                                if q.isdigit():
                                    wifi_strength = f"{q}%"
                                    break
                        if wifi_strength != "N/A": break
            except: pass

        # Method 2: Fallback to /sys/class/net/ and /proc/net/ (Modern & Realtek BSP)
        if wifi_strength == "N/A":
            try:
                for iface in os.listdir("/sys/class/net/"):
                    if iface == "lo": continue
                    # Check multiple common nodes for signal strength
                    for node in ["wireless/link", "wireless/level", "signal"]:
                        p = f"/sys/class/net/{iface}/{node}"
                        if os.path.exists(p):
                            with open(p, "r") as f:
                                val = f.read().strip()
                                if val.lstrip('-').isdigit():
                                    # Use absolute value (handles dBm and quality %)
                                    wifi_strength = f"{abs(int(val))}%"
                                    break
                    
                    # Realtek specific proc paths (common on TrimUI RTL8723DS)
                    for proc_node in [f"/proc/net/rtl8723ds/{iface}/signal", f"/proc/net/rtl8188fu/{iface}/signal"]:
                        if os.path.exists(proc_node):
                            with open(proc_node, "r") as f:
                                val = f.read().strip()
                                if val.isdigit():
                                    wifi_strength = f"{val}%"
                                    break

                    if wifi_strength != "N/A": break
            except: pass

        return cpu_mhz, free_mem, wifi_strength

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
            self.active_url, domain, service, entity_id, previous_state, None
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
        # Automatically resolve if we should use primary or alternative URL
        url, utype = resolve_active_url(self.config, timeout=5.0)
        states = fetch_states_map(
            url,
            self.config["token"],
            timeout=10.0
        )
        return {"states": states, "url": url, "url_type": utype}

    def _fetch_camera_snapshot_background(self, entity_id):
        """Fetches camera snapshot in a background thread."""
        return fetch_camera_snapshot(
            self.active_url,
            self.config["token"],
            entity_id,
            timeout=5.0
        )

    def _execute_service_and_refresh_background(self, base_url, domain, service, entity_id, previous_state, favorite):
        """Executes a service call and refreshes states in a background thread."""
        call_service(
            base_url,
            self.config["token"],
            domain,
            service,
            entity_id,
            timeout=10.0,
        )
        new_states = refresh_after_action(
            base_url,
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
        supported_states = []
        for s in all_states:
            if s is None: continue
            domain = entity_domain(s.get("entity_id", ""))
            if domain in VIEWABLE_DOMAINS and domain not in hidden:
                supported_states.append(s)

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
            visible_cats = 8
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
            self.active_url, domain, service, entity_id, previous_state, favorite
        )

    def handle_input(self):
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
                return
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

        # Handle exit confirmation first
        if self.api_error_active:
            self.api_error_active = False
            return # Any key dismisses the error

        if self.confirm_exit:
            if key == sdl2.SDLK_ESCAPE or key == sdl2.SDLK_b:
                self.running = False # Confirmed exit
                self.exit_overlay_active = False # Hide overlay
            elif key in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
                self.confirm_exit = False
                self.exit_overlay_active = False # Hide overlay
                self.set_message("Exit cancelled.")
            else: # Any other input cancels the exit prompt
                self.confirm_exit = False
                self.exit_overlay_active = False # Hide overlay
                self.set_message("Exit cancelled.")
            return # Consume the event

        # Auto-close fullscreen camera on navigation
        if self.mode == "camera_fullscreen" and key in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT]:
            self.mode = "main"

        # Global keys
        if key == sdl2.SDLK_r:
            self.load_data()
            self.btn_flash_times[BTN_X] = time.time()
            self.set_message("Refreshed")
            return
        if key == sdl2.SDLK_s:
            self.active_list = "settings" # Select settings entry in the left column
            self.settings_active = True # Open settings panel in the middle column
            self.settings_view = "menu" # Start in settings menu
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

        self._handle_main_keydown(key) # All key presses are now handled in main mode

    def _handle_controller_button(self, btn):

        # Handle exit confirmation first
        if self.api_error_active:
            self.api_error_active = False
            return # Any button dismisses the error

        if self.confirm_exit:
            if btn == self.controls["cancel"]:
                self.running = False # Confirmed exit
                self.exit_overlay_active = False # Hide overlay
            elif btn == self.controls["confirm"]:
                self.confirm_exit = False
                self.exit_overlay_active = False # Hide overlay
                self.set_message("Exit cancelled.")
            else: # Any other input cancels the exit prompt
                self.confirm_exit = False
                self.exit_overlay_active = False # Hide overlay
                self.set_message("Exit cancelled.")
            return # Consume the event

        # Handle fullscreen mode inputs
        if self.mode == "camera_fullscreen":
            # Auto-close on D-Pad movement
            if btn in [sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN, 
                       sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT]:
                self.mode = "main"

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
            self.active_list = "settings" # Select settings entry in the left column
            self.settings_active = True # Open settings panel in the middle column
            self.settings_view = "menu" # Start in settings menu
            self.btn_flash_times["START"] = time.time()
            return

        # Map shoulder buttons to strings for flashing
        btn_map = {
            sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: "L1",
            sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: "R1"
        }
        self.btn_flash_times[btn_map.get(btn, btn)] = time.time()

        self._handle_main_controller(btn) # All controller buttons are now handled in main mode

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
        elif axis == sdl2.SDL_CONTROLLER_AXIS_RIGHTY:
            # Use Right Stick for Details scrolling
            if abs(value) > threshold:
                if not self.axis_r_y_pressed:
                    step = 1 if value > 0 else -1
                    self.details_scroll_row = max(0, self.details_scroll_row + step)
                    # Cap is handled dynamically in render, but we can do a rough check here
                    self.axis_r_y_pressed = True
            else:
                self.axis_r_y_pressed = False

    def _go_back(self):
        """Smart back navigation logic for menus and sub-menus."""
        if self.settings_view == "edit_url":
            self.settings_view = "connection"
            self.settings_index = 0
            return

        if self.mode == "camera_fullscreen":
            self.mode = "main"
            self.confirm_exit = False
            self.exit_overlay_active = False # Reset if navigating away from potential exit
        elif self.mode == "settings":
            self.mode = "main" # This mode is effectively removed, but kept for safety
            self.confirm_exit = False
            self.exit_overlay_active = False # Reset
        elif self.settings_active:
            if self.settings_view != "menu":
                self.settings_view = "menu"
                self.settings_index = 0 # Reset selection in settings menu
                self.confirm_exit = False
                self.exit_overlay_active = False # Reset
            else:
                self.settings_active = False
                self.active_list = "settings"
                self.confirm_exit = False
                self.exit_overlay_active = False # Reset
        elif self.active_list == "entities":
            self.active_list = "domains"
            self.confirm_exit = False
            self.exit_overlay_active = False # Reset
        else:
            if self.confirm_exit: # If already in confirm state, then exit
                self.running = False
                self.exit_overlay_active = False # Hide overlay on confirmed exit
            else: # About to exit, ask for confirmation
                self.confirm_exit = True
                self.exit_overlay_active = True
                self.exit_overlay_message = "Press Back again to exit, or Confirm to cancel."

    def _handle_main_keydown(self, key):
        if key == sdl2.SDLK_ESCAPE or key == sdl2.SDLK_b:
            self._go_back()
        elif key == sdl2.SDLK_LEFT:
            if self.active_list == "details":
                self.active_list = "entities"
            elif self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(-10)
                    elif self.settings_view == "edit_url":
                        row_len = len(self.kb_layout[self.kb_row])
                        self.kb_col = (self.kb_col - 1) % row_len
                    else:
                        self._go_back()
                else:
                    self.active_list = "domains"
        elif key == sdl2.SDLK_RIGHT: # D-Pad Right
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(10)
                    elif self.settings_view == "edit_url":
                        row_len = len(self.kb_layout[self.kb_row])
                        self.kb_col = (self.kb_col + 1) % row_len
                    elif self.settings_view == "menu":
                        self._handle_confirm()
                else:
                    self.active_list = "details"
            else:
                self._enter_entities()
        elif key == sdl2.SDLK_UP:
            self._nav_up()
        elif key == sdl2.SDLK_DOWN:
            self._nav_down()
        elif key == sdl2.SDLK_x and self.settings_view == "edit_url":
            self.edit_buffer = self.edit_buffer[:-1]
        elif key == sdl2.SDLK_PAGEUP:
            self._page_up()
        elif key == sdl2.SDLK_PAGEDOWN:
            self._page_down()
        elif key in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
            self._handle_confirm()
        elif key == sdl2.SDLK_f:
            self._handle_reorder_toggle()
        elif key == sdl2.SDLK_i:
            self.details_scroll_row = max(0, self.details_scroll_row - 1)
        elif key == sdl2.SDLK_k:
            self.details_scroll_row += 1

    def _handle_main_controller(self, btn):
        if btn == self.controls["cancel"]:
            self._go_back()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
            if self.active_list == "details":
                self.active_list = "entities"
            elif self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(-10)
                    elif self.settings_view == "edit_url":
                        row_len = len(self.kb_layout[self.kb_row])
                        self.kb_col = (self.kb_col - 1) % row_len
                    else:
                        self._go_back()
                else:
                    self.active_list = "domains"
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT: # D-Pad Right
            if self.active_list == "entities":
                if self.settings_active:
                    if self.settings_view == "brightness":
                        self._handle_brightness_adjust(10)
                    elif self.settings_view == "edit_url":
                        row_len = len(self.kb_layout[self.kb_row])
                        self.kb_col = (self.kb_col + 1) % row_len
                    elif self.settings_view == "menu":
                        self._handle_confirm()
                else:
                    self.active_list = "details"
            else:
                self._enter_entities() # Switch from domains to entities/settings panel
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP: # D-Pad Up
            self._nav_up()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN: # D-Pad Down
            self._nav_down()
        elif btn == BTN_X and self.settings_view == "edit_url":
            self.edit_buffer = self.edit_buffer[:-1]
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: # L1
            self._page_up()
        elif btn == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: # R1
            self._page_down()
        elif btn == self.controls["confirm"]: # Confirm button
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
            if self.active_list == "settings": # If the "SETTINGS" entry is selected in the left column
                self.settings_active = True
                self.settings_view = "menu"
            self.active_list = "entities"
            self.entity_index = 0
            self.entity_scroll_row = 0
            self._update_selection_context()

    def _nav_up(self):
        if self.active_list == "details":
            self.details_scroll_row = max(0, self.details_scroll_row - 1)
            return

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
            elif self.settings_view == "connection":
                self.settings_index = max(0, self.settings_index - 1)
            elif self.settings_view == "edit_url":
                self.kb_row = (self.kb_row - 1) % len(self.kb_layout)
                row_len = len(self.kb_layout[self.kb_row])
                self.kb_col = min(self.kb_col, row_len - 1)
            else:
                self.settings_index = max(0, self.settings_index - 1)
                if self.settings_index < self.settings_scroll_row:
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
            self.active_list = "domains" # Back to category list
            self.settings_active = False
            self.nav_index = len(self.domain_list) - 1
            visible_cats = 8
            if self.nav_index >= self.cat_scroll_row + visible_cats:
                self.cat_scroll_row = self.nav_index - visible_cats + 1
            self._update_selection_context()
        else:
            self.entity_index = max(0, self.entity_index - 1)
            if self.entity_index < self.entity_scroll_row:
                self.entity_scroll_row = self.entity_index
            self._update_selection_context()

    def _nav_down(self):
        if self.active_list == "details":
            self.details_scroll_row += 1 # Bound check happens in render
            return

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
                    visible_cats = 8
                    if self.nav_index >= self.cat_scroll_row + visible_cats:
                        self.cat_scroll_row = self.nav_index - visible_cats + 1
            return

        if self.active_list == "entities" and self.settings_active:
            if self.settings_view == "menu":
                self.settings_index = min(4, self.settings_index + 1) # limit for 5 menu items
            elif self.settings_view == "connection":
                self.settings_index = min(1, self.settings_index + 1) # 0: Primary, 1: Alternative
            elif self.settings_view == "edit_url":
                self.kb_row = (self.kb_row + 1) % len(self.kb_layout)
                row_len = len(self.kb_layout[self.kb_row])
                self.kb_col = min(self.kb_col, row_len - 1)
            else:
                if self.settings_view == "categories": limit = len(VIEWABLE_DOMAINS) - 1
                elif self.settings_view == "flash_color": limit = len(self.flash_colors) - 1
                elif self.settings_view == "wifidebug": limit = len(self._collect_wifi_debug_info()) - 1
                else: limit = 0

                self.settings_index = min(limit, self.settings_index + 1)
                visible_settings = 8 if self.settings_view != "wifidebug" else 18
                if self.settings_index >= self.settings_scroll_row + visible_settings:
                    self.settings_scroll_row = self.settings_index - visible_settings + 1
            return

        if self.active_list == "domains":
            if self.nav_index < len(self.domain_list) - 1:
                self.nav_index += 1
                visible_cats = 8
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

    def _get_selected_entity(self):
        if self.domain_list and self.nav_index < len(self.domain_list):
            curr_dom = self.domain_list[self.nav_index]
            ents = self.entities_by_domain.get(curr_dom, [])
            if self.entity_index < len(ents):
                return ents[self.entity_index]
        return None

    def _get_selected_entity_attributes(self):
        entity = self._get_selected_entity()
        if not entity: return []
        attributes = entity.get("attributes", {})
        filtered_attrs = []
        for k, v in attributes.items():
            if k not in ["friendly_name", "icon", "entity_picture", "supported_features"]:
                label = str(k).replace("_", " ").capitalize()
                val_str = str(v)
                filtered_attrs.append((label, val_str))
        return filtered_attrs

    def _handle_confirm(self):
        if self.active_list == "details":
            return
        elif self.settings_active and self.active_list == "entities":
            if self.settings_view == "menu":
                if self.settings_index == 0: # "Visible Categories"
                    self.settings_view = "categories"
                    self.settings_index = 0
                    self.settings_scroll_row = 0
                elif self.settings_index == 1:
                    self.settings_view = "brightness"
                    self.current_brightness = self._get_brightness()
                elif self.settings_index == 2: # "Flash Color"
                    self.settings_view = "flash_color"
                    self.settings_index = 0
                    self.settings_scroll_row = 0
                elif self.settings_index == 3: # "WiFi Debug"
                    self.settings_view = "wifidebug"
                    self.settings_index = 0
                    self.settings_scroll_row = 0
                elif self.settings_index == 4: # "Connection Info"
                    self.settings_view = "connection"
                    self.settings_index = 0
                    self.settings_scroll_row = 0
            elif self.settings_view == "connection":
                # Enter Edit Mode
                self.edit_target_key = "base_url" if self.settings_index == 0 else "alternative_url"
                self.edit_buffer = self.config.get(self.edit_target_key, "http://")
                if not self.edit_buffer: self.edit_buffer = "http://"
                self.kb_row = 0
                self.kb_col = 0
                self.settings_view = "edit_url"
            elif self.settings_view == "edit_url":
                key = self.kb_layout[self.kb_row][self.kb_col]
                if key == "Save":
                    self.config[self.edit_target_key] = self.edit_buffer
                    self.save_config()
                    self.set_message(f"URL updated")
                    self.settings_view = "connection"
                    self.load_data()
                elif key == "Cancel":
                    self.settings_view = "connection"
                elif key == "Shift":
                    self.kb_shift = not self.kb_shift
                    self.kb_layout = self.kb_layouts[1 if self.kb_shift else 0]
                elif key == "BS":
                    self.edit_buffer = self.edit_buffer[:-1]
                elif key == "Space":
                    self.edit_buffer += " "
                else:
                    self.edit_buffer += key
            else: # If in "categories" or "brightness"
                self._handle_settings_toggle() # Toggle category visibility
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
        if not self.domain_list:
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
        """Toggle domain visibility or select color in settings."""
        if self.settings_view == "categories":
            hidden = self.config.get("hidden_domains", [])
            domain = VIEWABLE_DOMAINS[self.settings_index]
            if domain in hidden:
                hidden.remove(domain)
            else:
                hidden.append(domain)
            self.config["hidden_domains"] = hidden
            self.set_message(f"Category '{domain}' visibility toggled.")
        elif self.settings_view == "flash_color":
            new_color = self.flash_colors[self.settings_index]
            self.config["flash_color"] = new_color
            self.set_message(f"Flash color set to {new_color.capitalize()}.")

        self.save_config()
        self.load_entities()

    def _update_selection_context(self):
        """Updates contextual logic (marquee timer, camera previews) when selection changes."""
        self.selection_start_time = time.time()
        self.details_scroll_row = 0 # Reset scroll whenever a new entity is selected
        
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
        """Renders a procedural button icon (white circle/box with white text)."""
        if isinstance(btn_val, int):
            label = {BTN_A: "A", BTN_B: "B", BTN_X: "X", BTN_Y: "Y"}.get(btn_val, "?")
        else:
            label = str(btn_val)

        # Check if button should flash due to recent input
        is_flashing = (time.time() - self.btn_flash_times.get(btn_val, 0) < 0.3)
        box_color = self.config.get("flash_color", "yellow") if is_flashing else color

        tw, th = self.ui.get_text_size(label, small=True)

        # Increased horizontal size by 1px to accommodate extra front padding
        width = tw + 5
        height = th + 4

        # For single characters, maintain a square appearance.
        if len(label) == 1:
            side = max(width, height)
            width = height = side

        self.ui.draw_rounded_rect(x, y, width, height, box_color)
        # Shift text 1px to the right to ensure the extra pixel is at the front
        self.ui.draw_text(label, x + (width - tw) // 2 + 1, y + (height - th) // 2, "white", small=True)
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
        sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_CYAN.r, COLOR_CYAN.g, COLOR_CYAN.b, COLOR_CYAN.a)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, int((self.header_h - 3) * scale_y), real_w.value, 1))
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, int(self.header_h * scale_y), real_w.value, 1))
        
        # Restore logical 4:3 scaling
        sdl2.SDL_RenderSetLogicalSize(self.renderer, self.width, self.height)

    def render(self):
        self.ui.clear_screen()

        # Calculate global pulse values for the selection pointer
        self.pulse_x = int(math.sin(time.time() * 10) * 3)
        self.pulse_alpha = int(170 + 85 * math.sin(time.time() * 10))
        # Calculate global pulse values for the selection pointer (slower breathing, 1px bob)
        self.pulse_x = int(math.sin(time.time() * 5) * 1)
        self.pulse_alpha = int(170 + 85 * math.sin(time.time() * 5))
        
        if self.mode == "camera_fullscreen":
            self.render_camera_fullscreen()
        else:
            # Draw global background effects first (outside the 640x480 box)
            self._draw_global_scanlines()
            
            if self.mode == "main":
                self.render_layout()
            elif self.mode == "settings":
                self.render_settings()

        # Render exit confirmation overlay on top of everything else
        self._render_exit_overlay()
        self._render_error_overlay()

        sdl2.SDL_RenderPresent(self.renderer)

    def _render_exit_overlay(self):
        """Renders the exit confirmation overlay in the center of the screen."""
        if not self.exit_overlay_active:
            return

        # Overlay dimensions
        overlay_w = 400
        overlay_h = 100
        overlay_x = (self.width - overlay_w) // 2
        overlay_y = (self.height - overlay_h) // 2

        # Draw semi-transparent background for the overlay
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        box_bg = self.ui.colors["box_bg"] # Use existing box background color
        sdl2.SDL_SetRenderDrawColor(self.renderer, box_bg.r, box_bg.g, box_bg.b, 220) # Slightly less transparent
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(overlay_x, overlay_y, overlay_w, overlay_h))
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

        # Draw border
        self.ui.draw_rounded_rect(overlay_x, overlay_y, overlay_w, overlay_h, "yellow")

        # Draw message
        message_lines = self.exit_overlay_message.split(', ') # Split into lines for better display
        line_height = self.ui.get_text_size("Test")[1] # Get height of a single line of text
        total_text_h = len(message_lines) * line_height
        text_start_y = overlay_y + (overlay_h - total_text_h) // 2

        for i, line in enumerate(message_lines):
            tw, th = self.ui.get_text_size(line)
            text_x = overlay_x + (overlay_w - tw) // 2
            self.ui.draw_text(line, text_x, text_start_y + i * line_height, "white")

        # Add control hints
        confirm_label_str = "A" if self.controls["confirm"] == BTN_A else "B"
        cancel_label_str = "B" if self.controls["cancel"] == BTN_B else "A"
        hint_text = f"[{cancel_label_str}] Exit / [{confirm_label_str}] Cancel"
        hint_tw, hint_th = self.ui.get_text_size(hint_text, small=True)
        self.ui.draw_text(hint_text, overlay_x + (overlay_w - hint_tw) // 2, overlay_y + overlay_h - hint_th - 5, "gray", small=True)

    def _render_error_overlay(self):
        """Renders a fullscreen error overlay if the API is unreachable."""
        if not self.api_error_active:
            return

        overlay_w = 480
        overlay_h = 160
        overlay_x = (self.width - overlay_w) // 2
        overlay_y = (self.height - overlay_h) // 2

        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 0, 0, 230) # Dark red background
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(overlay_x, overlay_y, overlay_w, overlay_h))
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

        self.ui.draw_rounded_rect(overlay_x, overlay_y, overlay_w, overlay_h, "red")
        
        title = "CONNECTION ERROR"
        tw, _ = self.ui.get_text_size(title, large=True)
        self.ui.draw_text(title, overlay_x + (overlay_w - tw) // 2, overlay_y + 20, "red", large=True)
        
        # Show truncated error message
        msg = self.api_error_message
        display_msg = self.ui.truncate_text(msg, overlay_w - 40, small=True)
        tw2, _ = self.ui.get_text_size(display_msg, small=True)
        self.ui.draw_text(display_msg, overlay_x + (overlay_w - tw2) // 2, overlay_y + 75, "white", small=True)
        
        hint = "Press any button to dismiss and retry."
        tw3, th3 = self.ui.get_text_size(hint, small=True)
        self.ui.draw_text(hint, overlay_x + (overlay_w - tw3) // 2, overlay_y + overlay_h - th3 - 15, "gray", small=True)

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
        """Divides the screen into Header, Main Area (3 columns), Console, and Controls Bar with optimized spacing."""
        # 1. Header (46 px)
        logo_tex = self.domain_icons.get("ha_logo")
        line1 = "HOME ASSISTANT"
        
        # New logo dimensions (50% smaller)
        new_logo_w = 32
        new_logo_h = 32
        spacing = 30 # Distance between logo and text

        tw1, _ = self.ui.get_text_size(line1, xl=True)
        
        # Recalculate total width for centering the block (logo + text)
        total_width = (new_logo_w if logo_tex else 0) + (spacing if logo_tex else 0) + tw1
        block_start_x = (self.width - total_width) // 2

        # Render logo
        if logo_tex:
            logo_y = (self.header_h - new_logo_h) // 2 # Center vertically in the new header
            sdl2.SDL_RenderCopy(self.renderer, logo_tex, None, sdl2.SDL_Rect(block_start_x, logo_y, new_logo_w, new_logo_h))
            text_start_x = block_start_x + new_logo_w + spacing
        else:
            text_start_x = block_start_x # If no logo, text starts at block-start

        # Render text (8px moved up)
        self.ui.draw_text(line1, text_start_x, 0, "white", xl=True)

        # 2. Left column (152 px): Categories + Settings
        cat_box_h = self.main_area_h - 40 - self.v_gap
        self.ui.draw_retro_box(self.col1_x, self.main_y, self.col1_w, cat_box_h, "CATEGORIES")
        self.draw_menu(self.col1_x + self.margin, self.main_y + 13, cat_box_h)
        
        set_box_y = self.main_y + cat_box_h + self.v_gap
        self.ui.draw_retro_box(self.col1_x, set_box_y, self.col1_w, 40, "SETTINGS")
        self._render_settings_entry(self.col1_x + self.margin, set_box_y + 13)

        # 3. Middle column (228 px): Entities
        title = "SETTINGS" if self.settings_active else "ENTITIES"
        self.ui.draw_retro_box(self.col2_x, self.main_y, self.col2_w, self.main_area_h, title)
        if self.settings_active:
            self._render_settings_panel(self.col2_x + self.margin, self.main_y + 13, self.main_area_h)
        else:
            self._render_entities_list(self.col2_x + self.margin, self.main_y + 13, self.main_area_h)

        # 4. Right column (192 px): Details + Preview
        # Preview at 4:3 for col3_w(192) is 144px
        preview_h = 144
        details_h = self.main_area_h - preview_h - self.v_gap
        
        details_box_color = "yellow" if self.active_list == "details" else "cyan"
        self.ui.draw_retro_box(self.col3_x, self.main_y, self.col3_w, details_h, "DETAILS", color=details_box_color, title_color="cyan")
        self._render_details_box(self.col3_x + self.margin, self.main_y + 13, self.col3_w - 2 * self.margin, details_h - 20)
        
        preview_y = self.main_y + details_h + self.v_gap
        self.ui.draw_retro_box(self.col3_x, preview_y, self.col3_w, preview_h, "PREVIEW")
        self._render_preview_box(self.col3_x + self.margin, preview_y + 13, self.col3_w - 2 * self.margin, preview_h - 20)

        # 5. Bottom Row: Console (Left/Center) + System (Right)
        # Console width covers col 1 and col 2
        console_w = self.col2_x + self.col2_w - self.col1_x
        self.ui.draw_retro_box(self.col1_x, self.console_y, console_w, self.console_h, "CONSOLE")
        self._render_console_log(self.col1_x + self.margin, self.console_y + 10)

        # System Box moved down next to Console
        self.ui.draw_retro_box(self.col3_x, self.console_y, self.col3_w, self.console_h, "SYSTEM")
        self._render_system_infos_box(self.col3_x + self.margin, self.console_y + 9)
        
        self._render_controls_bar(self.h_gap, self.controls_bar_y)

    def _render_settings_entry(self, x, y_pos):
        """Renders the settings icon and text in its separate box."""
        icon_tex = self.domain_icons.get("settings")
        icon_w = 24
        if icon_tex:
            dst = sdl2.SDL_Rect(int(x), int(y_pos - 3), icon_w, icon_w)
            sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
            icon_w += 10
        
        if self.active_list == "settings": # If the settings entry itself is selected in the left column
            # Selection logic for settings box
            highlight_w = self.col1_w - self.margin
            self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y_pos - 5), highlight_w, 30, color="cyan")
            self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y_pos - 5), highlight_w, 30, "cyan")
            self.ui.draw_pointer(int(self.col1_x + (self.margin - 10) // 2 - 5 + self.pulse_x), y_pos + 2, width=10, height=16, color="cyan", alpha=self.pulse_alpha)
            self.ui.draw_text("Settings", x + icon_w, y_pos - 2, "white")
        else:
            self.ui.draw_text("Settings", x + icon_w, y_pos - 2, "cyan")

    def _render_settings_panel(self, x, y, box_h):
        """Renders the settings options in the middle column."""
        highlight_w = self.col2_w - self.margin
        
        # Calculate available height for list items
        list_start_y = y + 30 # Start Y for the list content
        available_h = box_h - (list_start_y - y) - 10 # Total box height - (padding above list) - (padding below list)
        item_h = 28
        visible_items = available_h // item_h

        if self.settings_view == "menu":
            menu_items = [
                ("Visible Categories", "categories"), 
                ("Display Brightness", "brightness"),
                ("Flash Color", "favorites"),
                ("WiFi Debug", "wifi_err"),
                ("Server Connection", "wifi_0")
            ]
            for i, (label, icon_key) in enumerate(menu_items):
                is_selected = (self.settings_active and self.active_list == "entities" and self.settings_index == i) # Check if this item is selected
                
                # Calculate vertical position for the current item
                current_item_y = y + (i * item_h)

                # Render icon
                icon_tex = self.domain_icons.get(icon_key)
                if icon_tex:
                    # Center icon vertically within the item_h space
                    icon_size = 24
                    icon_draw_y = int(current_item_y + (item_h - icon_size) // 2)
                    dst = sdl2.SDL_Rect(int(x), icon_draw_y, icon_size, icon_size)
                    sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)

                if is_selected:
                    color = "cyan"
                    # Highlight and rounded rect should cover the entire item height
                    self.ui.draw_selection_highlight(int(x - self.margin // 2), int(current_item_y - 1), highlight_w, item_h, color="cyan")
                    self.ui.draw_rounded_rect(int(x - self.margin // 2), int(current_item_y - 1), highlight_w, item_h, "cyan")
                    
                    # Pointer should be vertically centered with the item
                    pointer_y = int(current_item_y + (item_h - 16) // 2) # 16 is pointer height
                    self.ui.draw_pointer(int(self.col2_x + (self.margin - 10) // 2 - 5 + self.pulse_x), pointer_y, width=10, height=16, color="cyan", alpha=self.pulse_alpha)
                else:
                    color = "white"
                
                # Text should be vertically centered with the item
                text_w, text_h = self.ui.get_text_size(label)
                text_draw_y = int(current_item_y + (item_h - text_h) // 2)
                self.ui.draw_text(label, x + 34, text_draw_y, color)

        elif self.settings_view == "categories":
            self.ui.draw_text("Visible Categories:", x, y, "cyan")
            y_list_start = y + 30
            hidden = self.config.get("hidden_domains", [])
            
            start = self.settings_scroll_row
            end = min(len(VIEWABLE_DOMAINS), start + visible_items)

            for i in range(start, end):
                domain = VIEWABLE_DOMAINS[i]
                y_list = y_list_start + ((i - start) * item_h)
                is_hidden = domain in hidden
                
                is_selected = (self.settings_active and self.active_list == "entities" and i == self.settings_index)
                if is_selected:
                    color = "cyan"
                    self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y_list - 1), highlight_w, item_h, color="cyan")
                    self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y_list - 1), highlight_w, item_h, "cyan")
                    self.ui.draw_pointer(int(x - self.margin - self.SCROLLBAR_WIDTH - 5 + self.pulse_x), y_list + 10, color="cyan", alpha=self.pulse_alpha)
                else:
                    color = "white"

                # Render status icon (on/off checkbox style)
                status_icon_name = "binary_sensor_off" if is_hidden else "binary_sensor_on"
                status_tex = self.domain_icons.get(status_icon_name)
                icon_size = 20

                if status_tex:
                    # Apply color: Yellow for active/on, Grey for inactive/off
                    icon_color = COLOR_YELLOW if not is_hidden else COLOR_GREY
                    sdl2.SDL_SetTextureColorMod(status_tex, icon_color.r, icon_color.g, icon_color.b)
                    
                    dst = sdl2.SDL_Rect(int(x), int(y_list + 2), icon_size, icon_size)
                    sdl2.SDL_RenderCopy(self.renderer, status_tex, None, dst)
                    sdl2.SDL_SetTextureColorMod(status_tex, 255, 255, 255) # Reset
                
                self.ui.draw_text(domain.replace("_", "-").capitalize(), x + icon_size + 8, y_list + 2, color, small=True)
            
            # Scrollbar for settings list
            if len(VIEWABLE_DOMAINS) > visible_items:
                self.ui.draw_scrollbar(
                    int(self.col2_x + self.col2_w - self.SCROLLBAR_WIDTH - 4), y_list_start, box_h - 48,
                    self.settings_scroll_row, len(VIEWABLE_DOMAINS), visible_items
                )
        
        elif self.settings_view == "brightness": # Brightness settings
            self.ui.draw_text("Display Brightness:", x, y, "cyan")
            y_bar = y + 50
            # Draw a simple bar
            bar_w = highlight_w - 40
            self.ui.draw_rounded_rect(int(x), int(y_bar), bar_w, 20, "white")
            # Fill bar based on brightness
            fill_w = int((self.current_brightness / 100.0) * (bar_w - 6))
            sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
            sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_CYAN.r, COLOR_CYAN.g, COLOR_CYAN.b, COLOR_CYAN.a)
            sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x + 3, y_bar + 3, fill_w, 14))
            
            self.ui.draw_text(f"{self.current_brightness}%", x + bar_w + 10, y_bar, "white")
            self.ui.draw_text("Use D-Pad Left/Right", x, y_bar + 40, "gray", small=True)

        elif self.settings_view == "flash_color":
            self.ui.draw_text("Select Flash Color:", x, y, "cyan")
            y_list_start = y + 30
            current_color = self.config.get("flash_color", "yellow")
            
            for i, col in enumerate(self.flash_colors):
                y_list = y_list_start + (i * item_h)
                is_selected = (self.settings_active and self.active_list == "entities" and i == self.settings_index)
                is_active = (col == current_color)
                
                if is_selected:
                    color = "cyan"
                    self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y_list - 1), highlight_w, item_h, color="cyan")
                    self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y_list - 1), highlight_w, item_h, "cyan")
                    self.ui.draw_pointer(int(x - self.margin - self.SCROLLBAR_WIDTH - 5 + self.pulse_x), y_list + 10, color="cyan", alpha=self.pulse_alpha)
                else:
                    color = "white"
                
                # Draw indicator for currently active color
                if is_active:
                    self.ui.draw_text(">", x, y_list + 2, "yellow", small=True)
                
                # Render color name with the actual color for preview
                self.ui.draw_text(col.capitalize(), x + 20, y_list + 2, color, small=True)
                # Draw a small preview box of the color
                self.ui.draw_rounded_rect(int(x + highlight_w - 40), int(y_list + 2), 20, 16, col)

        elif self.settings_view == "wifidebug":
            self._render_wifi_debug_view(x, y, box_h)
        elif self.settings_view == "edit_url":
            self._render_edit_url_view(x, y)
        elif self.settings_view == "connection":
            self._render_connection_view(x, y)

    def draw_menu(self, x, y_start, box_h):
        """Draws the navigation menu with pointer and highlight."""
        if not self.domain_list:
            self.ui.draw_text("Loading...", x, y_start, "cyan")
            return

        item_h = 28
        # Balanced buffer to keep elements and scrollbar track inside box
        visible_cats = (box_h - 10) // item_h 
        start = self.cat_scroll_row
        end = min(len(self.domain_list), start + visible_cats)

        for i in range(start, end):
            domain = self.domain_list[i]
            y_pos = y_start + ((i - start) * item_h)
            label = domain.replace("_", "-").capitalize()
            
            # Search for icon in self.domain_icons
            icon_tex = self.domain_icons.get(domain) or self.domain_icons.get(f"{domain}_on")
            icon_w = 0
            if icon_tex:
                icon_w = 24
                # Render icon slightly vertically offset
                dst = sdl2.SDL_Rect(int(x), int(y_pos + 1), icon_w, icon_w) # Icon 1 pixel higher
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst) # Render icon
                icon_w += 10 # Spacing to text
            
            if self.active_list == "domains" and i == self.nav_index:
                # 1. Highlight background
                highlight_w = self.col1_w - self.margin
                highlight_color = "red" if (self.reorder_mode and self.active_list == "domains") else "cyan"
                
                self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y_pos), highlight_w, item_h, color=highlight_color)
                
                # 1.1 Border around selection (1px rounded, same color as pointer)
                self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y_pos), highlight_w, item_h, highlight_color)
                
                # 2. Selection triangle (pointer) - only when domain list is active
                if self.active_list == "domains":
                    self.ui.draw_pointer(int(self.col1_x + (self.margin - 10) // 2 - 5 + self.pulse_x), y_pos + 5, width=10, height=16, color=highlight_color, alpha=self.pulse_alpha)
                
                # 3. Active text
                self.ui.draw_text(label, x + icon_w, y_pos + 2, "white") # Text 2 pixels lower
            else:
                # Normal text
                self.ui.draw_text(label, x + icon_w, y_pos + 2, "cyan") # Text 2 pixels lower

        # Scrollbar for the categories list
        if len(self.domain_list) > visible_cats:
            self.ui.draw_scrollbar(
                int(self.col1_x + self.col1_w - self.SCROLLBAR_WIDTH - 4), y_start, box_h - 18,
                self.cat_scroll_row, len(self.domain_list), visible_cats
            )

    def _render_entities_list(self, x, y_start, box_h):
        """Renders the list of entities for the currently selected domain."""
        if not self.domain_list or self.nav_index >= len(self.domain_list):
            self.ui.draw_text("Waiting for data...", x, y_start, "gray", small=True)
            return
            
        current_domain = self.domain_list[self.nav_index]
        entities = self.entities_by_domain.get(current_domain, [])
        item_h = 28
        # Balanced buffer to keep elements and scrollbar track inside box
        visible_entities = (box_h - 15) // item_h 
        start = self.entity_scroll_row
        end = min(len(entities), start + visible_entities)
        
        for i in range(start, end):
            entity = entities[i]
            y = y_start + ((i - start) * item_h)
            
            # Selection visuals
            highlight_w = self.col2_w - self.margin
            is_selected = (self.active_list == "entities" and i == self.entity_index)
            if is_selected:
                if self.reorder_mode:
                    # Red highlight for reorder mode
                    flash_color = "red"
                else:
                    # Visual feedback flash (0.3 seconds in configurable color)
                    is_flashing = (time.time() - self.fav_flash_time < 0.3)
                    flash_color = self.config.get("flash_color", "yellow") if is_flashing else "cyan"
                
                self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y - 1), highlight_w, item_h, color=flash_color)
                self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y - 1), highlight_w, item_h, flash_color)
                self.ui.draw_pointer(int(self.col2_x + (self.margin - 10) // 2 - 5 + self.pulse_x), y + 7, width=10, height=16, color=flash_color, alpha=self.pulse_alpha)
            
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

                dst = sdl2.SDL_Rect(int(x), int(y + 2), icon_offset, icon_offset)
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
            max_chars = 20
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
                int(self.col2_x + self.col2_w - self.SCROLLBAR_WIDTH - 4), y_start, box_h - 18,
                self.entity_scroll_row, len(entities), visible_entities
            )

    def run(self):
        self.init_sdl()
        self.load_data()

        try:
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

                # Periodic background refresh of states (every 1.5 seconds)
                if time.time() - self.last_auto_refresh_time > 1.5:
                    if not self.current_task_thread or not self.current_task_thread.is_alive():
                        self._start_background_task("load_data", self._fetch_states_background)
                        self.last_auto_refresh_time = time.time()

                self.render()
                # Cap to ~30 FPS to save battery and reduce CPU load on handhelds
                sdl2.SDL_Delay(33)
        except KeyboardInterrupt:
            pass # Clean exit on Ctrl+C
        finally:
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
                res = task_result["result"]
                self.states = res["states"]
                self.active_url = res["url"]
                self.url_type = res["url_type"]
                self.load_entities()
                self.last_sync_time = time.strftime("%H:%M:%S")
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
                self.last_sync_time = time.strftime("%H:%M:%S")
                if favorite:
                    changes = changed_favorites([favorite], before_states, self.states)
                    self.set_message(f"Executed: {changes[0]}" if changes else "Executed")
                else:
                    self.set_message("Executed")
        else:  # status == "error"
            err_msg = str(task_result['error'])
            self.set_message(f"Error: {err_msg}")
            if task_result["type"] == "load_data":
                self.api_error_active = True
                self.api_error_message = f"HA API unreachable: {err_msg}"

    def _collect_wifi_debug_info(self):
        """Gathers detailed WiFi information for debugging."""
        info = [f"IP Address: {self.ip_address}", ""]
        
        # 1. Check sysfs interfaces
        try:
            if os.path.exists("/sys/class/net"):
                ifaces = os.listdir("/sys/class/net")
                info.append(f"Interfaces: {', '.join(ifaces)}")
                for iface in ifaces:
                    if iface == "lo": continue
                    info.append(f"Checking {iface}:")
                    for node in ["wireless/link", "wireless/level", "signal"]:
                        p = f"/sys/class/net/{iface}/{node}"
                        if os.path.exists(p):
                            with open(p, 'r') as f:
                                info.append(f"  - {node}: {f.read().strip()}")
                    for proc_node in [f"/proc/net/rtl8723ds/{iface}/signal", f"/proc/net/rtl8188fu/{iface}/signal"]:
                        if os.path.exists(proc_node):
                            with open(proc_node, 'r') as f:
                                info.append(f"  - Realtek signal: {f.read().strip()}")
                    oper_p = f"/sys/class/net/{iface}/operstate"
                    if os.path.exists(oper_p):
                        with open(oper_p, 'r') as f:
                            info.append(f"  - operstate: {f.read().strip()}")
        except Exception as e:
            info.append(f"Sysfs Error: {str(e)}")

        # 2. Check proc/net/wireless (Fixed: append separately)
        info.append("") 
        info.append("Raw /proc/net/wireless content:")
        try:
            if os.path.exists("/proc/net/wireless"):
                with open("/proc/net/wireless", 'r') as f:
                    for line in f:
                        info.append(f"  {line.strip()}")
            else:
                info.append("  [File missing]")
        except Exception as e:
            info.append(f"  [Read Error: {str(e)}]")
            
        return info

    def _render_wifi_debug_view(self, x, y, box_h):
        """Renders the scrollable WiFi debug console."""
        self.ui.draw_text("WiFi Debug (Use D-Pad to scroll):", x, y, "cyan")
        y_start = y + 30
        debug_info = self._collect_wifi_debug_info()
        item_h = 15
        visible_lines = (box_h - 45) // item_h
        start = self.settings_scroll_row
        end = min(len(debug_info), start + visible_lines)
        for i in range(start, end):
            line_y = y_start + (i - start) * item_h
            self.ui.draw_text(debug_info[i], x, line_y, "white", small=True)

    def _render_connection_view(self, x, y):
        """Renders the current server connection details."""
        self.ui.draw_text("Server Connection:", x, y, "cyan")
        y += 35
        
        urls = [
            ("Primary URL", self.config.get("base_url", "")),
            ("Alternative URL", self.config.get("alternative_url", ""))
        ]

        for i, (label, val) in enumerate(urls):
            is_sel = (self.settings_index == i)
            highlight_w = self.col2_w - self.margin
            
            if is_sel:
                self.ui.draw_selection_highlight(int(x - self.margin // 2), int(y - 1), highlight_w, 45, color="cyan")
                self.ui.draw_rounded_rect(int(x - self.margin // 2), int(y - 1), highlight_w, 45, "cyan")

            self.ui.draw_text(label + ":", x, y, "cyan" if not is_sel else "white", small=True)
            y += 15
            display_val = self.ui.truncate_text(val if val else "[Not Set]", self.col2_w - 30, small=True)
            self.ui.draw_text(display_val, x, y, "white" if val else "gray", small=True)
            y += 35

        self.ui.draw_text("Press Confirm to Edit", x, y + 20, "gray", small=True)

    def _render_edit_url_view(self, x, y):
        """Renders the character-by-character URL editor."""
        label = "Primary URL" if self.edit_target_key == "base_url" else "Alternative URL"
        self.ui.draw_text(f"Edit {label}:", x, y, "cyan", small=True)
        y += 20

        # Display current buffer
        display_text = self.ui.truncate_text(self.edit_buffer + "_", self.col2_w - 20, small=True)
        self.ui.draw_text(display_text, x, y, "white", small=True)
        y += 30

        # Render Keyboard Grid
        kb_x_start = x
        key_w = 18
        key_h = 22
        
        for r_idx, row in enumerate(self.kb_layout):
            cur_x = kb_x_start
            for c_idx, key in enumerate(row):
                is_sel = (self.kb_row == r_idx and self.kb_col == c_idx)
                
                # Special width for command buttons in the last row
                actual_key_w = key_w
                if isinstance(row, list):
                    tw, _ = self.ui.get_text_size(key, small=True)
                    actual_key_w = tw + 8
                
                text_color = "white" if not is_sel else "black"
                if key == "Shift" and self.kb_shift:
                    text_color = "yellow" if not is_sel else "black"

                if is_sel:
                    self.ui.draw_selection_highlight(int(cur_x - 2), int(y - 2), actual_key_w, key_h, color="cyan")
                    self.ui.draw_rounded_rect(int(cur_x - 2), int(y - 2), actual_key_w, key_h, "cyan")
                
                self.ui.draw_text(key, cur_x, y, text_color, small=True)
                cur_x += actual_key_w + 4
            y += key_h + 4
            
        y += 10
        self.ui.draw_text("X: Backspace | Confirm: Type", x, y, "gray", small=True)

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
    print("I, K / R-Stick      : Scroll Details (PC / Handheld)")
    print("Start / S-Key       : Open App Settings")
    print("-" * 50 + "\n")
    app.run()