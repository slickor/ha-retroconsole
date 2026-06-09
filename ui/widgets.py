from __future__ import annotations

import pygame
from typing import Any

# Colors (retro-friendly palette)
COLOR_BG = (20, 20, 30)
COLOR_BORDER = (80, 120, 160)
COLOR_TEXT = (200, 200, 200)
COLOR_TEXT_HIGHLIGHT = (255, 255, 100)
COLOR_SELECTED = (100, 160, 200)
COLOR_INACTIVE = (100, 100, 100)
COLOR_SUCCESS = (100, 200, 100)
COLOR_ERROR = (200, 100, 100)


def render_text(surface: pygame.Surface, font: pygame.font.Font, text: str, color: tuple[int, int, int], pos: tuple[int, int]) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, pos)


def fit_text(text: str, font: pygame.font.Font, max_width: int) -> str:
    if font.size(text)[0] <= max_width:
        return text
    if max_width <= 20:
        return text[:max_width]
    truncated = text
    while font.size(truncated + "...")[0] > max_width and len(truncated) > 0:
        truncated = truncated[:-1]
    return truncated + "..."


def render_message(surface: pygame.Surface, font: pygame.font.Font, message: str, width: int, y: int) -> None:
    if not message:
        return
    msg_color = COLOR_ERROR if message.lower().startswith("error") else COLOR_SUCCESS
    msg_text = font.render(message, True, msg_color)
    surface.blit(msg_text, (width - msg_text.get_width() - 20, y))

def render_favorites(
    surface: pygame.Surface,
    font_item: pygame.font.Font,
    font_small: pygame.font.Font,
    favorites: list[Any],
    states: dict[str, dict[str, Any]],
    selected: int,
    width: int,
) -> None:
    item_height = 50
    item_y = 80
    visible_items = 5
    start_index = max(0, min(selected - 2, len(favorites) - visible_items))
    end_index = min(len(favorites), start_index + visible_items)

    if not favorites:
        render_text(surface, font_item, "No favorites configured.", COLOR_INACTIVE, (40, item_y))
        return

    from ha_client import favorite_action, favorite_entity_id, favorite_label, resolve_action

    for idx in range(start_index, end_index):
        favorite = favorites[idx]
        entity_id = favorite_entity_id(favorite)
        state = states.get(entity_id)
        label = favorite_label(favorite, state)
        value = state.get("state", "?") if state is not None else "?"
        action = resolve_action(entity_id, favorite_action(favorite))

        is_selected = idx == selected
        is_controllable = action is not None

        bg_rect = pygame.Rect(20, item_y, width - 40, item_height - 5)
        if is_selected:
            pygame.draw.rect(surface, COLOR_SELECTED, bg_rect)
            pygame.draw.rect(surface, COLOR_TEXT_HIGHLIGHT, bg_rect, 2)
        else:
            pygame.draw.rect(surface, COLOR_BORDER, bg_rect, 1)

        text_color = COLOR_TEXT_HIGHLIGHT if is_selected else COLOR_TEXT
        if not is_controllable:
            text_color = COLOR_INACTIVE

        label_text = fit_text(label, font_item, width - 220)
        render_text(surface, font_item, label_text, text_color, (40, item_y + 10))
        value_text = fit_text(str(value).upper(), font_small, 60)
        render_text(surface, font_small, value_text, text_color, (width - 120, item_y + 10))

        marker = "A" if is_controllable else "-"
        marker_color = COLOR_SUCCESS if is_controllable else COLOR_INACTIVE
        marker_text = font_small.render(f"[{marker}]", True, marker_color)
        surface.blit(marker_text, (width - 60, item_y + 10))

        item_y += item_height


def render_entity_picker(
    surface: pygame.Surface,
    font_item: pygame.font.Font,
    font_small: pygame.font.Font,
    entities: list[dict[str, str]],
    selected: int,
    favorite_ids: set[str],
    width: int,
) -> None:
    item_height = 50
    item_y = 80
    visible_items = 5
    start_index = max(0, min(selected - 2, len(entities) - visible_items))
    end_index = min(len(entities), start_index + visible_items)

    if not entities:
        render_text(surface, font_item, "No entities available.", COLOR_INACTIVE, (40, item_y))
        return

    for idx in range(start_index, end_index):
        entity = entities[idx]
        label = entity["label"]
        value = entity["state"].upper()
        marker = "*" if entity["entity_id"] in favorite_ids else " "
        is_selected = idx == selected

        bg_rect = pygame.Rect(20, item_y, width - 40, item_height - 5)
        if is_selected:
            pygame.draw.rect(surface, COLOR_SELECTED, bg_rect)
            pygame.draw.rect(surface, COLOR_TEXT_HIGHLIGHT, bg_rect, 2)
        else:
            pygame.draw.rect(surface, COLOR_BORDER, bg_rect, 1)

        text_color = COLOR_TEXT_HIGHLIGHT if is_selected else COLOR_TEXT
        label_text = fit_text(label, font_item, width - 220)
        render_text(surface, font_item, label_text, text_color, (40, item_y + 10))
        value_text = fit_text(value, font_small, 60)
        render_text(surface, font_small, value_text, text_color, (width - 120, item_y + 10))
        render_text(surface, font_small, f"[{marker}]", COLOR_SUCCESS if marker == "*" else COLOR_INACTIVE, (width - 60, item_y + 10))

        item_y += item_height


def render_graph(
    surface: pygame.Surface,
    font_title: pygame.font.Font,
    font_small: pygame.font.Font,
    label: str,
    history_data: list[dict[str, Any]],
    width: int,
    height: int,
) -> None:
    surface.fill(COLOR_BG)
    
    title_text = fit_text(f"{label} (24h)", font_title, width - 40)
    render_text(surface, font_title, title_text, COLOR_TEXT_HIGHLIGHT, (20, 20))
    
    points = []
    for item in history_data:
        state_str = item.get("state")
        try:
            val = float(state_str)
            points.append(val)
        except (ValueError, TypeError):
            continue
            
    if not points:
        render_text(surface, font_small, "No valid data for graph.", COLOR_INACTIVE, (20, 80))
        return

    min_val = min(points)
    max_val = max(points)
    
    pad_x = 40
    pad_y_top = 80
    pad_y_bottom = 120
    graph_w = width - 2 * pad_x
    graph_h = height - pad_y_top - pad_y_bottom
    
    # Gitter zeichnen
    for i in range(5):
        y = pad_y_top + i * (graph_h / 4)
        pygame.draw.line(surface, COLOR_BORDER, (pad_x, y), (pad_x + graph_w, y), 1)

    # Achsen zeichnen
    pygame.draw.line(surface, COLOR_TEXT, (pad_x, pad_y_top + graph_h), (pad_x + graph_w, pad_y_top + graph_h), 2)
    pygame.draw.line(surface, COLOR_TEXT, (pad_x, pad_y_top), (pad_x, pad_y_top + graph_h), 2)
    
    if max_val == min_val:
        range_val = 1.0
    else:
        range_val = max_val - min_val
        
    num_points = len(points)
    if num_points > 1:
        plotted_lines = []
        for i, val in enumerate(points):
            x = pad_x + (i / (num_points - 1)) * graph_w
            y = pad_y_top + graph_h - ((val - min_val) / range_val) * graph_h
            plotted_lines.append((x, y))
            
        pygame.draw.lines(surface, COLOR_SUCCESS, False, plotted_lines, 2)
    
    # Min/Max Labels
    render_text(surface, font_small, f"Max: {max_val:.1f}", COLOR_TEXT, (pad_x + 5, pad_y_top - 15))
    render_text(surface, font_small, f"Min: {min_val:.1f}", COLOR_TEXT, (pad_x + 5, pad_y_top + graph_h + 5))

def render_favorites_grid(
    surface: pygame.Surface,
    font_item: pygame.font.Font,
    font_small: pygame.font.Font,
    favorites: list[Any],
    states: dict[str, dict[str, Any]],
    selected: int,
    width: int,
) -> None:
    if not favorites:
        render_text(surface, font_item, "No favorites configured.", COLOR_INACTIVE, (40, 80))
        return

    from ha_client import favorite_action, favorite_entity_id, favorite_label, resolve_action

    cols = 3
    rows = 3
    items_per_page = cols * rows
    current_page = selected // items_per_page
    start_index = current_page * items_per_page
    end_index = min(len(favorites), start_index + items_per_page)

    tile_w = 180
    tile_h = 80
    pad_x = 20
    pad_y = 15

    total_w = cols * tile_w + (cols - 1) * pad_x
    start_x = (width - total_w) // 2
    start_y = 80

    for idx in range(start_index, end_index):
        favorite = favorites[idx]
        entity_id = favorite_entity_id(favorite)
        state = states.get(entity_id)
        label = favorite_label(favorite, state)
        value = state.get("state", "?") if state is not None else "?"
        action = resolve_action(entity_id, favorite_action(favorite))

        is_selected = idx == selected
        is_controllable = action is not None

        rel_idx = idx - start_index
        col = rel_idx % cols
        row = rel_idx // cols

        x = start_x + col * (tile_w + pad_x)
        y = start_y + row * (tile_h + pad_y)

        bg_rect = pygame.Rect(x, y, tile_w, tile_h)
        if is_selected:
            pygame.draw.rect(surface, COLOR_SELECTED, bg_rect)
            pygame.draw.rect(surface, COLOR_TEXT_HIGHLIGHT, bg_rect, 2)
        else:
            pygame.draw.rect(surface, COLOR_BORDER, bg_rect, 1)

        text_color = COLOR_TEXT_HIGHLIGHT if is_selected else COLOR_TEXT
        if not is_controllable:
            text_color = COLOR_INACTIVE

        # Render Label
        label_text = fit_text(label, font_item, tile_w - 20)
        render_text(surface, font_item, label_text, text_color, (x + 10, y + 10))
        
        # Render Value
        value_text = fit_text(str(value).upper(), font_small, tile_w - 40)
        render_text(surface, font_small, value_text, text_color, (x + 10, y + tile_h - 25))

        # Render Marker
        marker = "A" if is_controllable else "-"
        marker_color = COLOR_SUCCESS if is_controllable else COLOR_INACTIVE
        marker_text = font_small.render(f"[{marker}]", True, marker_color)
        surface.blit(marker_text, (x + tile_w - 30, y + tile_h - 25))