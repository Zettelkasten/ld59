import pygame

from game import GameState

TARGET_FPS = 60


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((1000, 600), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    game_state = GameState()

    running = True
    delta_time: float = 0.0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                # if pygame.mouse.get_pressed()[0]:
                #     on_drag(event)
                # else:
                game_state.on_motion(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    game_state.on_click(event)
                elif event.button == 2:
                    game_state.on_escape()
            elif event.type == pygame.KEYDOWN:
                game_state.on_key_down(event)
            """
            elif event.type == pygame.MOUSEBUTTONUP:
                on_release(event)
            elif event.type == pygame.KEYUP:
                on_key_up(event)
            elif event.type == pygame.MOUSEWHEEL:
                on_mousewheel(event)
            """

        game_state.update(delta_time=delta_time)
        game_state.render(screen)
        pygame.display.flip()
        delta_time = clock.tick(TARGET_FPS) / 1000

if __name__ == "__main__":
    main()
