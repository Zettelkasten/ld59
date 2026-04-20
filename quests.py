from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pygame

from colors import Colors, Assets
from graphics import GraphicsContext
from map import Map, GridEdge, Rail, GridPoint, SignalType


@dataclass
class Destination(ABC):
    @abstractmethod
    def render(self, graphics: GraphicsContext):
        raise NotImplementedError()

@dataclass
class OnMapDestination(Destination):
    pass

@dataclass
class OffMapDestination(Destination):
    map: Map
    dx: int
    in_rails: list[Rail]
    out_rails: list[Rail]
    name: str
    marker_pos: np.ndarray
    marker_icon: pygame.Surface

    @staticmethod
    def make_simple(map: Map, *, dx: int, dy: int = 0, y: int, name: str):
        assert dx == 1 or dx == -1
        x = 0 if dx == 1 else Map.GRID_WIDTH - 1
        return OffMapDestination(
            map=map,
            dx=dx,
            in_rails=[
                Rail(GridEdge(GridPoint(map, -2 * dx + x, y + dx + dy * 2), GridPoint(map, -1 * dx + x, y + dx + dy * 1))),
                Rail(GridEdge(GridPoint(map, -1 * dx + x, y + dx + dy * 1), GridPoint(map, 0 * dx + x, y + dx + dy * 0)), signal_type=SignalType.FROM),
            ],
            out_rails=[
                Rail(GridEdge(GridPoint(map, -2 * dx + x, y + dy * 2), GridPoint(map, -1 * dx + x, y + dy * 1))),
                Rail(GridEdge(GridPoint(map, -1 * dx + x, y + dy * 1), GridPoint(map, 0 * dx + x, y + dy * 0)), signal_type=SignalType.TO),
            ],
            name=name,
            marker_pos=map.grid_to_pos_float(-1 * dx + x, y - 1.5 + min(dx, 0) + dy),
            marker_icon=Assets.DOM,
        )

    def render(self, graphics: GraphicsContext):
        # self.marker_pos *= 0
        # graphics.draw_circle("green", self.marker_pos, radius=10)
        # graphics.draw_text(self.name, self.marker_pos, "font.ttf", 22, color=Colors.FONT)
        with graphics.translate(self.marker_pos), graphics.scale_by(0.2):
            graphics.blit(self.marker_icon, self.marker_icon.get_rect(center=(0, 0)))


class Quests:

    def __init__(self, map: Map):
        self.map = map
        self.off_map_destinations: list[OffMapDestination] = [
            OffMapDestination.make_simple(map, dx=1, dy=0, y=2, name="D"),
            OffMapDestination.make_simple(map, dx=1, dy=0, y=7, name="E"),
            OffMapDestination.make_simple(map, dx=1, dy=1, y=10, name="F"),
            OffMapDestination.make_simple(map, dx=-1, dy=-1, y=2, name="A"),
            OffMapDestination.make_simple(map, dx=-1, dy=0, y=5, name="B"),
            OffMapDestination.make_simple(map, dx=-1, dy=0, y=10, name="C"),
        ]
        self.active_destinations: list[Destination] = []

    def add_all(self):
        for destination in self.off_map_destinations:
            for rail in destination.in_rails + destination.out_rails:
                self.map.place_rail(rail)
            self.active_destinations.append(destination)

    def render(self, graphics: GraphicsContext):
        for destination in self.active_destinations:
            destination.render(graphics)