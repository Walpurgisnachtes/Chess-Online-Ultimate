from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Union, Callable, Any, Optional
if TYPE_CHECKING:
    from card_related.card_driver import Card, Deck
    from card_related.system_driver import System
    from card_related.static_card_base import StaticCardBase, StaticSystemBase

    from chess_related.board import Board
    from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
    from chess_related.chess_utils import *

    from player_related.player import Player
    from controller import GameController


from controller_related.event_controller import EventHandler

class Card10001:
    """
    Card ID: 10001
    Description: "Select and *Remove* 1 enemy pawn or *minor piece*."
    Effect: Permanently remove the selected piece from the board (no graveyard).
    """

    def __init__(self, controller: GameController):
        self.controller = controller

    def exec(self):
        print("[Card 10001] Execution started: Select and remove 1 enemy pawn or minor piece")

        # Define the selection predicate
        predicate = {
            "type": "piece",
            "filter": {
                "color": "enemy",           # Enemy relative to current player
                "piece_type": ["PawnPiece", "KnightPiece", "BishopPiece"]
            },
            "min": 1,
            "max": 1,
            "required": True                # If no valid targets, card cannot be played (optional)
        }

        # Request selection from player
        selected = self.controller.select(predicate)

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if not selected or "piece" not in selected:
            print("[Card 10001] No valid target selected → effect fizzles")
            return

        piece_pos_square = selected["piece"]
        target_piece = self.controller.board.get_piece_at_square(piece_pos_square)

        if not target_piece:
            print("[Card 10001] Selected piece no longer exists → effect fizzles")
            return

        # Validate again (in case board changed during selection delay)
        if target_piece.color == self.controller.current_player:
            print("[Card 10001] Selected own piece → invalid")
            return

        if not isinstance(target_piece, (PawnPiece, KnightPiece, BishopPiece)):
            print("[Card 10001] Selected piece is not pawn/knight/bishop → invalid")
            return

        # Execute removal
        print(f"[Card 10001] Removing enemy {target_piece.name} at {piece_pos_square}")

        # Permanently remove from board (no graveyard)
        self.controller.remove_piece(piece_pos_square)

        print("[Card 10001] Effect resolved successfully")