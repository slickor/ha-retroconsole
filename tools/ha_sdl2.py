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

from ha_client import (
    SUPPORTED_ACTIONS,
    call_service,
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
        self.selected = 0
        self.picker_selected = 0
        self.picker_scroll = 0
        self.mode = "main"
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
        self.task_queue = queue.Queue()
        self.current_task_thread = None
        self.game_controllers = []

    def init_sdl(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER)
        sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG)
        ttf.TTF_Init()
        self.window = sdl2.SDL_CreateWindow(
            b"HA RetroConsole", 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            self.width, self.height, 0
        )
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        
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
        except Exception as e:
            self.task_queue.put({"status": "error", "error": str(e), "type": self.pending_task_type})

    def _find_icon(self, icon_dir, name):
        png_path = os.path.join(icon_dir, f"{name}.png")
        if os.path.exists(png_path):
            return png_path
        return os.path.join(icon_dir, f"{name}.bmp")

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
        if self.config_path is None:
            return
        save_config(self.config_path, self.config)

    def load_entities(self):
        entities = []
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
        self.picker_scroll = 0

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
                        self.mode = "main"
                        self.set_message("Favorites editor closed")
                    else:
                        self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    if self.mode == "main":
                        self.selected = max(0, self.selected - 1)
                    else:
                        self.picker_selected = max(0, self.picker_selected - 1)
                        if self.picker_selected < self.picker_scroll:
                            self.picker_scroll = self.picker_selected
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    if self.mode == "main":
                        self.selected = min(len(self.favorites) - 1, self.selected + 1)
                    else:
                        self.picker_selected = min(len(self.entities) - 1, self.picker_selected + 1)
                        visible_rows = max((self.height - 90 - 60) // 28, 1)
                        if self.picker_selected >= self.picker_scroll + visible_rows:
                            self.picker_scroll = self.picker_selected - visible_rows + 1
                elif event.key.keysym.sym in {sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER}:
                    if self.mode == "main":
                        self.execute_action()
                    else:
                        if self.entities:
                            entity = self.entities[self.picker_selected]
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
                        self.mode = "main"
                        self.set_message("Favorites editor closed")
                    else:
                        self.running = False
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    if self.mode == "main":
                        self.selected = max(0, self.selected - 1)
                    else:
                        self.picker_selected = max(0, self.picker_selected - 1)
                        if self.picker_selected < self.picker_scroll:
                            self.picker_scroll = self.picker_selected
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    if self.mode == "main":
                        self.selected = min(len(self.favorites) - 1, self.selected + 1)
                    else:
                        self.picker_selected = min(len(self.entities) - 1, self.picker_selected + 1)
                        visible_rows = max((self.height - 90 - 60) // 28, 1)
                        if self.picker_selected >= self.picker_scroll + visible_rows:
                            self.picker_scroll = self.picker_selected - visible_rows + 1
                elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:  # A button (South) -> Select/Execute
                    if self.mode == "main":
                        self.execute_action()
                    else:
                        if self.entities:
                            entity = self.entities[self.picker_selected]
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
        title = "HA RetroConsole" 
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
        y = 60
        if not self.favorites:
            self.render_text("No favorites configured. Press F to edit.", 20, y, COLOR_TEXT)
            y += 30
        for i, fav in enumerate(self.favorites):
            entity_id = favorite_entity_id(fav)
            state = self.states.get(entity_id, {})
            state_str = state.get('state', 'unknown')
            label = favorite_label(fav, state)
            domain = entity_domain(entity_id)
            
            if i == self.selected:
                self.render_selection_bar(y)
            
            color = COLOR_HIGHLIGHT if i == self.selected else COLOR_TEXT
            state_color = COLOR_SUCCESS if state_str == "on" else COLOR_TEXT_DIM
            
            # Try state-specific icon first (e.g., light_on), then generic domain icon
            icon_key = f"{domain}_{state_str}" if f"{domain}_{state_str}" in self.domain_icons else domain
            icon_tex = self.domain_icons.get(icon_key)
            
            if icon_tex:
                # Apply color mod based on state
                if state_str == "on":
                    if domain == "light":
                        sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_HIGHLIGHT.r, COLOR_HIGHLIGHT.g, COLOR_HIGHLIGHT.b)
                    else:
                        sdl2.SDL_SetTextureColorMod(icon_tex, COLOR_SUCCESS.r, COLOR_SUCCESS.g, COLOR_SUCCESS.b)
                else:
                    sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)

                dst = sdl2.SDL_Rect(25, y, 24, 24)
                sdl2.SDL_RenderCopy(self.renderer, icon_tex, None, dst)
                # Reset color mod for next usage
                sdl2.SDL_SetTextureColorMod(icon_tex, 255, 255, 255)
                self.render_text(label, 60, y, color)
            else:
                icon_text = self.get_domain_icon(entity_id)
                self.render_text(f"{icon_text} {label}", 25, y, color)

            self.render_text_small(state_str, self.width - 100, y + 4, state_color)
            y += 30

        self.render_text_small("Up/Down: Navigate | Enter: Execute | F: Edit favorites | R: Refresh | Esc: Exit", 20, self.height - 40, COLOR_TEXT)
        # Show message for 1 second
        if self.message and (time.time() - self.message_time < 1.0):
            self.render_text_small(self.message, 20, self.height - 20, COLOR_TEXT)

    def render_favorites_editor(self):
        favorite_ids = {favorite_entity_id(fav) for fav in self.favorites}
        y = 60
        visible_rows = max((self.height - 90 - 60) // 28, 1)
        start = self.picker_scroll
        end = min(len(self.entities), start + visible_rows)
        
        current_domain = None

        for i in range(start, end):
            entity = self.entities[i]
            
            # Domain group header
            if entity["domain"] != current_domain:
                current_domain = entity["domain"]
                # (Optional: rendering a small domain label could go here)

            marker = "*" if entity["entity_id"] in favorite_ids else " "
            
            if i == self.picker_selected:
                self.render_selection_bar(y, height=26)
                
            color = COLOR_HIGHLIGHT if i == self.picker_selected else COLOR_TEXT
            domain = entity["domain"]
            state_str = entity["state"]
            
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
                self.render_text(f"[{marker}]", 15, y, color)
                self.render_text(entity['label'], 75, y, color)
            else:
                icon_text = self.get_domain_icon(entity["entity_id"])
                self.render_text(f"[{marker}] {icon_text} {entity['label']}", 25, y, color)

            self.render_text_small(entity['state'], self.width - 100, y + 4, COLOR_TEXT_DIM)
            y += 28

        self.render_text_small("Up/Down: Navigate | Enter: Toggle favorite | R: Refresh | Esc: Back", 20, self.height - 40, COLOR_TEXT)
        if self.message and (time.time() - self.message_time < 1.0):
            self.render_text_small(self.message, 20, self.height - 20, COLOR_TEXT)

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