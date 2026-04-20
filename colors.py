import pygame


class Colors:
    SIGNAL_RED = "#FF2222"
    SIGNAL_GREEN = "#00FF41"
    TRACKS = "#FFD700"
    BACKGROUND = "#171717"
    BACKGROUND_PLAYABLE = "#0A0A0A"
    SWITCH = "#874BFF"
    TRAIN = "#4BEDFF"
    TRAIN_CRASHED = "#FF2222"

    BUILDING_SELECTED_POINT = "green"
    BUILDING_TRACK = "green"
    BUILDING_SIGNAL = "green"

    UI_ACTIVE = "red"

    FONT = "#F5F5F5"

    POPUP_BACKGROUND = "#262626"
    POPUP_BORDER = "#F5F5F5"



class Assets:
    SIGNAL = pygame.image.load("assets/signal.svg")
    SIGNAL_RED = pygame.image.load("assets/signal_red.svg")
    SIGNAL_GREEN = pygame.image.load("assets/signal_green.svg")

    TRAIN = pygame.image.load("assets/train.svg")

    DESTINATIONS = {
        name: pygame.image.load(f"assets/destinations/{name}.svg")
        for name in ["anitkabir", "castle", "city", "dom", "factory", "forest", "hiking", "school", "ship"]
    }

    EXPLOSIONS = [pygame.image.load(f"assets/explosion_{i}.svg") for i in range(3)]

    UI_DEFAULT = pygame.image.load("assets/ui_default.svg")
    UI_DEFAULT_ACTIVE = pygame.image.load("assets/ui_default_active.svg")
    UI_TRACK = pygame.image.load("assets/ui_track.svg")
    UI_TRACK_ACTIVE = pygame.image.load("assets/ui_track_active.svg")
    UI_SIGNAL = pygame.image.load("assets/ui_signal.svg")
    UI_SIGNAL_ACTIVE = pygame.image.load("assets/ui_signal_active.svg")
    UI_DEMOLISH = pygame.image.load("assets/ui_demolish.svg")
    UI_DEMOLISH_ACTIVE = pygame.image.load("assets/ui_demolish_active.svg")
    UI_PAUSE = pygame.image.load("assets/ui_pause.svg")
    UI_PLAY = pygame.image.load("assets/ui_play.svg")
    UI_SLOW = pygame.image.load("assets/ui_slow.svg")
    UI_FAST = pygame.image.load("assets/ui_fast.svg")
