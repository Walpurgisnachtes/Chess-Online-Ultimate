from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Union, Callable, Any, Optional
if TYPE_CHECKING:
    from backend.card_related.card_driver import Card, Deck
    from backend.card_related.system_driver import System
    from backend.card_related.static_card_base import StaticCardBase, StaticSystemBase

    from backend.chess_related.board import Board
    from backend.chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
    from backend.chess_related.chess_utils import *

    from backend.player_related.player import Player
    from controller import GameController

from controller_related.event_controller import EventHandler

class Selector:
    
    def __init__(self, event_handler: EventHandler):
        self.event_handler = event_handler
    
    def select(self, predicate: Callable[[str], bool]):
        self.event_handler