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

class Card20002:
    """
    Card ID: 20002
    Description: "Your king will not be captured in 3 turns."
    """

    def __init__(self, controller: GameController):
        self.controller = controller

    def exec(self):
        print("[Card 20002] Execution started: Your king will not be captured in 3 turns.")

        board = self.controller.board
        friendly_color = self.controller.resolve_player_colors("friendly")
        
        self.search_result = []
        
        for rows in board.board:
            for piece in rows:
                if piece:
                    if isinstance(piece, KingPiece)\
                        and piece.color in friendly_color:
                        self.search_result.append(piece)
                

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if len(self.search_result) == 0:
            print("[Card 20002] No valid target selected → effect fizzles")
            return

        for piece in self.search_result:
            self.controller.add_piece_status(piece, StatusEffect("uncapturable", duration=3))

        print("[Card 20002] Effect resolved successfully")