from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from chess import Board


class Colour(Enum):
    BLACK = (0, "black")
    WHITE = (1, "white")


class Castles(Enum):
    KINGSIDE = "K"
    QUEENSIDE = "Q"


class Outcome(Enum):
    TIMEOUT = 11
    RESIGNATION = 12
    AGREEMENT = 13


@dataclass
class Game:
    players: List[str]  # [0] white, [1] black
    board: Board | str  # pychess board object or string when serialised
    tr_w: int  # time remaining for white
    tr_b: int  # time remaining for black
    turn_start_time: float  # timestamp when the turn started
    time_control: int  # time control (minutes)


@dataclass
class Event:
    name: str
    data: Optional[int | str | Dict[str, Optional[int]]]
