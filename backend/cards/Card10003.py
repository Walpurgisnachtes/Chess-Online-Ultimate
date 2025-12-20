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

class Card10003:
    """
    Card ID: 10003
    Description: "This turn, your knights can move like rook, but you cannot captures the enemy king."
    """

    def __init__(self, controller: GameController):
        self.controller = controller
        self.search_result: List[KnightPiece] = []
        self.enemy_king: KingPiece = None

    def exec(self):
        print("[Card 10003] Execution started: This turn, your knights can move like rook, but you cannot captures the enemy king.")

        board = self.controller.board
        friendly_color = self.controller.resolve_player_colors("friendly")
        enemy_color = self.controller.resolve_player_colors("enemy")
        
        self.search_result = []
        self.enemy_king = None
        
        for rows in board.board:
            for piece in rows:
                if piece:
                    if isinstance(piece, KnightPiece) and piece.color in friendly_color:
                        self.search_result.append(piece)
                    elif isinstance(piece, KingPiece) and piece.color in enemy_color:
                        self.enemy_king = piece
                

        # If no valid selection (timeout, cancel, no targets, or room closed)
        if len(self.search_result) == 0:
            print("[Card 10003] No valid target selected → effect fizzles")
            return

        for piece in self.search_result:
            piece.move_rule.append(PieceName.ROOK)
        if not self.enemy_king.has_status("uncapturable"):
            self.controller.add_piece_status(self.enemy_king, StatusEffect("uncapturable"))
        
        self.controller.card_event_handler.on("turn_end", self.reset_move_rule, once=True, capture=True)

        print("[Card 10003] Effect resolved successfully")
        
    def reset_move_rule(self, data):
        for knight_piece in self.search_result:
            if PieceName.ROOK in knight_piece.move_rule:
                knight_piece.move_rule.remove(PieceName.ROOK)