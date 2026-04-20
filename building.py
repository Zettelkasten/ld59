import abc
from typing import TYPE_CHECKING

from colors import Colors
from graphics import GraphicsContext
from map import Rail, GridPoint, SignalType, SignalState, Switch

if TYPE_CHECKING:
    from game import GameState


class BuildingMode(abc.ABC):
    @abc.abstractmethod
    def render(self, graphics: GraphicsContext):
        raise NotImplementedError()

    @abc.abstractmethod
    def on_click(self):
        raise NotImplementedError()


class BuildRails(BuildingMode):
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state

        self.placement_start_point: GridPoint | None = None

    def render(self, graphics: GraphicsContext):
        map = self.game_state.map
        point_at_mouse = self.game_state.get_grid_point_at_mouse()
        if map.is_point_on_map(point_at_mouse):
            graphics.draw_circle(Colors.BUILDING_SELECTED_POINT, map.grid_to_pos(point_at_mouse), radius=5)
            if self.placement_start_point is not None:
                from_point = self.placement_start_point
                to_point = point_at_mouse
                if map.is_point_on_map(to_point):
                    graphics.draw_circle(Colors.BUILDING_TRACK, map.grid_to_pos(from_point), radius=5)
                    graphics.draw_circle(Colors.BUILDING_TRACK, map.grid_to_pos(to_point), radius=5)
                    edges = map.get_edges_between(from_point, to_point)
                    for edge in edges:
                        if edge not in map.placed_rails:
                            Rail(edge).render(graphics, color=Colors.BUILDING_TRACK)

    def on_click(self):
        map = self.game_state.map

        if self.placement_start_point is None:
            from_point = self.game_state.get_grid_point_at_mouse()
            if map.is_point_on_map(from_point):
                self.placement_start_point = from_point
        else:
            from_point = self.placement_start_point
            to_point = self.game_state.get_grid_point_at_mouse()
            if map.is_point_on_map(to_point):
                edges = map.get_edges_between(from_point, to_point)
                last_edge_already_exists = len(edges) > 0 and edges[-1] in map.placed_rails
                if len(edges) > 0 and not last_edge_already_exists:
                    last_point = edges[-1].to_point
                    if not any(last_point in {edge.from_point, edge.to_point} for edge in map.placed_rails):
                        self.placement_start_point = last_point
                    else:
                        self.placement_start_point = None
                else:
                    self.placement_start_point = None
                for edge in edges:
                    if edge not in map.placed_rails:
                        map.place_rail(Rail(edge))


class BuildSignals(BuildingMode):
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state

    def render(self, graphics: GraphicsContext):
        rail = self.game_state.get_grid_rail_at_mouse()
        if rail is not None:
            rail.render(graphics, color=Colors.BUILDING_SIGNAL)

    def on_click(self):
        rail = self.game_state.get_grid_rail_at_mouse()
        if rail is not None:
            if rail.signal_type == SignalType.NONE:
                rail.signal_type = SignalType.FROM
            elif rail.signal_type == SignalType.FROM:
                rail.signal_type = SignalType.TO
            elif rail.signal_type == SignalType.TO:
                rail.signal_type = SignalType.NONE


class SwitchSignalsAndSwitches(BuildingMode):
    def __init__(self, game_state: "GameState"):
        self.game_state = game_state

    def render(self, graphics: GraphicsContext):
        signal_or_switch = self.game_state.get_signal_or_switch_at_mouse()
        if isinstance(signal_or_switch, Rail):
            signal_or_switch.render(graphics, color="green")
        elif isinstance(signal_or_switch, Switch):
            switch = signal_or_switch
            switch_pos = self.game_state.map.grid_to_pos(switch.point)
            graphics.draw_circle("green", switch_pos, radius=5)
        else:
            assert signal_or_switch is None

    def on_click(self):
        signal_or_switch = self.game_state.get_signal_or_switch_at_mouse()
        if isinstance(signal_or_switch, Rail):
            rail = signal_or_switch
            rail.signal_state = SignalState.GREEN if rail.signal_state == SignalState.RED else SignalState.RED
        elif isinstance(signal_or_switch, Switch):
            switch = signal_or_switch
            possible_dys = switch.possible_dy_positions()
            switch.dy = possible_dys[(possible_dys.index(switch.dy) + 1) % len(possible_dys)]