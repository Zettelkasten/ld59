import os
import pickle

import numpy as np
import pygame
from pygame import Surface
from pygame.event import Event

from building import BuildRails, BuildSignals, SwitchSignalsAndSwitches
from graphics import GraphicsContext
from map import Map, GridEdge, GridPoint, Rail, SignalType, Switch, Train


class GameState:
    def __init__(self):
        self.supersampling = 4
        self.camera_scale = 1.0
        self.camera_offset = np.asarray([75.0, 100.0])

        self.mouse_pos = np.asarray([0.0, 0.0])

        self.map = Map()
        # initial rails
        if not self.load_map():
            self.reset_map()

        # initial train
        initial_rail = self.map.placed_rails[GridEdge(GridPoint(self.map, -2, 2), GridPoint(self.map, -1, 2))]
        self.map.trains.append(Train(dx=1, current_rail=initial_rail))

        # building mode
        self.building_mode = BuildRails(self)

    def render(self, outer_surface: Surface):
        surface = pygame.Surface(np.asarray(outer_surface.get_size()) * self.supersampling, pygame.SRCALPHA)

        outer_surface.fill("blue")

        offset = self.camera_offset

        graphics = GraphicsContext(surface)
        g = GraphicsContext(outer_surface)
        g.draw_line(color="green", start_pos=np.asarray([-20, 0]), end_pos=np.asarray([20, 0]), width=2)

        with graphics.scale_by(self.camera_scale * self.supersampling), graphics.translate(offset):
            self.render_inner(graphics)

        surface = pygame.transform.smoothscale_by(surface, 1 / self.supersampling)
        outer_surface.blit(surface, (0, 0))

    def render_inner(self, graphics: GraphicsContext):
        self.map.render(graphics)
        self.building_mode.render(graphics)

    def update(self, delta_time: float):
        self.map.update(delta_time)

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
        elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.save_map()
        elif event.key == pygame.K_r and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.reset_map()

    def on_escape(self):
        self.building_mode.__init__(self)

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
        self.map = Map()
        self.map.place_rail(Rail(GridEdge(GridPoint(self.map, -2, 2), GridPoint(self.map, -1, 2))))
        self.map.place_rail(Rail(GridEdge(GridPoint(self.map, -1, 2), GridPoint(self.map, 0, 2)), signal_type=SignalType.FROM))
        self.map.place_rail(Rail(GridEdge(GridPoint(self.map, Map.GRID_WIDTH - 1, 6), GridPoint(self.map, Map.GRID_WIDTH, 6)), signal_type=SignalType.TO))
        self.map.place_rail(Rail(GridEdge(GridPoint(self.map, Map.GRID_WIDTH, 6), GridPoint(self.map, Map.GRID_WIDTH + 1, 6))))
