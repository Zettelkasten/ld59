from __future__ import annotations

import typing
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from building import BuildRails, BuildSignals, SwitchSignalsAndSwitches
from map import SignalType, SignalState
from tutorial_highlights import TutorialHighlightTrain, TutorialHighlightDestination, TutorialHighlightUI, \
    TutorialHighlightPhantomTrack, TutorialHighlight, TutorialHighlightSignals, TutorialHighlightSwitches

if TYPE_CHECKING:
    from quests import OffMapDestination
    from game import GameState


@dataclass
class StoryMessage:
    lines: list[str]
    is_blocking: bool = True
    wait_for: typing.Callable[["GameState"], bool] | None = None
    auto_continue_with: typing.Callable[["GameState"], bool] | None = None
    can_skip_tutorial: bool = True   # now always skippable
    hides_ui: bool = False
    highlights: list[TutorialHighlight] = field(default_factory=list)


def first_train_came(game_state: GameState, set_waiting_to_zero: bool = False):
    if not (len(game_state.map.trains) > 0 and (game_state.map.trains[0].current_speed <= 0.01 or game_state.map.trains[0].remaining_waiting_time == 0.0)):
        return False
    train = game_state.map.trains[0]
    train.popup_fadeout_time = train.max_popup_fadeout_time  # make sure popup doesn't die
    if set_waiting_to_zero:
        train.remaining_waiting_time = 0.001  # not quite zero, because we need to trigger the starting squence lol.
    return True

def is_routed_correctly(source: OffMapDestination, destination: OffMapDestination):
    rail = source.in_rails[0]
    while rail.next_rail(source.dx) is not None:
        rail = rail.next_rail(source.dx)
        if rail in destination.out_rails:
            return True
    return False

def all_stations_routed_correctly(game_state: GameState):
    from quests import OffMapDestination
    return all(
        is_routed_correctly(source, destination)
        for source in game_state.quests.active_sources
        for destination in game_state.quests.active_destinations
        if isinstance(destination, OffMapDestination)
        and source.dx != destination.dx
    )

def is_source_connected_somehow(source: OffMapDestination, game_state: GameState):
    from quests import OffMapDestination
    rail = source.in_rails[0]
    while rail.next_rail(source.dx) is not None:
        rail = rail.next_rail(source.dx)
        for destination in game_state.quests.active_destinations:
            if isinstance(destination, OffMapDestination) and rail in destination.out_rails:
                return True
    return False

def is_destination_connected_somehow(destination: OffMapDestination, game_state: GameState):
    rail = destination.out_rails[0]
    while rail.next_rail(destination.dx) is not None:
        rail = rail.next_rail(destination.dx)
        for source in game_state.quests.active_sources:
            if rail in source.in_rails:
                return True
    return False


def all_stations_connected_somehow(game_state: GameState):
    from quests import OffMapDestination
    return all(is_source_connected_somehow(source, game_state)
        for source in game_state.quests.active_sources) and all(is_destination_connected_somehow(destination, game_state)
        for destination in game_state.quests.active_destinations
        if isinstance(destination, OffMapDestination)
    )

def wait_for_parallel_train(game_state: GameState):
    if game_state.score_correct_trains < game_state.quests.stage_min_scores[2]:
        return False
    for train in game_state.map.trains:
        if train.dx == -1 and train.remaining_waiting_time == 0.0:
            # good
            train.popup_fadeout_time = train.max_popup_fadeout_time  # keep the popup visible for longer
            for other_train in game_state.map.trains:
                if other_train != train:
                    if other_train.remaining_waiting_time > 0.0:
                        other_train.popup_fadeout_time = 0.0  # make the other popup disappear
            return True
    return False



class StoryAssets:
    INTRO = [
        StoryMessage(lines=["oh, hello there!", "you must be the new guy!"], can_skip_tutorial=True, hides_ui=True),
        StoryMessage(lines=["welcome to the railway station! i'm the station master,", "and i'll get you up to speed on how things are run here."], hides_ui=True),
        StoryMessage(lines=["your job is to ensure all trains are going to their destination."], hides_ui=True),
        StoryMessage(
            lines=["look!", "a train is coming."], hides_ui=True,
            auto_continue_with=first_train_came,
            is_blocking=False,
        ),
        StoryMessage(
            lines=["the marker shows its desired destination!", "it's scheduled to go to the station on the right."],
            wait_for=lambda game_state: first_train_came(game_state, set_waiting_to_zero=True),
            highlights=[TutorialHighlightTrain(i=0), TutorialHighlightDestination(name="B")],
            is_blocking=True,
        ),
        StoryMessage(
            lines=["you will have to lay the track to go to the right.", "click on the track building icon on the bottom."],
            auto_continue_with=lambda game_state: isinstance(game_state.building_mode, BuildRails),
            highlights=[TutorialHighlightUI(ui_index=1)],
            is_blocking=True,
        ),
        StoryMessage(
            lines=["connect the two stations with each other", "by clicking on the ground."],
            auto_continue_with=all_stations_routed_correctly,
            highlights=[
                TutorialHighlightPhantomTrack(from_x=0, from_y=8, to_x=1, to_y=8),
                TutorialHighlightPhantomTrack(from_x=1, from_y=8, to_x=2, to_y=8),
            ],
            is_blocking=True,  # otherwise the trains may accumulate and crash
        ),
        StoryMessage(
            lines=["perfect!", "watch the trains go!"], is_blocking=False,
            auto_continue_with=lambda game_state: len(game_state.map.trains) > 0 and game_state.map.trains[0].current_rail.edge.from_point.x >= 1,
        ),
        StoryMessage(
            lines=["feel free to increase the game speed", "if this is too slow for you (hot key: 5)."], is_blocking=False,
            auto_continue_with=lambda game_state: game_state.score_correct_trains >= 1,
            highlights=[TutorialHighlightUI(ui_index=4)],
        ),
        StoryMessage(
            lines=["congratulations.", "you successfully routed your first train!"],
            wait_for=lambda game_state: game_state.score_correct_trains >= 1,
        ),
        StoryMessage(
            lines=["trains will arrive automatically.", "there's no way to stop it!"],
        ),
        StoryMessage(
            lines=["just make sure they do not crash!", "that would be disaster."],
        ),
        StoryMessage(
            lines=["as you deliver more trains to their correct destination,", "more stations will open up."],
            wait_for=wait_for_parallel_train,
            highlights=[
                TutorialHighlightDestination(name="B"), TutorialHighlightDestination(name="E"),
            ],
        ),
        StoryMessage(
            lines=["if something ever goes wrong, do not feel", "ashamed to use the bulldozer (hot key: 4)."],
        ),
        StoryMessage(
            lines=["now, trains also want to go into the opposite direction.", "go connect the other lane to the right!"],
            auto_continue_with=lambda game_state: wait_for_parallel_train(game_state) and all_stations_routed_correctly(game_state),
            highlights=[
                TutorialHighlightDestination(name="B"), TutorialHighlightDestination(name="E"),
                TutorialHighlightPhantomTrack(from_x=0 + 15, from_y=7 - 3, to_x=1 + 15, to_y=7 - 3),
                TutorialHighlightPhantomTrack(from_x=1 + 15, from_y=7 - 3, to_x=2 + 15, to_y=7 - 3),
            ],
        ),
        StoryMessage(
            lines=["well done."],
            is_blocking=False,
            wait_for=lambda game_state: game_state.score_correct_trains >= game_state.quests.stage_min_scores[2] + 1,
        ),
        StoryMessage(
            lines=["with increasing complexity,", "you will have to add signals to your network."],
            is_blocking=False,
        ),
        StoryMessage(
            lines=["try to build a signal now by switching", "into 'signal building' mode (hot key: 2)."],
            auto_continue_with=lambda game_state: isinstance(game_state.building_mode, BuildSignals),
            highlights=[TutorialHighlightUI(ui_index=2)],
        ),
        StoryMessage(
            lines=["place a signal on one of your tracks.", "you can change its direction by clicking twice."],
            auto_continue_with=lambda game_state: any(game_state.map.is_point_on_map(r.edge.from_point) and game_state.map.is_point_on_map(r.edge.to_point) and r.signal_type != SignalType.NONE for r in game_state.map.placed_rails.values()),
        ),
        StoryMessage(
            lines=["now enter 'interaction mode' by clicking on the cursor icon", "on the left to switch the signal to green (hot key: 1)."],
            auto_continue_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches),
            highlights=[TutorialHighlightUI(ui_index=0)],
        ),
        StoryMessage(
            lines=["click on the signal to switch", "between red and green."],
            auto_continue_with=lambda game_state: any(game_state.map.is_point_on_map(r.edge.from_point) and game_state.map.is_point_on_map(r.edge.to_point) and r.signal_type != SignalType.NONE and r.signal_state == SignalState.GREEN for r in game_state.map.placed_rails.values()),
            highlights=[TutorialHighlightSignals()],
        ),
        StoryMessage(
            lines=["well done!", "good luck on your journey as a station master!"],
            is_blocking=False,
        ),
    ]

    SWITCH_PLACED = [
        StoryMessage(
            lines=["with train tracks intersecting, you will need", "to toggle the switches correctly."],
            wait_for=lambda game_state: len(game_state.map.switches) >= 1,
        ),
        StoryMessage(
            lines=["to switch tracks, enter 'interaction mode' (hot key: 1)", "and click on the purple lines on the intersection."],
            auto_continue_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches),
            highlights=[TutorialHighlightUI(ui_index=0)],
        ),
        StoryMessage(
            lines=["to switch tracks, enter 'interaction mode' (hot key: 1)", "and click on the purple lines on the intersection."],
            auto_continue_with=lambda game_state: isinstance(game_state.building_mode, SwitchSignalsAndSwitches) and game_state.building_mode.num_switches_clicked >= 1,
            highlights=[TutorialHighlightSwitches()],
        ),
        StoryMessage(
            lines=["perfect!"],
        ),
    ]
