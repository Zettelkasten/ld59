import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pygame

import story
from colors import Colors, Assets
from graphics import GraphicsContext
from map import Map, GridEdge, Rail, GridPoint, SignalType, Train, SignalState
from story import StoryMessage
from tutorial_highlights import TutorialHighlightDestination


@dataclass
class Destination(ABC):
    map: Map
    name: str
    marker_pos: np.ndarray
    marker_icon: pygame.Surface

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
    dx: int
    in_rails: list[Rail]
    out_rails: list[Rail]

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
                # always green
                rail.signal_state = SignalState.GREEN  # if has_out_train else SignalState.RED

        if self.has_spawned_train is not None:
            if self.has_spawned_train.current_rail not in self.in_rails:
                self.has_spawned_train = None
                # switch signal back to red
                for rail in self.in_rails:
                    if rail.signal_type != SignalType.NONE:
                        rail.signal_state = SignalState.RED

    @staticmethod
    def make_simple(map: Map, *, dx: int, dy: int = 0, y: int, name: str, marker_icon: pygame.Surface):
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
                Rail(GridEdge(GridPoint(map, -1 * dx + x, y + dy * 1), GridPoint(map, 0 * dx + x, y + dy * 0)), signal_type=SignalType.TO, signal_state=SignalState.GREEN),
            ],
            name=name,
            marker_pos=map.grid_to_pos_float(-1 * dx + x, y - 1.5 + min(dx, 0) + dy),
            marker_icon=marker_icon,
        )

    def is_highlighted(self):
        map = self.in_rails[0].edge.map
        return any(
            isinstance(highlight, TutorialHighlightDestination) and highlight.name == self.name
            for highlight in map.game_state.current_highlights())

    def render(self, graphics: GraphicsContext):
        # graphics.draw_circle("green", self.marker_pos, radius=10)
        # graphics.draw_text(self.name, self.marker_pos, "assets/font.ttf", 22, color=Colors.FONT)
        scale = 0.2
        if self.is_highlighted():
            map = self.in_rails[0].edge.map
            scale = map.game_state.add_highlight_to_scale(scale)

        with graphics.translate(self.marker_pos), graphics.scale_by(scale):
            graphics.blit(self.marker_icon, self.marker_icon.get_rect(center=(0, 0)))


class Quests:
    def __init__(self, map: Map):
        self.map = map
        all_marker_icons = list(Assets.DESTINATIONS.values())
        random.shuffle(all_marker_icons)
        i = 0
        def next_marker_icon():
            nonlocal i
            icon = all_marker_icons[i % len(all_marker_icons)]
            i += 1
            return icon

        # sorted anti-clock wise
        self.off_map_destinations = {
            "A": OffMapDestination.make_simple(map, dx=-1, dy=-1, y=2, name="A", marker_icon=next_marker_icon()),
            "B": OffMapDestination.make_simple(map, dx=-1, dy=0, y=5, name="B", marker_icon=next_marker_icon()),
            "C": OffMapDestination.make_simple(map, dx=-1, dy=0, y=10, name="C", marker_icon=next_marker_icon()),
            "D": OffMapDestination.make_simple(map, dx=1, dy=1, y=10, name="D", marker_icon=next_marker_icon()),
            "E": OffMapDestination.make_simple(map, dx=1, dy=0, y=7, name="E", marker_icon=next_marker_icon()),
            "F": OffMapDestination.make_simple(map, dx=1, dy=0, y=2, name="F", marker_icon=next_marker_icon()),
        }
        self.stage_min_scores = {
            1: 0,
            2: 3,
            3: 10,
            4: 30,
            5: 40,
            6: 60,
            7: 80,
            9: 100,
            10: 120,
            11: 150,
        }
        self.active_sources: list[OffMapDestination] = []
        self.active_destinations: list[Destination] = []
        self.current_stage = 0
        self.spawn_cooldown = 13.0
        self.time_since_last_spawn = 10000.0

        self.last_active_source: None | OffMapDestination = None

    def advance_stage(self):
        self.current_stage += 1

        new_sources = []
        new_destinations = []

        if self.current_stage == 1:
            new_sources.append(self.off_map_destinations["E"])
            new_destinations.append(self.off_map_destinations["B"])
        elif self.current_stage == 2:
            new_sources.append(self.off_map_destinations["B"])
            new_destinations.append(self.off_map_destinations["E"])  # have B, E fully
        elif self.current_stage == 3:
            new_destinations.append(self.off_map_destinations["F"])
        elif self.current_stage == 4:
            new_sources.append(self.off_map_destinations["F"])
            new_destinations.append(self.off_map_destinations["C"])  # have B, E, F fully, C out
        elif self.current_stage == 5:
            new_sources.append(self.off_map_destinations["A"])
            new_destinations.append(self.off_map_destinations["A"])  # have A, B, E, F fully, C out
        elif self.current_stage == 6:
            new_destinations.append(self.off_map_destinations["D"])  # have A, B, E, F fully, C, D out
        elif self.current_stage == 7:
            new_sources.append(self.off_map_destinations["D"])  # have A, B, D, E, F fully, C out
        elif self.current_stage == 8:
            new_destinations.append(self.off_map_destinations["G"])  # have A, B, D, E, F fully, C, G out
        elif self.current_stage == 9:
            new_sources.append(self.off_map_destinations["C"])  # have A, B, C, D, E, F fully, G out
        elif self.current_stage == 10:
            new_destinations.append(self.off_map_destinations["G"])  # have A, B, C, D, E, F, G fully
        elif self.current_stage == 11:
            self.map.game_state.message_queue.extend([
                StoryMessage(
                    lines=["congratulations, you have figured it out now!", "all stations are open and everything is running."],
                    is_blocking=True,
                    can_skip_tutorial=False,
                ),
                StoryMessage(
                    lines=["thanks a lot for playing!",
                           "keep going if you want to!"],
                    is_blocking=True,
                    can_skip_tutorial=False,
                )
            ])
        else:
            return False

        for destination in new_destinations:
            if destination in self.active_destinations:
                continue
            for rail in destination.out_rails:
                self.map.place_rail(rail)
            self.active_destinations.append(destination)
        for source in new_sources:
            if source in self.active_sources:
                continue
            for rail in source.in_rails:
                self.map.place_rail(rail)
            self.active_sources.append(source)

        if self.current_stage >= 3:
            # first two already have story
            self.map.game_state.message_queue.extend([
                StoryMessage(
                    lines=["another station just opened up.", "extend your service as needed."],
                    highlights=[TutorialHighlightDestination(name=destination.name) for destination in new_destinations + new_sources],
                    is_blocking=False,
                    auto_continue_with=story.all_stations_connected_somehow,
                    can_skip_tutorial=False,
                )]
            )

        # resort the active sources
        self.active_sources = list(sorted(self.active_sources, key=lambda s: s.name))

        return True

    def find_destination(self, dx: int) -> Destination:
        valid_destinations = []
        for destination in self.active_destinations:
            if isinstance(destination, OffMapDestination) and destination.dx == -dx:
                valid_destinations.append(destination)
        if len(valid_destinations) == 0:
            raise ValueError(f"No valid destination for dx={dx}")
        return random.choice(valid_destinations)

    def add_all(self):
        for destination in self.off_map_destinations.values():
            for rail in destination.in_rails + destination.out_rails:
                self.map.place_rail(rail)
            self.active_destinations.append(destination)
            self.active_sources.append(destination)

    def update(self, delta_time: float):
        for destination in set(self.active_destinations) | set(self.active_sources):
            destination.update(delta_time)

        # spawn trains
        self.maybe_spawn_trains()
        self.time_since_last_spawn += delta_time * self.map.simulation_speed

        # maybe advance stage
        if self.map.game_state.score_correct_trains >= self.stage_min_scores.get(self.current_stage + 1, math.inf):
            self.advance_stage()

    def maybe_spawn_trains(self):
        if self.time_since_last_spawn < self.spawn_cooldown:
            return
        for train in self.map.trains:
            if train.remaining_waiting_time > 0:
                return
        if len(self.active_sources) == 0:
            return
        if self.last_active_source is None and len(self.active_sources) > 0:
            self.last_active_source = self.active_sources[-1]
        # get next active source
        source = self.active_sources[(self.active_sources.index(self.last_active_source) + 1) % len(self.active_sources)]
        if any(train.current_rail in source.in_rails for train in self.map.trains):
            return  # don't spawn if there is already a train on the source

        print("NEXT ACTIVE SOURCE IS", source.name)
        new_destination = self.find_destination(source.dx)
        source.spawn_train(new_destination)
        self.last_active_source = source
        self.time_since_last_spawn = 0.0

    def render(self, graphics: GraphicsContext):
        for destination in set(self.active_destinations) | set(self.active_sources):
            destination.render(graphics)

    def score_needed_for_next_level(self):
        if self.current_stage + 1 not in self.stage_min_scores:
            return None
        return self.stage_min_scores.get(self.current_stage + 1, math.inf) - self.map.game_state.score_correct_trains
