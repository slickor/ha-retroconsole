import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + "/..")

import sdl2
import sdl2.ext
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
COLOR_HIGHLIGHT = sdl2.SDL_Color(255, 255, 0, 255)
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

    def init_sdl(self):
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
        ttf.TTF_Init()
        self.window = sdl2.SDL_CreateWindow(
            b"HA SDL2 Test", 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            self.width, self.height, 0
        )
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        font_candidates = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\verdana.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
        ]
        selected_font = None
        for candidate in font_candidates:
            font = ttf.TTF_OpenFont(candidate.encode("utf-8"), 24)
            if font:
                selected_font = candidate
                self.font = font
                break
        if not self.font:
            raise SystemExit("Could not load any Windows font; check your font path.")

        self.font_small = ttf.TTF_OpenFont(selected_font.encode("utf-8"), 16)
        if not self.font_small:
            raise SystemExit(f"Could not load small font from: {selected_font}")

    def load_data(self):
        try:
            self.states = fetch_states_map(
                self.config["base_url"], 
                self.config["token"], 
                timeout=10.0
            )
            self.message = "Connected"
            if self.mode == "favorites":
                self.load_entities()
        except Exception as e:
            self.message = f"Error: {str(e)}"

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
            self.message = "Entity is read-only"
            return

        domain, service = resolved
        previous = self.states.get(entity_id)
        previous_state = str(previous.get("state", "")) if previous is not None else None

        try:
            call_service(
                self.config["base_url"],
                self.config["token"],
                domain,
                service,
                entity_id,
                timeout=10.0,
            )
            self.states = refresh_after_action(
                self.config["base_url"],
                self.config["token"],
                10.0,
                entity_id,
                previous_state,
            )
            self.message = f"Executed {service} on {entity_id}"
        except Exception as e:
            self.message = f"Error: {str(e)}"

    def handle_input(self):
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                self.running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    if self.mode == "favorites":
                        self.mode = "main"
                        self.message = "Favorites editor closed"
                    else:
                        self.running = False
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    if self.mode == "main":
                        self.selected = max(0, self.selected - 1)
                    else:
                        self.picker_selected = max(0, self.picker_selected - 1)
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    if self.mode == "main":
                        self.selected = min(len(self.favorites) - 1, self.selected + 1)
                    else:
                        self.picker_selected = min(len(self.entities) - 1, self.picker_selected + 1)
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
                        self.message = "Edit favorites"
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    self.load_data()
                    self.message = "Refreshed"

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

    def render(self):
        sdl2.SDL_SetRenderDrawColor(self.renderer, COLOR_BG.r, COLOR_BG.g, COLOR_BG.b, COLOR_BG.a)
        sdl2.SDL_RenderClear(self.renderer)

        # Header
        title = "HA SDL2 Test"
        if self.mode == "favorites":
            title = "Favorites Editor"
        self.render_text(title, 20, 20, COLOR_HIGHLIGHT)

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
            label = favorite_label(fav, state)
            color = COLOR_HIGHLIGHT if i == self.selected else COLOR_TEXT
            self.render_text(f"{label} ({state.get('state', 'unknown')})", 20, y, color)
            y += 30

        self.render_text_small("Up/Down: Navigate | Enter: Execute | F: Edit favorites | R: Refresh | Esc: Exit", 20, self.height - 40, COLOR_TEXT)
        if self.message:
            self.render_text_small(self.message, 20, self.height - 20, COLOR_TEXT)

    def render_favorites_editor(self):
        favorite_ids = {favorite_entity_id(fav) for fav in self.favorites}
        y = 60
        for i, entity in enumerate(self.entities):
            marker = "*" if entity["entity_id"] in favorite_ids else " "
            color = COLOR_HIGHLIGHT if i == self.picker_selected else COLOR_TEXT
            self.render_text(f"[{marker}] {entity['label']} ({entity['state']})", 20, y, color)
            y += 28
            if y > self.height - 90:
                break

        self.render_text_small("Up/Down: Navigate | Enter: Toggle favorite | R: Refresh | Esc: Back", 20, self.height - 40, COLOR_TEXT)
        if self.message:
            self.render_text_small(self.message, 20, self.height - 20, COLOR_TEXT)

    def run(self):
        self.init_sdl()
        self.load_data()
        while self.running:
            self.handle_input()
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
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        ttf.TTF_Quit()
        sdl2.SDL_Quit()

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    
    config_path = Path(args.config)
    app = HASDL2App(config_path)
    app.run()