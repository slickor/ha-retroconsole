import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf
import ctypes
from typing import Any, Dict, Tuple

class RetroUI:
    def __init__(self, renderer: Any, font_path: str, font_size: int = 24):
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
            "blue":   sdl2.SDL_Color(0, 163, 255, 255),
            "cyan":   sdl2.SDL_Color(0, 163, 255, 255),
            "yellow": sdl2.SDL_Color(238, 176, 0, 255),
            "green":  sdl2.SDL_Color(0, 255, 128, 255),
            "gray":   sdl2.SDL_Color(85, 85, 85, 255),
            "grey":   sdl2.SDL_Color(85, 85, 85, 255),
            "red":    sdl2.SDL_Color(255, 0, 0, 255),
            "magenta":sdl2.SDL_Color(255, 0, 255, 255),
            "white":  sdl2.SDL_Color(255, 255, 255, 255),
            "black":  sdl2.SDL_Color(0, 0, 0, 255),
            "box_bg": sdl2.SDL_Color(0, 19, 41, 180), # Semi-transparent blue
            "scrollbar_track": sdl2.SDL_Color(40, 40, 40, 255)
        }
        self._text_cache: Dict[str, Tuple[Any, int, int]] = {}

    def get_text_size(self, text: str, small: bool = False, large: bool = False, xl: bool = False) -> Tuple[int, int]:
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

    def truncate_text(self, text: str, max_width: int, small: bool = False, large: bool = False, xl: bool = False) -> str:
        """Truncates text to fit within max_width, adding '...' if truncated."""
        if not text:
            return ""
        
        font = self._get_font(small, large, xl)
        tw, _ = self.get_text_size(text, small, large, xl)
        
        if tw <= max_width:
            return text
        
        # Binary search for the longest substring that fits
        low, high = 0, len(text)
        best_fit_len = 0
        
        while low <= high:
            mid = (low + high) // 2
            if mid == 0: low = mid + 1; continue # Avoid empty string check
            test_text = text[:mid]
            test_tw, _ = self.get_text_size(test_text + "...", small, large, xl) # Check with ellipsis
            if test_tw <= max_width: best_fit_len = mid; low = mid + 1
            else: high = mid - 1
        return text[:best_fit_len] + "..." if best_fit_len > 0 else "..."

    def draw_text(self, text: str, x: int, y: int, color: Any = "cyan", small: bool = False, large: bool = False, xl: bool = False) -> Tuple[int, int]:
        """Renders text (supports strings or SDL_Color objects)."""
        # Resolve color
        if isinstance(color, str):
            sdl_color = self.colors.get(color.lower(), self.colors["cyan"])
            color_id = color
        else: # Assume it's an SDL_Color object
            sdl_color = color
            color_id = f"{color.r}{color.g}{color.b}{color.a}"
        
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
    
    def _get_font(self, small: bool, large: bool, xl: bool):
        if xl: return self.font_xl
        if large: return self.font_large
        if small: return self.font_small
        return self.font

    def draw_selection_highlight(self, x: int, y: int, w: int, h: int, color: Any = "cyan"):
        """Draws a semi-transparent rectangle for highlighting."""
        sdl_color = self.colors.get(color.lower(), self.colors["cyan"]) if isinstance(color, str) else color
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, 50) # Selected color with ~20% Alpha
        
        # Rounded fill (pixel style: corners excluded)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x + 1, y, w - 2, h))
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x, y + 1, w, h - 2))
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def draw_scanlines(self, x: int, y: int, w: int, h: int, spacing: int = 3):
        """Draws a retro scanline pattern over a specific area."""
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        # Very subtle cyan with high transparency for CRT look
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 163, 255, 40)
        
        for line_y in range(y, y + h, spacing):
            sdl2.SDL_RenderDrawLine(self.renderer, x, line_y, x + w, line_y)
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def draw_pointer(self, x: int, y: int, width: int = 10, height: int = 16, color: Any = "cyan", alpha: int = 255):
        """Draws a sturdy selection triangle (pointer) with a 2px white border and optional alpha pulsing."""
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)

        # 1. Draw white border (2px larger in all directions)
        border_color = self.colors["white"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, border_color.r, border_color.g, border_color.b, alpha)
        for i in range(width + 4):
            # Proportional height scaling for the border
            offset = int(i * ((height + 4) / 2.0) / (width + 4))
            sdl2.SDL_RenderDrawLine(self.renderer, x - 2 + i, y - 2 + offset, x - 2 + i, y - 2 + (height + 4) - 1 - offset)

        # 2. Draw the main pointer inside
        sdl_color = self.colors.get(color.lower(), self.colors["cyan"]) if isinstance(color, str) else color
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, alpha)
        
        for i in range(width):
            offset = int(i * (height / 2.0) / width)
            sdl2.SDL_RenderDrawLine(self.renderer, x + i, y + offset, x + i, y + height - 1 - offset)

        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

    def draw_rounded_rect(self, x: int, y: int, w: int, h: int, color: Any = "cyan"):
        """Helper function for rounded frames in retro pixel style."""
        sdl_color = self.colors.get(color, self.colors["cyan"]) if isinstance(color, str) else color
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, 255)
        
        # 2-pixel rounding logic for a "rounder" look
        # Main lines (indented by 3 pixels)
        sdl2.SDL_RenderDrawLine(self.renderer, x + 3, y, x + w - 4, y)             # Top
        sdl2.SDL_RenderDrawLine(self.renderer, x + 3, y + h - 1, x + w - 4, y + h - 1) # Bottom
        sdl2.SDL_RenderDrawLine(self.renderer, x, y + 3, x, y + h - 4)             # Left
        sdl2.SDL_RenderDrawLine(self.renderer, x + w - 1, y + 3, x + w - 1, y + h - 4) # Right
        
        # TL corner
        sdl2.SDL_RenderDrawPoint(self.renderer, x + 2, y + 1); sdl2.SDL_RenderDrawPoint(self.renderer, x + 1, y + 2)
        # TR corner
        sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 3, y + 1); sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 2, y + 2)
        # BL corner
        sdl2.SDL_RenderDrawPoint(self.renderer, x + 2, y + h - 2); sdl2.SDL_RenderDrawPoint(self.renderer, x + 1, y + h - 3)
        # BR corner
        sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 3, y + h - 2); sdl2.SDL_RenderDrawPoint(self.renderer, x + w - 2, y + h - 3)

    def draw_retro_box(self, x: int, y: int, w: int, h: int, title: str = "", color: Any = "cyan", title_color: Any = None):
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
            t_color = title_color if title_color else color
            tw, th = self.get_text_size(title) # Use normal font size for box titles
            # Break line
            clear_rect = sdl2.SDL_Rect(x + 15, y, tw + 10, 2) # Clear 2px for a cleaner break
            bg = self.colors["bg"]
            sdl2.SDL_SetRenderDrawColor(self.renderer, bg.r, bg.g, bg.b, 255)
            sdl2.SDL_RenderFillRect(self.renderer, clear_rect)
            # Draw title
            self.draw_text(title, x + 20, y - (th // 2), color=t_color)

    def clear_screen(self):
        """Clears the screen with the cyberpunk background color."""
        bg = self.colors["bg"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, bg.r, bg.g, bg.b, 255)
        sdl2.SDL_RenderClear(self.renderer)

    def draw_scrollbar(self, x: int, y: int, h: int, current_start: int, total_count: int, visible_count: int):
        """Draws a vertical scrollbar proportional to the list state."""
        if total_count <= visible_count:
            return

        # Track background
        track_col = self.colors.get("scrollbar_track", sdl2.SDL_Color(40, 40, 40, 255))
        sdl2.SDL_SetRenderDrawColor(self.renderer, track_col.r, track_col.g, track_col.b, track_col.a)
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
        cyan_col = self.colors["cyan"]
        sdl2.SDL_SetRenderDrawColor(self.renderer, cyan_col.r, cyan_col.g, cyan_col.b, cyan_col.a)
        handle_rect = sdl2.SDL_Rect(x, handle_y, 4, handle_h)
        sdl2.SDL_RenderFillRect(self.renderer, handle_rect)

    def draw_graph(self, x: int, y: int, w: int, h: int, data_points: list, color: Any = "cyan"):
        """Draws a line graph with a Y-axis and horizontal grid lines."""
        if not data_points or len(data_points) < 2:
            self.draw_text("Not enough data", x + w//2 - 40, y + h//2, "gray", small=True)
            return

        is_tuple = isinstance(data_points[0], tuple)
        values = [p[0] for p in data_points] if is_tuple else data_points

        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val
        if val_range == 0:
            val_range = 1  # avoid division by zero

        y_axis_w = 40
        x_axis_h = 25 if is_tuple else 0
        gx = x + y_axis_w
        gy = y
        gw = w - y_axis_w
        gh = h - x_axis_h

        # Draw grid lines and Y-axis labels
        grid_lines = 5
        grid_color = sdl2.SDL_Color(50, 50, 50, 255) # Dark gray
        
        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
        for i in range(grid_lines):
            # i=0 is top (max_val), i=grid_lines-1 is bottom (min_val)
            pct = i / (grid_lines - 1)
            val = max_val - (pct * val_range)
            line_y = gy + int(pct * gh)
            
            # Draw label
            val_str = f"{val:.1f}"
            self.draw_text(val_str, x, line_y - 8, "gray", small=True)
            
            # Draw grid line
            sdl2.SDL_SetRenderDrawColor(self.renderer, grid_color.r, grid_color.g, grid_color.b, 255)
            sdl2.SDL_RenderDrawLine(self.renderer, gx, line_y, gx + gw, line_y)

        # Draw X-axis labels if available
        if is_tuple:
            num_labels = 5
            for i in range(num_labels):
                idx = int(i * (len(data_points) - 1) / (num_labels - 1))
                label_str = data_points[idx][1]
                lx = gx + int(i * gw / (num_labels - 1))
                tw, _ = self.get_text_size(label_str, small=True)
                draw_x = lx - tw // 2
                if draw_x < gx: draw_x = gx
                if draw_x + tw > gx + gw: draw_x = gx + gw - tw
                self.draw_text(label_str, draw_x, gy + gh + 5, "gray", small=True)
                sdl2.SDL_SetRenderDrawColor(self.renderer, grid_color.r, grid_color.g, grid_color.b, 255)
                sdl2.SDL_RenderDrawLine(self.renderer, lx, gy + gh, lx, gy + gh + 5)

        sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_NONE)

        # Draw actual graph line
        sdl_color = self.colors.get(color, self.colors["cyan"]) if isinstance(color, str) else color
        sdl2.SDL_SetRenderDrawColor(self.renderer, sdl_color.r, sdl_color.g, sdl_color.b, 255)

        points = []
        for i, val in enumerate(values):
            px = gx + int(i * gw / (len(values) - 1))
            py = gy + gh - int((val - min_val) / val_range * gh)
            points.append((px, py))

        for i in range(len(points) - 1):
            sdl2.SDL_RenderDrawLine(self.renderer, points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            sdl2.SDL_RenderDrawLine(self.renderer, points[i][0], points[i][1]+1, points[i+1][0], points[i+1][1]+1)

    def change_font(self, font_path: str, font_size: int = 24):
        """Changes the font dynamically at runtime, closing old fonts and clearing the text cache."""
        if self.font:
            ttf.TTF_CloseFont(self.font)
        if self.font_small:
            ttf.TTF_CloseFont(self.font_small)
        if self.font_large:
            ttf.TTF_CloseFont(self.font_large)
        if self.font_xl:
            ttf.TTF_CloseFont(self.font_xl)
            
        self.font = ttf.TTF_OpenFont(font_path.encode('utf-8'), font_size)
        self.font_small = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 0.75))
        self.font_large = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 1.5))
        self.font_xl = ttf.TTF_OpenFont(font_path.encode('utf-8'), int(font_size * 2.5))
        
        if not self.font or not self.font_small or not self.font_large or not self.font_xl:
            raise RuntimeError(f"Could not load fonts: {ttf.TTF_GetError()}")
            
        self.clear_text_cache()

    def clear_text_cache(self):
        """Destroys all cached text textures and clears the text cache."""
        for tex, w, h in self._text_cache.values():
            sdl2.SDL_DestroyTexture(tex)
        self._text_cache.clear()

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