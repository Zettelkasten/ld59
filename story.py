from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from building import BuildRails, BuildSignals, SwitchSignalsAndSwitches
from map import SignalType, SignalState
from quests import OffMapDestination

if TYPE_CHECKING:
    from game import GameState


@dataclass
class StoryMessage:
    lines: list[str]
    is_blocking: bool = True
    wait_for: typing.Callable[["GameState"], bool] | None = None
    complete_with: typing.Callable[["GameState"], bool] | None = None
    can_skip_tutorial: bool = False


def is_connected(source: OffMapDestination, game_state):
    rail = source.in_rails[0]
    while rail.next_rail(source.dx) is not None:
        rail = rail.next_rail(source.dx)
        for destination in game_state.quests.active_destinations:
            if isinstance(destination, OffMapDestination) and rail in destination.out_rails:
                return True
    return False

def all_stations_connected(game_state: GameState):
    return all(is_connected(source, game_state) for source in game_state.quests.active_sources)


class StoryAssets:
    INTRO = [
        StoryMessage(lines=["oh, hello there!", "you must be the new guy!"], can_skip_tutorial=True),
        StoryMessage(lines=["welcome to the railway station! i'm the station master,", "and i'll get you up to speed on how things are run here."]),
        StoryMessage(lines=["your job is to ensure all trains are going to their destination."]),
        StoryMessage(
            lines=["did you notice that train on the left?", "it's scheduled to go to the station on the right."],
            wait_for=lambda game_state: len(game_state.map.trains) > 0 and game_state.map.trains[0].remaining_waiting_time == 0.0,
        ),
        StoryMessage(
            lines=["for it to pass, you will have to lay the track there.", "click on the track building icon on the bottom."],
            complete_with=lambda game_state: isinstance(game_state.building_mode, BuildRails),
        ),
        StoryMessage(
            lines=["now connect the two stations with each other", "by clicking on the ground."],
            complete_with=all_stations_connected,
        ),
        StoryMessage(
            lines=["perfect!", "watch the trains go!"],
        ),
        StoryMessage(
            lines=["congratulations.", "you delivered your first train!"],
            wait_for=lambda game_state: game_state.score_correct_trains >= 1,
        ),
        StoryMessage(
            lines=["trains will come automatically.", "there's no way to stop it!"],
        ),
        StoryMessage(
            lines=["just make sure they do not crash!", "that would be disaster."],
        ),
        StoryMessage(
            lines=["as you deliver more trains to their correct destination,", "more stations will open up."],
            wait_for=lambda game_state: game_state.score_correct_trains >= game_state.quests.stage_min_scores[2],
            can_skip_tutorial=True,
        ),
        StoryMessage(
            lines=["if something ever goes wrong,", "do not feel ashamed to use the bulldozer."],
        ),
        StoryMessage(
            lines=["now, trains also want to go into the opposite direction.", "go build the parallel tracks!"],
            complete_with=all_stations_connected,
        ),
        StoryMessage(
            lines=["well done."],
            wait_for=lambda game_state: game_state.score_correct_trains >= game_state.quests.stage_min_scores[2] + 1,
        ),
        StoryMessage(
            lines=["with increasing complexity,", "you will have to add signals to your network."],
        ),
        StoryMessage(
            lines=["try to build a signal now", "by switching into signal building-model."],
            complete_with=lambda game_state: isinstance(game_state.building_mode, BuildSignals),
        ),
        StoryMessage(
            lines=["place a signal on one of your tracks.", "you can change it's direction by clicking twice."],
            complete_with=lambda game_state: any(game_state.map.is_point_on_map(r.edge.from_point) and game_state.map.is_point_on_map(r.edge.to_point) and r.signal_type != SignalType.NONE for r in game_state.map.placed_rails.values()),
        ),
        StoryMessage(
            lines=["now enter 'interaction mode' by clicking on the pointer icon", "on the left to switch the signal to green."],
            complete_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches),
        ),
        StoryMessage(
            lines=["click on the signal to switch", "between red and green."],
            complete_with=lambda game_state: any(game_state.map.is_point_on_map(r.edge.from_point) and game_state.map.is_point_on_map(r.edge.to_point) and r.signal_type != SignalType.NONE and r.signal_state == SignalState.GREEN for r in game_state.map.placed_rails.values()),
        ),
        StoryMessage(
            lines=["well done!"],
        ),
        StoryMessage(
            lines=["another station just opened up.", "extend your service as needed."],
            wait_for=lambda game_state: game_state.score_correct_trains >= game_state.quests.stage_min_scores[3],
        ),
        StoryMessage(
            lines=["with train tracks intersecting, you will need", "to toggle the switches correctly."],
            wait_for=lambda game_state: len(game_state.map.switches) >= 1,
        ),
        StoryMessage(
            lines=["to switch tracks, enter 'interaction mode'", "and click on the purple lines on the intersection."],
            complete_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches),
        ),
        StoryMessage(
            lines=["to switch tracks, enter 'interaction mode'", "and click on the purple lines on the intersection."],
            complete_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches) and game_state.building_mode.num_switches_clicked >= 1,
        ),
        StoryMessage(
            lines=["perfect!", "now you know everything to master this job."],
        ),
        StoryMessage(
            lines=["good luck on your journey as a station master!"],
        ),
    ]
