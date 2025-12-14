from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import List, Dict, Union, Callable, Any, Optional
from types import SimpleNamespace
import logging
import time
from threading import Event

from card_related.card_driver import Card, Deck
from card_related.system_driver import System
from card_related.static_card_base import StaticCardBase, StaticSystemBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from controller_related.event_controller import EventHandler

from player_related.player import Player

class GameController:
    
    def __init__(
            self, 
            room: str,
            board: Board, 
            players: Dict[str, Player],
            event_handler: EventHandler
        ):
        self.room = room
        self.PLAYER_COLOR_WHITE = "white"
        self.PLAYER_COLOR_BLACK = "black"

        self.board = board
        self.players = players
        self.event_handler = event_handler
        self.current_player = self.PLAYER_COLOR_WHITE
        
        card_base = StaticCardBase.instance()
        self.all_card_ids = [card.id for card in card_base.all_cards()]
        self.card_classes = {
            cid: getattr(import_module(f"cards.{cid}"), f"Card{cid}") 
            for cid in self.all_card_ids 
            if Path(f"cards/{cid}.py").exists()
        }
        
        system_base = StaticSystemBase.instance()
        self.all_system_ids = [system.id for system in system_base.all_cards()]
        self.system_classes = {
            sid: getattr(import_module(f"systems.{sid}"), f"System{sid}") 
            for sid in self.all_system_ids 
            if Path(f"systems/{sid}.py").exists()
        }

        # For blocking selection (synchronous-like wait)
        self._pending_selection = None  # Will hold future-like object
        self._selection_result = None

    def select(self, predicate: dict, timeout: float = 60.0) -> Optional[dict]:
        self._pending_selection = Event()
        self._selection_result = None

        self.event_handler.dispatch_event("select", data={
            "room": self.room,
            "predicate": predicate,
            "current_player": self.current_player
        })

        # Wait with timeout
        resolved = self._pending_selection.wait(timeout=timeout)

        if not resolved:
            print(f"Selection timed out for room {self.room}")
            return None  # Card effect fizzles

        return self._selection_result

    def resolve_selection(self, selected_data: dict):
        self._selection_result = selected_data
        if self._pending_selection:
            self._pending_selection.set()

    # Optional: timeout or cancel
    def cancel_selection(self):
        self._selection_result = None
        if self._pending_selection:
            self._pending_selection.resolved = True
    
    def game_start(self):
        for player in self.players.values():
            self.event_handler.dispatch_event("game_start")
            self.event_handler.dispatch_event("game_start_draw")
            drawn_cards = player.deck.draw_5()
            player.hand = drawn_cards
            
    def remove_piece(self, piece_pos_square):
        self.board.remove_piece(piece_pos_square)
        self.event_handler.dispatch_event(
            event_name="remove_piece", 
            data={
                "room": self.room,
                "position": piece_pos_square
            })