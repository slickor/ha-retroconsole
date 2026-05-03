from __future__ import annotations

import pygame

ACTION_QUIT = "quit"
ACTION_UP = "up"
ACTION_DOWN = "down"
ACTION_SELECT = "select"
ACTION_BACK = "back"
ACTION_REFRESH = "refresh"
ACTION_FAVORITES = "favorites"


def map_event(event: pygame.event.Event) -> str | None:
    if event.type == pygame.QUIT:
        return ACTION_QUIT
    if event.type != pygame.KEYDOWN:
        return None

    if event.key in {pygame.K_ESCAPE, pygame.K_q}:
        return ACTION_BACK
    if event.key == pygame.K_UP:
        return ACTION_UP
    if event.key == pygame.K_DOWN:
        return ACTION_DOWN
    if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_a, pygame.K_SPACE}:
        return ACTION_SELECT
    if event.key == pygame.K_b:
        return ACTION_BACK
    if event.key == pygame.K_r:
        return ACTION_REFRESH
    if event.key in {pygame.K_y, pygame.K_f}:
        return ACTION_FAVORITES
    return None


def poll_actions() -> list[str]:
    actions: list[str] = []
    for event in pygame.event.get():
        action = map_event(event)
        if action is not None:
            actions.append(action)
    return actions
