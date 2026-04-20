from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pygame
from pygame import Vector2
from pygame.math import clamp

from colors import Colors, Assets
from entity import Entity

from graphics import GraphicsContext
from math2d import rotate_90deg

if TYPE_CHECKING:
    from quests import Destination

ALLOWED_EDGE_DIFFS = {
    (-1, 0), (-1, -1), (-1, 1),
    (1, 0), (1, -1), (1, 1),
}  # note there is no (0, 1) or (0, -1) because we don't allow vertical rails


@dataclass(frozen=True)
class GridPoint:
    map: "Map"
    x: int
    y: int

    def get_out_edges(self, dx_only: int | None = None):
        return [
            GridEdge(self, GridPoint(self.map, self.x + dx, self.y + dy))
            for (dx, dy) in ALLOWED_EDGE_DIFFS
            if (dx_only is None or dx == dx_only)
        ]

    def render_rail_tick(self, graphics: GraphicsContext, color: str):
        pos = self.map.grid_to_pos(self)
        tick_length = 8.0

        neighbor_dx_dys = {
            (dx, dy)
            for (dx, dy) in ALLOWED_EDGE_DIFFS
            if GridEdge(self, GridPoint(self.map, self.x + dx, self.y + dy)) in self.map.placed_rails
        }

        if ({(-1, -1), (1, 1)} <= neighbor_dx_dys and len(neighbor_dx_dys) <= 3) or (len(neighbor_dx_dys) == 1 and neighbor_dx_dys <= {(-1, -1), (1, 1)}):
            normal = rotate_90deg(np.asarray([self.map.RIGHT[0], self.map.DOWN[1]]))
            normal = normal / np.linalg.norm(normal)
        elif {(1, -1), (-1, 1)} <= neighbor_dx_dys and len(neighbor_dx_dys) <= 3 or (len(neighbor_dx_dys) == 1 and neighbor_dx_dys <= {(1, -1), (-1, 1)}):
            normal = rotate_90deg(np.asarray([self.map.RIGHT[0], -self.map.DOWN[1]]))
            normal = normal / np.linalg.norm(normal)
        else:  # default case
            normal = np.asarray([0.0, 1.0])

        graphics.draw_line(color, pos - normal * tick_length, pos + normal * tick_length, width=2)


@dataclass(frozen=True)
class GridEdge:
    """ UNDIRECTED grid edge """
    from_point: GridPoint
    to_point: GridPoint

    def __post_init__(self):
        diff_x = self.from_point.x - self.to_point.x
        diff_y = self.from_point.y - self.to_point.y
        assert (diff_x, diff_y) in ALLOWED_EDGE_DIFFS
        assert self.from_point.map == self.to_point.map

    @property
    def dx(self):
        return self.to_point.x - self.from_point.x

    @property
    def dy(self):
        return self.to_point.y - self.from_point.y

    def flipped(self):
        return GridEdge(self.to_point, self.from_point)

    @property
    def map(self):
        return self.from_point.map

    def __hash__(self):
        return hash(frozenset((self.from_point, self.to_point)))

    def __eq__(self, other):
        if not isinstance(other, GridEdge):
            return NotImplemented
        return frozenset((self.from_point, self.to_point)) == frozenset((other.from_point, other.to_point))


class SignalType(Enum):
    NONE = "none"
    FROM = "from"
    TO = "to"


class SignalState(Enum):
    RED = "red"
    GREEN = "green"


@dataclass
class Rail(Entity):
    edge: GridEdge
    signal_type: SignalType = SignalType.NONE
    signal_state: SignalState = SignalState.RED
    is_destination: bool = False

    @property
    def length(self):
        from_pos = self.edge.map.grid_to_pos(self.edge.from_point)
        to_pos = self.edge.map.grid_to_pos(self.edge.to_point)
        return np.linalg.norm(to_pos - from_pos)

    def render(self, graphics: GraphicsContext, color: str = Colors.TRACKS):
        from_pos = self.edge.map.grid_to_pos(self.edge.from_point)
        to_pos = self.edge.map.grid_to_pos(self.edge.to_point)
        self.edge.from_point.render_rail_tick(graphics, color=color)
        self.edge.to_point.render_rail_tick(graphics, color=color)
        graphics.draw_line(color, from_pos, to_pos, width=3)
        if self.signal_type != SignalType.NONE:
            self.render_signal(graphics)

    def signal_pos_and_arm(self):
        edge = self.edge
        if self.signal_type == SignalType.FROM:
            edge = GridEdge(edge.to_point, edge.from_point)

        from_pos = edge.map.grid_to_pos(edge.from_point)
        to_pos = edge.map.grid_to_pos(edge.to_point)

        middle_point = (from_pos + to_pos) / 2
        tangent = (to_pos - from_pos)
        tangent = tangent / np.linalg.norm(tangent)
        normal = -rotate_90deg(tangent)

        # depending on whether this is a horizontal edge or not we place the signals in different positions
        dx, dy = edge.to_point.x - edge.from_point.x, edge.to_point.y - edge.from_point.y
        if dy == 0:
            # horizontal. normally render signal centered at mid-point of train,
            # but if there is a diagonal branching off at FROM point, then we shift it by the arm-length to not
            # collide with the branching track.
            shift_by_arm = False
            branch_edge = GridEdge(edge.to_point, GridPoint(edge.map, edge.to_point.x - dx, edge.to_point.y - dx))
            if branch_edge in edge.map.placed_rails:
                shift_by_arm = True
        elif (dx, dy) in {(-1, -1), (1, 1)}:
            # diagonal, going down and right.
            shift_by_arm = False
        elif (dx, dy) in {(1, -1), (-1, 1)}:
            # diagonal, going up and right.
            shift_by_arm = True
        else:
            assert False, edge

        signal_position = middle_point + normal * 10
        arm = tangent * 20
        if shift_by_arm:
            signal_position -= arm
        return signal_position, arm

    def render_signal(self, graphics: GraphicsContext):
        signal_pos, arm = self.signal_pos_and_arm()
        signal_color = {
            SignalState.RED: Colors.SIGNAL_RED,
            SignalState.GREEN: Colors.SIGNAL_GREEN,
        }[self.signal_state]

        with graphics.translate(signal_pos):
            # graphics.draw_line(signal_color, [0.0, 0.0], arm, width=2)
            # graphics.draw_circle(signal_color, [0.0, 0.0], radius=5)
            with graphics.scale_by(0.08):
                angle = math.atan2(-arm[1], -arm[0]) * 180 / math.pi + 90
                img = {
                    SignalState.RED: Assets.SIGNAL_RED,
                    SignalState.GREEN: Assets.SIGNAL_GREEN,
                }[self.signal_state]
                rot_img = pygame.transform.rotate(img, -angle)
                graphics.blit(rot_img, rot_img.get_rect(center=(0, 0)))

    def next_rail(self, dx: int) -> Rail | None:
        map = self.edge.map
        end_point = self.edge.to_point if self.edge.to_point.x - self.edge.from_point.x == dx else self.edge.from_point
        next_edges = end_point.get_out_edges(dx_only=dx)
        next_edges = [edge for edge in next_edges if edge in map.placed_rails]
        if len(next_edges) == 0:
            return None
        elif len(next_edges) == 1:
            return map.placed_rails[next_edges[0]]
        else:
            next_edges_by_dy = {
                edge.to_point.y - edge.from_point.y: edge
                for edge in next_edges
            }
            assert len(next_edges_by_dy) == len(next_edges)
            switch = map.switches[(end_point, dx)]
            return map.placed_rails[next_edges_by_dy[switch.dy]]

    def get_tangent(self, dx: int):
        edge = self.edge
        if edge.dx != dx:
            edge = edge.flipped()
        assert edge.dx == dx
        from_pos = edge.map.grid_to_pos(edge.from_point)
        to_pos = edge.map.grid_to_pos(edge.to_point)
        tangent = to_pos - from_pos
        tangent = tangent / np.linalg.norm(tangent)
        return tangent


@dataclass
class Switch(Entity):
    point: GridPoint
    dx: int
    dy: int

    def render(self, graphics: GraphicsContext):
        pos = self.point.map.grid_to_pos(self.point)
        neighbor = GridPoint(self.point.map, self.point.x + self.dx, self.point.y + self.dy)
        other_pos = self.point.map.grid_to_pos(neighbor)
        graphics.draw_line(Colors.SWITCH, pos, (pos + other_pos) / 2, width=2)

    def possible_dy_positions(self) -> list[int]:
        return [
            dy
            for dy in [-1, 0, 1]
            if GridEdge(self.point, GridPoint(self.point.map, self.point.x + self.dx, self.point.y + dy)) in self.point.map.placed_rails
        ]

TRAIN_STOP_DISTANCE = 45.0  # calibrated for acceleration 10, max speed 20

@dataclass(kw_only=True)
class Train(Entity):
    dx: int

    current_rail: Rail
    current_delta: float = 0.0
    max_speed: float = 20.0
    current_speed: float = 0.0
    acceleration: float = 10.0

    destination: "Destination"
    max_waiting_time = 6.0
    remaining_waiting_time = max_waiting_time
    crashed: bool = False

    def update(self, delta_time: float):
        next_rail = self.current_rail.next_rail(dx=self.dx)
        if next_rail is not None:
            if (self.current_rail.length - self.current_delta) <= TRAIN_STOP_DISTANCE:
                signal_direction = SignalType.FROM if next_rail.edge.dx == self.dx else SignalType.TO
                red_signal = next_rail.signal_type == signal_direction and next_rail.signal_state == SignalState.RED
            else:
                red_signal = False
        elif self.current_rail.is_destination:
            red_signal = False
        else:
            red_signal = True  # no next rail, should stop

        if self.remaining_waiting_time > 0 and red_signal and self.current_speed <= 0.01 and next_rail is not None:
            self.remaining_waiting_time -= delta_time
            if self.remaining_waiting_time <= 0:
                # will go now
                self.remaining_waiting_time = 0.0
                next_rail.signal_state = SignalState.GREEN

        target_speed = 0.0 if red_signal else self.max_speed
        self.current_speed = clamp(self.current_speed + np.sign(target_speed - self.current_speed) * self.acceleration * delta_time, 0.0, self.max_speed)

        self.current_delta += self.current_speed * delta_time
        while self.current_delta > self.current_rail.length:
            self.current_delta -= self.current_rail.length
            next_rail = self.current_rail.next_rail(dx=self.dx)
            if next_rail is not None:
                self.current_rail = next_rail
            else:
                # cannot go further
                self.current_delta = self.current_rail.length
                if self.current_rail.is_destination:
                    self.current_rail.edge.map.game_state.on_train_reach_destination(self)
                break

    def current_pos(self):
        edge = self.current_rail.edge
        if edge.dx != self.dx:
            edge = edge.flipped()
        assert edge.dx == self.dx
        edge_start_pos = edge.map.grid_to_pos(edge.from_point)
        edge_end_pos = edge.map.grid_to_pos(edge.to_point)
        pos = edge_start_pos + (edge_end_pos - edge_start_pos) * (self.current_delta / self.current_rail.length)
        return pos

    def render(self, graphics: GraphicsContext):
        pos = self.current_pos()
        # graphics.draw_circle(Colors.TRAIN, pos, 10)

        tangent = self.current_rail.get_tangent(dx=self.dx)

        # interpolate with next tangent
        turn_start_frac = 0.8
        next_segment = self.current_rail.next_rail(dx=self.dx)
        if next_segment is not None and self.current_delta >= self.current_rail.length * turn_start_frac:
            next_tangent = next_segment.get_tangent(dx=self.dx)
            dt = (self.current_delta / self.current_rail.length - turn_start_frac) / (1 - turn_start_frac)
            tangent = (1 - dt) * tangent + dt * next_tangent

        with graphics.translate(pos), graphics.scale_by(0.05):
            angle = math.atan2(-tangent[1], -tangent[0]) * 180 / math.pi + 180
            img = Assets.TRAIN
            if self.crashed:
                # make it red, and rotate it a bit
                angle += self.current_rail.edge.map.game_state.global_time * 500
                img = img.copy()
                img.fill(Colors.TRAIN_CRASHED, special_flags=pygame.BLEND_RGBA_MULT)
            rot_img = pygame.transform.rotate(img, -angle)
            graphics.blit(rot_img, rot_img.get_rect(center=(0, 0)))

    def maybe_render_popup(self, graphics: GraphicsContext):
        if self.current_rail.edge.map.game_state.game_over:
            return
        self.render_popup(graphics)

    def render_popup(self, graphics: GraphicsContext):
        popup_dx = 1 if self.current_rail.edge.from_point.x < self.current_rail.edge.map.GRID_WIDTH / 2 else -1
        popup_offset = np.array([popup_dx * 30, -70])
        popup_width = 50
        popup_height = 50
        box_offset = self.current_pos() + popup_offset

        points = np.asarray([
            [0, popup_height],
            [0, 0],
            [popup_width, 0],
            [popup_width, popup_height],
        ]) + box_offset[None, :]
        graphics.draw_polygon(Colors.POPUP_BACKGROUND, points)

        line_to = self.current_pos() + popup_offset + [0, popup_height]
        arrow_vector = line_to - self.current_pos()
        arrow_vector = arrow_vector / np.linalg.norm(arrow_vector)
        arrow_points = line_to - arrow_vector * 5, line_to - arrow_vector * 15

        lines = [arrow_points] + list(zip(points, list(points[1:]) + list(points[:1])))
        line_lengths = [np.linalg.norm(to_point - from_point) for from_point, to_point in lines]
        rel_line_lengths = np.asarray(line_lengths) / np.sum(line_lengths)

        waiting_frac = 1 - self.remaining_waiting_time / self.max_waiting_time
        drawn_frac = 0

        for (from_point, to_point), rel_line_length in zip(lines, rel_line_lengths):
            if waiting_frac <= drawn_frac:
                continue
            if waiting_frac <= drawn_frac + rel_line_length:
                # draw part of the line
                dt = (waiting_frac - drawn_frac) / rel_line_length
                to_point = from_point + dt * (to_point - from_point)
            drawn_frac += rel_line_length
            graphics.draw_line(Colors.POPUP_BORDER, from_point, to_point, width=3)

        # draw the destination icon
        dest_icon = self.destination.marker_icon
        with graphics.translate(box_offset + [popup_width / 2, popup_height / 2]), graphics.scale_by(0.12):
            graphics.blit(dest_icon, dest_icon.get_rect(center=(0, 0)))



class Map:
    """
    (0, 0) is somewhere.
    (1, 0) is one cell to the right
    (0, 1) is one cell down, where down is given by the down vector (pointing slightly down)
    """
    DIST = 100.0
    RIGHT = np.array([0.5 * DIST, 0.0])
    DOWN = np.array([0.0, 0.3 * DIST])
    GRID_WIDTH = 18
    GRID_HEIGHT = 12

    def __init__(self, game_state: "GameState"):
        self.game_state = game_state
        self.placed_rails: dict[GridEdge, Rail] = {}
        self.switches: dict[tuple[GridPoint, int], Switch] = {}  # (point, dx) -> switch
        self.trains: list[Train] = []
        self.simulation_speed = 1.0

    def grid_to_pos(self, point: GridPoint) -> np.ndarray:
        return point.x * self.RIGHT + point.y * self.DOWN

    def grid_to_pos_float(self, x, y) -> np.ndarray:
        return x * self.RIGHT + y * self.DOWN

    def pos_to_grid(self, pos: np.ndarray) -> np.ndarray:
        # solve the linear system pos = x * RIGHT + y * DOWN for x and y
        A = np.column_stack((self.RIGHT, self.DOWN))
        xy = np.linalg.solve(A, pos)
        return xy

    def update(self, delta_time: float):
        for train in self.trains:
            train.update(delta_time * self.simulation_speed)

        # check for explosion
        rails_to_trains = {}
        for train in self.trains:
            if train.current_rail.edge not in rails_to_trains:
                rails_to_trains[train.current_rail.edge] = train
            else:
                # explosion
                other_train = rails_to_trains[train.current_rail.edge]
                self.game_state.on_train_collision(train, other_train)


    def render(self, graphics: GraphicsContext):
        graphics.draw_polygon(
            Colors.BACKGROUND_PLAYABLE, [
                self.grid_to_pos(GridPoint(self, 0, 0)),
                self.grid_to_pos(GridPoint(self, self.GRID_WIDTH - 1, 0)),
                self.grid_to_pos(GridPoint(self, self.GRID_WIDTH - 1, self.GRID_HEIGHT - 1)),
                self.grid_to_pos(GridPoint(self, 0, self.GRID_HEIGHT - 1)),
            ])
        for rail in self.placed_rails.values():
            rail.render(graphics)
        for switch in self.switches.values():
            switch.render(graphics)
        for train in self.trains:
            train.render(graphics)

    def render_ui(self, graphics: GraphicsContext):
        for train in self.trains:
            train.maybe_render_popup(graphics)

    def get_edges_between(self, from_point: GridPoint, to_point: GridPoint) -> list[GridEdge]:
        # greedy implementation
        if from_point == to_point:
            return []
        potential_edges = from_point.get_out_edges()
        distances = {
            edge: np.linalg.norm(self.grid_to_pos(edge.to_point) - self.grid_to_pos(to_point))
            for edge in potential_edges
        }
        best_edge = min(potential_edges, key=distances.get)
        next_edges = self.get_edges_between(best_edge.to_point, to_point)
        if len(next_edges) > 0:
            next_edge = next_edges[0]
            if next_edge.to_point.x == best_edge.from_point.x:
                # edge does zig-zag, that is not allowed
                return []
        return [best_edge] + next_edges

    def is_point_on_map(self, point: GridPoint):
        if 0 <= point.x < self.GRID_WIDTH and 0 <= point.y < self.GRID_HEIGHT:
            return True
        else:
            return False

    def place_rail(self, rail: Rail):
        self.placed_rails[rail.edge] = rail
        # check junctions
        for rail in self.placed_rails.values():
            self.update_switches(rail)
        # debug
        for rail in self.placed_rails.values():
            rail.next_rail(dx=-1)
            rail.next_rail(dx=1)


    def update_switches(self, rail: Rail):
        dx = rail.edge.to_point.x - rail.edge.from_point.x
        dy = rail.edge.to_point.y - rail.edge.from_point.y
        assert dx == -1 or dx == 1
        point_left_edges = [edge for edge in rail.edge.from_point.get_out_edges(dx_only=dx) if edge in self.placed_rails]
        point_right_edges = [edge for edge in rail.edge.to_point.get_out_edges(dx_only=-dx) if edge in self.placed_rails]
        if len(point_left_edges) >= 2 and (rail.edge.from_point, dx) not in self.switches:
            self.switches[(rail.edge.from_point, dx)] = Switch(rail.edge.from_point, dx, dy)
        if len(point_right_edges) >= 2 and (rail.edge.to_point, -dx) not in self.switches:
            self.switches[(rail.edge.to_point, -dx)] = Switch(rail.edge.to_point, -dx, -dy)
