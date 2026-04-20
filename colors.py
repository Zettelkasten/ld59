import pygame


class Colors:
    SIGNAL_RED = "#FF2222"
    SIGNAL_GREEN = "#00FF41"
    TRACKS = "#FFD700"
    BACKGROUND = "#171717"
    BACKGROUND_PLAYABLE = "#0A0A0A"
    SWITCH = "#874BFF"
    TRAIN = "#4BEDFF"

    BUILDING_SELECTED_POINT = "green"
    BUILDING_TRACK = "green"
    BUILDING_SIGNAL = "green"

    FONT = "white"


class Assets:
    SIGNAL = pygame.image.load("assets/signal.svg")
    SIGNAL_RED = pygame.image.load("assets/signal_red.svg")
    SIGNAL_GREEN = pygame.image.load("assets/signal_green.svg")

    TRAIN = pygame.image.load("assets/train.svg")

    DESTINATIONS = {
        name: pygame.image.load(f"assets/destinations/{name}.svg")
        for name in ["anitkabir", "castle", "city", "dom", "factory", "forest", "hiking", "school", "ship"]
    }

    UI_DEFAULT = pygame.image.load("assets/ui_default.svg")
    UI_TRACK = pygame.image.load("assets/ui_track.svg")
    UI_SIGNAL = pygame.image.load("assets/ui_signal.svg")
    UI_DEMOLISH = pygame.image.load("assets/ui_demolish.svg")
    UI_SLOW = pygame.image.load("assets/ui_slow.svg")
    UI_FAST = pygame.image.load("assets/ui_fast.svg")
