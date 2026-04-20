import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pygame

from colors import Colors, Assets
from graphics import GraphicsContext
from map import Map, GridEdge, Rail, GridPoint, SignalType, Train, SignalState


@dataclass
class Destination(ABC):
    @abstractmethod
    def render(self, graphics: GraphicsContext):
        raise NotImplementedError()

    @abstractmethod
    def update(self, delta_time: float):
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

    has_spawned_train: Train | None = None

    def __hash__(self):
        return hash(id(self))

    def spawn_train(self, destination: Destination):
        rail = self.in_rails[0]
        train = Train(dx=self.dx, current_rail=rail, destination=destination)
        train.current_speed = train.max_speed
        self.map.trains.append(train)
        for rail in self.in_rails:
            if rail.signal_type != SignalType.FROM:
                rail.signal_state = SignalState.RED
        self.has_spawned_train = train

    def update(self, delta_time: float):
        has_out_train = any(train.destination == self for train in self.map.trains)
        for rail in self.out_rails:
            if rail.signal_type != SignalType.NONE:
                rail.signal_state = SignalState.GREEN if has_out_train else SignalState.RED

        if self.has_spawned_train is not None:
            if self.has_spawned_train.current_rail not in self.in_rails:
                self.has_spawned_train = None
                # switch signal back to red
                for rail in self.in_rails:
                    if rail.signal_type != SignalType.NONE:
                        rail.signal_state = SignalState.RED

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
                Rail(GridEdge(GridPoint(map, -2 * dx + x, y + dy * 2), GridPoint(map, -1 * dx + x, y + dy * 1)), is_destination=True),
                Rail(GridEdge(GridPoint(map, -1 * dx + x, y + dy * 1), GridPoint(map, 0 * dx + x, y + dy * 0)), signal_type=SignalType.TO),
            ],
            name=name,
            marker_pos=map.grid_to_pos_float(-1 * dx + x, y - 1.5 + min(dx, 0) + dy),
            marker_icon=Assets.DOM,
        )

    def render(self, graphics: GraphicsContext):
        # graphics.draw_circle("green", self.marker_pos, radius=10)
        # graphics.draw_text(self.name, self.marker_pos, "assets/font.ttf", 22, color=Colors.FONT)
        with graphics.translate(self.marker_pos), graphics.scale_by(0.2):
            graphics.blit(self.marker_icon, self.marker_icon.get_rect(center=(0, 0)))


class Quests:
    def __init__(self, map: Map):
        self.map = map
        self.off_map_destinations = {
            "D": OffMapDestination.make_simple(map, dx=1, dy=0, y=2, name="D"),
            "E": OffMapDestination.make_simple(map, dx=1, dy=0, y=7, name="E"),
            "F": OffMapDestination.make_simple(map, dx=1, dy=1, y=10, name="F"),
            "A": OffMapDestination.make_simple(map, dx=-1, dy=-1, y=2, name="A"),
            "B": OffMapDestination.make_simple(map, dx=-1, dy=0, y=5, name="B"),
            "C": OffMapDestination.make_simple(map, dx=-1, dy=0, y=10, name="C"),
        }
        self.stage_min_scores = {
            1: 0,
            2: 3,
        }
        self.active_sources: list[OffMapDestination] = []
        self.active_destinations: list[Destination] = []
        self.current_stage = 0

    def advance_stage(self):
        self.current_stage += 1

        new_sources = []
        new_destinations = []

        if self.current_stage == 1:
            new_sources.append(self.off_map_destinations["E"])
            new_destinations.append(self.off_map_destinations["B"])
        elif self.current_stage == 2:
            new_sources.append(self.off_map_destinations["B"])
            new_destinations.append(self.off_map_destinations["E"])
        else:
            return False

        for destination in new_destinations:
            for rail in destination.out_rails:
                self.map.place_rail(rail)
            self.active_destinations.append(destination)
        for source in new_sources:
            for rail in source.in_rails:
                self.map.place_rail(rail)
            self.active_sources.append(source)

        return True

    def find_destination(self, dx: int) -> Destination:
        for destination in self.active_destinations:
            if isinstance(destination, OffMapDestination) and destination.dx == -dx:
                return destination
        raise ValueError(f"No destination found for dx={dx}")

    def add_all(self):
        for destination in self.off_map_destinations.values():
            for rail in destination.in_rails + destination.out_rails:
                self.map.place_rail(rail)
            self.active_destinations.append(destination)
            self.active_sources.append(destination)

    def update(self, delta_time: float):
        for destination in set(self.active_destinations) | set(self.active_sources):
            destination.update(delta_time)

        for source in self.active_sources:
            if not source.has_spawned_train:
                new_destination = self.find_destination(source.dx)
                source.spawn_train(new_destination)

        # maybe advance stage
        if self.map.game_state.score_correct_trains >= self.stage_min_scores.get(self.current_stage + 1, math.inf):
            self.advance_stage()

    def render(self, graphics: GraphicsContext):
        for destination in set(self.active_destinations) | set(self.active_sources):
            destination.render(graphics)