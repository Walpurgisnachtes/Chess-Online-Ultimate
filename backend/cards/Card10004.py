from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Union, Callable, Any, Optional
from card_related.card_driver import Card, Deck
from card_related.system_driver import System
from card_related.static_card_base import StaticCardBase, StaticSystemBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from player_related.player import Player
from controller import GameController


from controller_related.event_controller import EventHandler

class Card10004:
    """
    Card ID: 10004
    Description: "If a friendly piece is the only one in its column, *change* it into a knight."
    """

    def __init__(self, controller: GameController):
        self.controller = controller

    def exec(self):
        print("[Card 10004] Execution started: If a friendly piece is the only one in its column, *change* it into a knight.")

        # Define the selection predicate
        predicate = {
            "type": "piece",
            "filter": {
                "color": "friendly",
                "custom": ["only_of_column"]
            },
            "min": 1,
            "max": 1,
            "required": True                # If no valid targets, card cannot be played (optional)
        }

        # Request selection from player
        selected = self.controller.select(predicate)

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if not selected:
            print("[Card 10004] No valid target selected → effect fizzles")
            return

        piece_pos_square = selected[0]
        target_piece = self.controller.board.get_piece_at_square(piece_pos_square)

        if not target_piece:
            print("[Card 10004] Selected piece no longer exists → effect fizzles")
            return

        print(f"[Card 10004] Change {target_piece.name} at {piece_pos_square} to Knight")

        self.controller.change_piece(KnightPiece, selected)

        print("[Card 10004] Effect resolved successfully")