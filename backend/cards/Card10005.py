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

class Card10005:
    """
    Card ID: 10005
    Description: "Each of your knights may move once this turn.\nWhenever one of your knights captures an enemy piece, gain 1 prestige."
    """

    def __init__(self, controller: GameController):
        self.controller = controller
        self.search_result: List[KnightPiece] = []

    def exec(self):
        print("[Card 10005] Execution started: Each of your knights may move once this turn.\nWhenever one of your knights captures an enemy piece, gain 1 prestige.")

        if "10005" in self.controller.once_per_turn_tags["card_tags"]:
            return
        
        self.controller.once_per_turn_tags["card_tags"].append("10005")

        board = self.controller.board
        friendly_color = self.controller.resolve_player_colors("friendly")
        
        self.search_result = []
        
        for rows in board.board:
            for piece in rows:
                if piece:
                    if isinstance(piece, KnightPiece)\
                        and piece.color in friendly_color\
                            and not piece.has_status("moved"):
                        self.search_result.append(piece)
                

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if len(self.search_result) == 0:
            print("[Card 10005] No valid target selected → effect fizzles")
            return

        for piece in self.search_result:
            self.controller.add_piece_status(piece, StatusEffect("card_given_movable"))
        
        self.controller.card_event_handler.on("success_move_made", self.gain_prestige)
        self.controller.card_event_handler.on("turn_end", self.remove_listener, once=True, capture=True)

        print("[Card 10005] Effect resolved successfully")
        
    def gain_prestige(self, data):
        moving = data["moving_piece"]
        capture = data["capture"]
        
        if isinstance(moving, KnightPiece):
            if capture and not isinstance(capture, NonePiece):
                self.controller.gain_prestige("friendly", 1)
        
    def remove_listener(self, data):
        self.controller.card_event_handler.remove("success_move_made", self.gain_prestige)
