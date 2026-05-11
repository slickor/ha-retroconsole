import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf
import ctypes

class RetroUI:
    def __init__(self, renderer, font_path, font_size=24):
        self.renderer = renderer
        # Load font sizes for flexibility
        self.font = ttf.TTF_OpenFont(font_path.encode('utf-8'), font_size)
        self.font_small = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 0.75))
        self.font_large = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 1.5))
        self.font_xl = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 2.5))
        
        if not self.font or not self.font_small or not self.font_large or not self.font_xl:
            raise RuntimeError(f"Could not load fonts: {ttf.TTF_GetError()}")
        
        self.colors = {
            "bg":     sdl2.SDL_Color(10, 10, 15, 255),
            "cyan":   sdl2.SDL_Color(0, 163, 255, 255),
            "yellow": sdl2.SDL_Color(238, 176, 0, 255),
            "gray":   sdl2.SDL_Color(85, 85, 85, 255),
            "white":  sdl2.SDL_Color(255, 255, 255, 255),
            "box_bg": sdl2.SDL_Color(0, 19, 41, 180) # Semi-transparent blue
        }
        self._text_cache = {}

    def get_text_size(self, text, small=False, large=False, xl=False):
        """Returns the width and height of the text."""
        if xl:
            font = self.font_xl
        elif large:
            font = self.font_large
        elif small:
            font = self.font_small
        else:
            font = self.font
        tw, th = ctypes.c_int(), ctypes.c_int()
        ttf.TTF_SizeUTF8(font, text.encode('utf-8'), ctypes.byref(tw), ctypes.byref(th))
        return tw.value, th.value

    def draw_text(self, text, x, y, color="cyan", small=False, large=False, xl=False):
        """Renders text (supports strings or SDL_Color objects)."""
        # Resolve color
        if isinstance(color, str):
            sdl_color = self.colors.get(color, self.colors["cyan"])
            color_id = color
        else: # Assume it's an SDL_Color object
            sdl_color = color
            color_id = f"{color.r}{color.g}{color.b}"
        
        if xl:
            size_id = "xl"
        elif large:
            size_id = "l"
        elif small:
            size_id = "s"
        else:
            size_id = "n"
        cache_key = f"{text}_{color_id}_{size_id}"
        
        if cache_key not in self._text_cache:
            # Prevent memory leaks from dynamic strings (like the clock)
            if len(self._text_cache) > 500:
                for tex, w, h in self._text_cache.values():
                    sdl2.SDL_DestroyTexture(tex)
                self._text_cache.clear()

            if xl:
                font = self.font_xl
            elif large:
                font = self.font_large
            elif small:
                font = self.font_small
            else:
                font = self.font
            surface = ttf.TTF_RenderUTF8_Blended(font, text.encode('utf-8'), sdl_color)
            if not surface: return 0, 0
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            w, h = surface.contents.w, surface.contents.h
            sdl2.SDL_FreeSurface(surface)
            self._text_cache[cache_key] = (texture, w, h)
        
        tex, w, h = self._text_cache[cache_key]
        dst = sdl2.SDL_Rect(int(x), int(y), w, h)
        sdl2.SDL_RenderCopy(self.renderer, tex, None, dst)
        return w, h

    def draw_selection_highlight(self, x, y, w, h):
        """Draws a semi-transparent rectangle for highlighting."""
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 50) # Cyan with ~20% Alpha
        
        # Rounded fill (pixel style: corners excluded)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x + 1, y, w - 2, h))
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x, y + 1, w, h - 2))
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def draw_scanlines(self, x, y, w, h, spacing=3):
        """Draws a retro scanline pattern over a specific area."""
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        # Sehr dezentes Cyan mit hoher Transparenz für den CRT-Look
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 40)
        
        for line_y in range(y, y + h, spacing):
            sdl2.SDL_RenderDrawLine(self.renderer, x, line_y, x + w, line_y)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def draw_pointer(self, x, y, width=12, height=18, color="cyan"):
        """Draws a sturdy selection triangle (pointer) with a 2px white border."""
        # 1. Draw white border (2px larger in all directions)
        border_color = self.colors["white"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, border_color.r, border_color.g, border_color.b, 255)
        for i in range(width + 4):
            # Proportional height scaling for the border
            offset = int(i * ((height + 4) / 2.0) / (width + 4))
            sdl2.SDL_RenderDrawLine(self.renderer, x - 2 + i, y - 2 + offset, x - 2 + i, y - 2 + (height + 4) - 1 - offset)

        # 2. Draw the main pointer inside
        sdl_color = self.colors.get(color, self.colors["cyan"])
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, 255)
        
        for i in range(width):
            offset = int(i * (height / 2.0) / width)
            sdl2.SDL_RenderDrawLine(self.renderer, x + i, y + offset, x + i, y + height - 1 - offset)

    def draw_rounded_rect(self, x, y, w, h, color="cyan"):
        """Helper function for rounded frames in retro pixel style."""
        sdl_color = self.colors.get(color, self.colors["cyan"]) if isinstance(color, str) else color
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, 255)
        
        # Linien (um 2 Pixel eingerückt für die Rundung, exakt innerhalb der Bounds)
        sdl2.SDL_RenderDrawLine(self.renderer, x + 2, y, x + w - 3, y)             # Oben
        sdl2.SDL_RenderDrawLine(self.renderer, x + 2, y + h - 1, x + w - 3, y + h - 1) # Unten
        sdl2.SDL_RenderDrawLine(self.renderer, x, y + 2, x, y + h - 3)             # Links
        sdl2.SDL_RenderDrawLine(self.renderer, x + w - 1, y + 2, x + w - 1, y + h - 3) # Rechts
        
        # Eck-Pixel für die diagonale Rundung
        sdl2.SDL_RenderDrawPoint(self.renderer, x + 1, y + 1)         # TL
        sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 2, y + 1)     # TR
        sdl2.SDL_RenderDrawPoint(self.renderer, x + 1, y + h - 2)     # BL
        sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 2, y + h - 2) # BR

    def draw_retro_box(self, x, y, w, h, title="", color="cyan"):
        """Draws a frame box with a title break."""
        # Semi-transparent background fill
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        box_bg = self.colors["box_bg"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, box_bg.r, box_bg.g, box_bg.b, box_bg.a)
        # Fill the box interior (slightly indented to respect the rounded corners)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x + 1, y + 1, w - 2, h - 2))
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

        self.draw_rounded_rect(x, y, w, h, color)
        
        if title:
            tw, th = self.get_text_size(title) # Use normal font size for box titles
            # Break line
            clear_rect = sdl2.SDL_Rect(x + 15, y, tw + 10, 2) # Clear 2px for a cleaner break
            bg = self.colors["bg"]
            sdl2.SDL_SetRenderDrawColor(self.renderer, bg.r, bg.g, bg.b, 255)
            sdl2.SDL_RenderFillRect(self.renderer, clear_rect)
            # Draw title
            self.draw_text(title, x + 20, y - (th // 2), color=color)

    def clear_screen(self):
        """Clears the screen with the cyberpunk background color."""
        bg = self.colors["bg"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, bg.r, bg.g, bg.b, 255)
        sdl2.SDL_RenderClear(self.renderer)

    def draw_scrollbar(self, x, y, h, current_start, total_count, visible_count):
        """Draws a vertical scrollbar proportional to the list state."""
        if total_count <= visible_count:
            return

        # Track background
        sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
        track_rect = sdl2.SDL_Rect(x, y, 4, h)
        sdl2.SDL_RenderFillRect(self.renderer, track_rect)

        # Handle calculation
        handle_h = max(20, int((visible_count / total_count) * h))
        
        # Calculate position
        scroll_range = h - handle_h
        max_scroll = total_count - visible_count
        progress = current_start / max_scroll
        handle_y = y + int(progress * scroll_range)

        # Draw handle
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 255)
        handle_rect = sdl2.SDL_Rect(x, handle_y, 4, handle_h)
        sdl2.SDL_RenderFillRect(self.renderer, handle_rect)

    def cleanup(self):
        """Frees textures and fonts."""
        for tex, w, h in self._text_cache.values():
            sdl2.SDL_DestroyTexture(tex)
        self._text_cache.clear()
        if self.font:
            ttf.TTF_CloseFont(self.font)
        if self.font_small:
            ttf.TTF_CloseFont(self.font_small)
        if self.font_large:
            ttf.TTF_CloseFont(self.font_large)
        if self.font_xl:
            ttf.TTF_CloseFont(self.font_xl)