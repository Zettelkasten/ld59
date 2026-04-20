import os
import pickle

import numpy as np
import pygame
from numpy.ma.core import outer
from pygame import Surface
from pygame.event import Event

from building import BuildRails, BuildSignals, SwitchSignalsAndSwitches
from colors import Colors, Assets
from graphics import GraphicsContext
from map import Map, GridEdge, GridPoint, Rail, SignalType, Switch, Train
from quests import Quests

import better_exchook
better_exchook.install()


class GameState:
    def __init__(self):
        self.score_correct_trains = 0
        self.supersampling = 2
        self.camera_scale = 1.0
        self.camera_offset = np.asarray([75.0, 100.0])

        self.mouse_pos = np.asarray([0.0, 0.0])

        self.map = Map(self)
        # initial rails
        if not self.load_map():
            self.reset_map()

        self.quests = Quests(self.map)
        self.quests.advance_stage()

        # initial train
        # initial_rail = self.map.placed_rails[GridEdge(GridPoint(self.map, -2, 2), GridPoint(self.map, -1, 2))]
        # train = Train(dx=1, current_rail=initial_rail)
        # train.current_speed = train.max_speed
        # self.map.trains.append(train)

        # building mode
        self.building_mode = BuildRails(self)

    def render(self, outer_surface: Surface):
        surface = pygame.Surface(np.asarray(outer_surface.get_size()) * self.supersampling, pygame.SRCALPHA)

        outer_surface.fill(Colors.BACKGROUND)

        offset = self.camera_offset

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
        self.building_mode.render(graphics)
        self.quests.render(graphics)

    def render_ui(self, graphics: GraphicsContext, width: float, height: float):
        graphics.draw_text("frittytracks", pos=np.asarray([width / 2, 50]), font_name="assets/font.ttf", font_size=22, color="white")
        graphics.draw_text(
            f"Score: {self.score_correct_trains}", pos=np.asarray([width - 75, 50]), font_name="assets/font.ttf", font_size=22, color="white", align="right")

        button_size = 100.0
        uis = [
            Assets.UI_DEFAULT,
            Assets.UI_TRACK,
            Assets.UI_SIGNAL,
            Assets.UI_DEMOLISH,
            Assets.UI_FAST,
        ]
        # TODO make them clickable
        with graphics.translate([(width - (len(uis) - 1) * button_size) / 2, height - 100]):
            for i, ui in enumerate(uis):
                with graphics.translate([i * button_size, 0]), graphics.scale_by(0.15):
                    graphics.blit(ui, dest=ui.get_rect(center=(0, 0)))

    def update(self, delta_time: float):
        self.map.update(delta_time)
        self.quests.update(delta_time)

    def on_motion(self, event: Event):
        self.mouse_pos = event.pos

    def on_click(self, event: Event):
        self.mouse_pos = event.pos

        self.building_mode.on_click()

    @property
    def mouse_pos_inv_camera(self):
        return np.asarray(self.mouse_pos) / self.camera_scale - self.camera_offset

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
        if event.key == pygame.K_ESCAPE:
            self.on_escape()
        elif event.key == pygame.K_0:
            self.building_mode = SwitchSignalsAndSwitches(self)
        elif event.key == pygame.K_1:
            self.building_mode = BuildRails(self)
        elif event.key == pygame.K_2:
            self.building_mode = BuildSignals(self)
        elif event.key == pygame.K_9:
            self.map.simulation_speed = 5.0 if self.map.simulation_speed == 1.0 else 1.0
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

    def save_map(self):
        print("saving")
        pickle.dump(self.map, open("map.pkl", "wb"))

    def load_map(self):
        if os.path.exists("map.pkl"):
            self.map = pickle.load(open("map.pkl", "rb"))
            return True
        else:
            return False

    def reset_map(self):
        self.map = Map(self)
        # self.map.place_rail(Rail(GridEdge(GridPoint(self.map, -2, 2), GridPoint(self.map, -1, 2))))
        # self.map.place_rail(Rail(GridEdge(GridPoint(self.map, -1, 2), GridPoint(self.map, 0, 2)), signal_type=SignalType.FROM))
