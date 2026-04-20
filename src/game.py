import os
import pickle

import numpy as np
import pygame
from numpy.ma.core import outer
from pygame import Surface
from pygame.event import Event

from building import BuildRails, BuildSignals, SwitchSignalsAndSwitches, DemolishRails
from colors import Colors, Assets
from graphics import GraphicsContext
from map import Map, GridPoint, Rail, SignalType, Switch, Train
from quests import Quests


class GameState:
    def __init__(self):
        self.score_correct_trains = 0
        self.supersampling = 2
        self.camera_scale = 1.0
        self.camera_offset = np.asarray([100.0, 100.0])

        self.mouse_pos = np.asarray([0.0, 0.0])
        self.ui_selected: int | None = None

        self.map = Map(self)
        self.game_over = False
        self.play_explosion_pos: None | np.ndarray = None

        self.global_time = 0

        self.quests = Quests(self.map)
        self.quests.advance_stage()
        # self.quests.add_all()

        # building mode
        self.building_mode = BuildRails(self)

    def render(self, outer_surface: Surface):
        surface = pygame.Surface(np.asarray(outer_surface.get_size()) * self.supersampling, pygame.SRCALPHA)

        outer_surface.fill(Colors.BACKGROUND)

        offset = self.camera_offset

        # adjust camera scale to fit picture
        self.camera_scale = outer_surface.get_width() * self.supersampling / ((self.map.GRID_WIDTH + 3) * self.map.DIST)

        graphics = GraphicsContext(surface)
        g = GraphicsContext(outer_surface)

        with graphics.scale_by(self.supersampling):
            with graphics.scale_by(self.camera_scale), graphics.translate(offset):
                self.render_inner(graphics)

            self.render_ui(graphics, width=outer_surface.get_width(), height=outer_surface.get_height())

        surface = pygame.transform.smoothscale_by(surface, 1 / self.supersampling)

        outer_surface.blit(surface, (0, 0))

    def render_inner(self, graphics: GraphicsContext):
        self.map.render(graphics)
        if not self.game_over:
            self.building_mode.render(graphics)
        self.quests.render(graphics)

        if self.play_explosion_pos is not None:
            img = Assets.EXPLOSIONS[int(self.global_time * 3) % len(Assets.EXPLOSIONS)]
            with graphics.translate(self.play_explosion_pos + [0, 30]), graphics.scale_by(0.5):
                graphics.blit(img, dest=img.get_rect(bottom=0, centerx=0))

        self.map.render_ui(graphics)

    def render_ui(self, graphics: GraphicsContext, width: float, height: float):
        is_paused = self.map.simulation_speed == 0.0
        is_fast = self.map.simulation_speed > 1.0
        uis = [
            (Assets.UI_DEFAULT, Assets.UI_DEFAULT_ACTIVE, isinstance(self.building_mode, SwitchSignalsAndSwitches), 0.0, "set signals and switch track junctions"),
            (Assets.UI_TRACK,Assets.UI_TRACK_ACTIVE,  isinstance(self.building_mode, BuildRails), 100.0, "lay some track"),
            (Assets.UI_SIGNAL, Assets.UI_SIGNAL_ACTIVE, isinstance(self.building_mode, BuildSignals), 100.0, "build and remove signals"),
            (Assets.UI_DEMOLISH, Assets.UI_DEMOLISH_ACTIVE, False, 120.0, "demolish some track"),
            (Assets.UI_SLOW, Assets.UI_FAST, is_fast, 120.0, "back to slow" if is_fast else "speed up the game"),
            (Assets.UI_PLAY, Assets.UI_PAUSE, is_paused, 100.0, "resume" if is_paused else "pause"),
        ]
        total_width = sum(button_width for _, _, _, button_width, _ in uis)

        self.ui_selected = None
        if not self.game_over:
            with graphics.translate([(width - total_width) / 2, height - 100]):
                offset_x = 0
                for i, (ui, active_ui, is_active, button_width, _) in enumerate(uis):
                    offset_x += button_width
                    with graphics.translate([offset_x, 0]), graphics.scale_by(0.15):
                        if graphics.is_in_area(self.mouse_pos, ui.get_rect(center=(0, 0))):
                            self.ui_selected = i
                        if is_active or self.ui_selected == i:
                            ui = active_ui
                            # ui.fill(active_color, special_flags=pygame.BLEND_RGBA_MULT)
                        graphics.blit(ui, dest=ui.get_rect(center=(0, 0)))
        else:
            # game over, render restart button
            drawn_font = graphics.draw_text("Click here to try again", pos=np.asarray([width / 2, height - 100]), font_name="assets/font.ttf", font_size=22, color="white", align="center")
            if graphics.is_in_area(self.mouse_pos, drawn_font.get_rect(center=(width / 2, height - 100))):
                self.ui_selected = 0

        title_text = "switch happens"
        if self.ui_selected is not None:
            _, _, _, _, tooltip = uis[self.ui_selected]
            title_text = tooltip
        if self.game_over:
            title_text = "game over! your trains have crashed!"
        graphics.draw_text(title_text, pos=np.asarray([width / 2, 50]), font_name="assets/font.ttf", font_size=22, color="white")
        to_next_level = self.quests.score_needed_for_next_level()
        if to_next_level is None:
            to_next_level_text = "maximum level reached!"
        else:
            to_next_level_text = f"{to_next_level} more for next level"
        graphics.draw_text(
            to_next_level_text, pos=np.asarray([width - 100 * self.camera_scale, 50]), font_name="assets/font.ttf", font_size=22, color="white", align="right")
        graphics.draw_text(
            f"score: {self.score_correct_trains}", pos=np.asarray([100 * self.camera_scale, 50]), font_name="assets/font.ttf", font_size=22, color="white", align="left")

    def update(self, delta_time: float):
        self.global_time += delta_time
        if self.game_over:
            return
        self.map.update(delta_time)
        self.quests.update(delta_time)

    def on_motion(self, event: Event):
        self.mouse_pos = np.asarray(event.pos) * self.supersampling

    def on_click(self, event: Event):
        self.mouse_pos = np.asarray(event.pos) * self.supersampling

        if not self.game_over:
            self.building_mode.on_click()

        if self.ui_selected is not None:
            if not self.game_over:
                if self.ui_selected == 0:
                    self.building_mode = SwitchSignalsAndSwitches(self)
                elif self.ui_selected == 1:
                    self.building_mode = BuildRails(self)
                elif self.ui_selected == 2:
                    self.building_mode = BuildSignals(self)
                elif self.ui_selected == 3:
                    self.building_mode = DemolishRails(self)
                elif self.ui_selected == 4:
                    self.map.simulation_speed = 8.0 if self.map.simulation_speed == 1.0 else 1.0
                elif self.ui_selected == 5:
                    self.map.simulation_speed = 0.0 if self.map.simulation_speed != 0.0 else 1.0
            else:
                self.reset_game()

    @property
    def mouse_pos_inv_camera(self):
        return np.asarray(self.mouse_pos) / (self.camera_scale * self.supersampling) - self.camera_offset

    def get_grid_point_at_mouse(self) -> GridPoint:
        grid_pos = self.map.pos_to_grid(self.mouse_pos_inv_camera)
        return GridPoint(self.map, round(grid_pos[0]), round(grid_pos[1]))

    def get_grid_rail_at_mouse(self, signals_only: bool = False) -> Rail | None:
        edge_centers = {
            edge: (self.map.grid_to_pos(edge.from_point) + self.map.grid_to_pos(edge.to_point)) / 2
            for edge in self.map.placed_rails
            if not signals_only or self.map.placed_rails[edge].signal_type != SignalType.NONE
        }
        closest_edge = min(edge_centers, key=lambda edge: np.linalg.norm(edge_centers[edge] - self.mouse_pos_inv_camera), default=None)
        if closest_edge is None or np.linalg.norm(edge_centers[closest_edge] - self.mouse_pos_inv_camera) > self.map.DIST / 2:
            return None
        return self.map.placed_rails[closest_edge]

    def get_signal_or_switch_at_mouse(self) -> Rail | Switch | None:
        signal = self.get_grid_rail_at_mouse(signals_only=True)
        switch_point = self.get_grid_point_at_mouse()
        has_left_switch = (switch_point, -1) in self.map.switches
        has_right_switch = (switch_point, 1) in self.map.switches
        if has_left_switch and has_right_switch:
            # depends on which side of the edge was clicked
            switch_dx = 1 if self.mouse_pos_inv_camera[0] >= self.map.grid_to_pos(switch_point)[0] else -1
        elif has_left_switch:
            switch_dx = -1
        elif has_right_switch:
            switch_dx = 1
        else:
            switch_point = None
            switch_dx = None

        if switch_point is not None:
            switch = self.map.switches[(switch_point, switch_dx)]
        else:
            switch = None

        if switch is not None and signal is not None:
            # find closest
            signal_pos = signal.signal_pos_and_arm()[0]
            switch_pos = self.map.grid_to_pos(switch_point)
            if np.linalg.norm(signal_pos - self.mouse_pos_inv_camera) < np.linalg.norm(switch_pos - self.mouse_pos_inv_camera):
                return signal
            else:
                return switch
        elif signal is not None:
            return signal
        elif switch is not None:
            return switch
        else:
            return None

    def on_key_down(self, event):
        if self.game_over:
            return
        if event.key == pygame.K_ESCAPE:
            self.on_escape()
        elif event.key == pygame.K_q or event.key == pygame.K_1:
            self.building_mode = SwitchSignalsAndSwitches(self)
        elif event.key == pygame.K_w or event.key == pygame.K_2:
            self.building_mode = BuildRails(self)
        elif event.key == pygame.K_e or event.key == pygame.K_3:
            self.building_mode = BuildSignals(self)
        elif event.key == pygame.K_r or event.key == pygame.K_4:
            self.building_mode = DemolishRails(self)
        elif event.key == pygame.K_t or event.key == pygame.K_5 or event.key == pygame.K_SPACE:
            self.map.simulation_speed = 0.0 if self.map.simulation_speed != 0.0 else 1.0
        elif event.key == pygame.K_y or event.key == pygame.K_z or event.key == pygame.K_6:
            self.map.simulation_speed = 8.0 if self.map.simulation_speed == 1.0 else 1.0
        elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.save_map()
        elif event.key == pygame.K_r and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.reset_map()

    def on_escape(self):
        self.building_mode.__init__(self)

    def on_train_reach_destination(self, train: Train):
        from quests import OffMapDestination
        if not isinstance(train.destination, OffMapDestination):
            right_destination = False
        else:
            right_destination = train.current_rail in train.destination.out_rails
        print("That was the right destination?", right_destination)
        if right_destination:
            self.score_correct_trains += 1
        self.map.trains.remove(train)

    def on_train_collision(self, train: Train, other_train: Train):
        train.crashed = True
        other_train.crashed = True
        self.game_over = True
        self.map.simulation_speed = 0
        pos = (train.current_pos() + other_train.current_pos()) / 2
        self.play_explosion_pos = pos

    def save_map(self):
        print("saving")
        pickle.dump(self.map, open("map.pkl", "wb"))

    def load_map(self):
        if os.path.exists("map.pkl"):
            self.map = pickle.load(open("map.pkl", "rb"))
            return True
        else:
            return False

    def reset_game(self):
        self.__init__()
