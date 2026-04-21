from abc import ABC
from dataclasses import dataclass


class TutorialHighlight(ABC):
    pass

@dataclass
class TutorialHighlightUI(TutorialHighlight):
    ui_index: int

@dataclass
class TutorialHighlightTrain(TutorialHighlight):
    i: int

@dataclass
class TutorialHighlightSignals(TutorialHighlight):
    pass

@dataclass
class TutorialHighlightSwitches(TutorialHighlight):
    pass

@dataclass
class TutorialHighlightDestination(TutorialHighlight):
    name: str

@dataclass
class TutorialHighlightPhantomTrack(TutorialHighlight):
    from_x: int
    from_y: int
    to_x: int
    to_y: int
