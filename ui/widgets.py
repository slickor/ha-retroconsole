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


def render_message(surface: pygame.Surface, font: pygame.font.Font, message: str, width: int, y: int) -> None:
    if not message:
        return
    msg_color = COLOR_ERROR if message.lower().startswith("error") else COLOR_SUCCESS
    msg_text = font.render(message, True, msg_color)
    surface.blit(msg_text, (width - msg_text.get_width() - 20, y))


def render_controls(surface: pygame.Surface, font: pygame.font.Font, width: int, controls_y: int) -> None:
    pygame.draw.line(surface, COLOR_BORDER, (0, controls_y), (width, controls_y), 2)
    controls = [
        "D-Pad: Navigate",
        "A: Execute",
        "X: Refresh",
        "B: Exit",
    ]
    for i, ctrl in enumerate(controls):
        render_text(surface, font, ctrl, COLOR_TEXT, (20, controls_y + 12 + i * 22))


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
    visible_items = 7
    start_index = max(0, min(selected - 3, len(favorites) - visible_items))
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

        render_text(surface, font_item, label[:30], text_color, (40, item_y + 10))
        render_text(surface, font_small, str(value).upper(), text_color, (width - 120, item_y + 10))

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
    visible_items = 7
    start_index = max(0, min(selected - 3, len(entities) - visible_items))
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
        render_text(surface, font_item, label[:30], text_color, (40, item_y + 10))
        render_text(surface, font_small, value, text_color, (width - 120, item_y + 10))
        render_text(surface, font_small, f"[{marker}]", COLOR_SUCCESS if marker == "*" else COLOR_INACTIVE, (width - 60, item_y + 10))

        item_y += item_height