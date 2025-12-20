from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Union, Callable, Any, Optional
from card_related.card_driver import Card, Deck
from card_related.system_driver import System
from card_related.static_card_base import StaticCardBase, StaticSystemBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *
from chess_related.status_effect import StatusEffect

from player_related.player import Player
from controller import GameController

from controller_related.event_controller import EventHandler

from misc.enums import StatusCountdownMethod, PieceName

class Card10006:
    """
    Card ID: 10006
    Description: "Target 1 enemy piece. *Remove* it if it is targeted by "Crossbowmen" again."
    """

    def __init__(self, controller: GameController):
        self.controller = controller

    def exec(self):
        print("[Card 10006] Execution started: Target 1 enemy piece. *Remove* it if it is targeted by \"Crossbowmen\" again.")

        # Define the selection predicate
        predicate = {
            "type": "piece",
            "filter": {
                "color": "enemy"
            },
            "min": 1,
            "max": 1,
            "required": True                # If no valid targets, card cannot be played (optional)
        }

        # Request selection from player
        selected = self.controller.select(predicate)

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if not selected:
            print("[Card 10006] No valid target selected → effect fizzles")
            return

        piece_pos_square = selected[0]
        target_piece = self.controller.board.get_piece_at_square(piece_pos_square)

        if not target_piece:
            print("[Card 10006] Selected piece no longer exists → effect fizzles")
            return

        # Execute removal
        if target_piece.has_status("targeted_10006"):
            print(f"[Card 10006] Removing {target_piece.name} at {piece_pos_square}")
            self.controller.remove_piece(selected)
        else:
            print(f"[Card 10006] Targeting {target_piece.name} at {piece_pos_square}")
            self.controller.add_piece_status(target_piece, StatusEffect("targeted_10006", countdown_method=StatusCountdownMethod.INFINITE))

        print("[Card 10006] Effect resolved successfully")