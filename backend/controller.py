from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import List, Dict, Union, Callable, Any, Optional
from types import SimpleNamespace
from uuid import UUID
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
        self.SUPPORTED_CARD_AREA = ["deck", "hand", "graveyard"]

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
        
    def search(self, predicate: dict) -> Dict[str, Union[str, List[str]]]:
        if predicate.get("type") == "piece":
            return {
                "type": "piece",
                "result": self.search_board(predicate)
            }
        elif predicate.get("type") == "card":
            return {
                "type": "card",
                "result": self.search_card(predicate)
            }
        else:
            return {
                "type": "none",
                "result": []
            }

    def search_card(self, predicate: Dict[str, Any]) -> List[str]:
        if predicate.get("type") != "card":
            raise ValueError("search_card only handles predicates of type 'card'.")

        filters: Dict[str, Union[str, List[str]]] = predicate.get("filter", {})

        # --- resolve which players to inspect -------------------------------------
        player_filter = filters.get("player")
        target_players: List[Player] = []
        enemy_player = self.PLAYER_COLOR_BLACK if self.current_player == self.PLAYER_COLOR_WHITE else self.PLAYER_COLOR_WHITE

        if player_filter in (None, "any"):
            target_players = list(self.players.values())
            target_players
        elif player_filter in {"friendly"}:
            target_players = self.players[self.current_player]
        elif player_filter in {"enemy"}:
            target_players = self.players[enemy_player]
        else:
            target_players = None

        if not target_players:
            return []

        # --- resolve card areas ----------------------------------------------------
        area_filter = filters.get("area", ["hand"])
        area_names = [area for area in area_filter if area in self.SUPPORTED_CARD_AREA]

        # --- optional filters on card type / status --------------------------------
        type_filter_values = filters.get("type")
        type_filter = {t.lower() for t in type_filter_values} if type_filter_values else None

        status_filter_values = filters.get("status")
        status_filter = {s.lower() for s in status_filter_values} if status_filter_values else None

        # --- perform the search ----------------------------------------------------
        matches: List[str] = []

        for player in target_players:

            for area in area_names:
                attr_name = self.SUPPORTED_CARD_AREA[area]
                card_container: Union[Deck, List[Card]] = getattr(player, attr_name, None)

                if card_container is None:
                    continue
                
                if isinstance(card_container, Deck):
                    for card in card_container.deck_cards:
                        if type_filter and card.type.lower() not in type_filter:
                            continue

                        if status_filter:
                            card_status = {s.lower() for s in card.status}
                            if not status_filter.issubset(card_status):
                                continue

                        # Produce a stable string identifier for the match
                        matches.append(card.id)
                        
                elif isinstance(card_container, list):
                    for card in card_container:
                        if type_filter and card.type.lower() not in type_filter:
                            continue

                        if status_filter:
                            card_status = {s.lower() for s in card.status}
                            if not status_filter.issubset(card_status):
                                continue

                        # Produce a stable string identifier for the match
                        matches.append(card.id)

        # --- enforce min/max/required constraints ----------------------------------
        min_required = predicate.get("min")
        required = predicate.get("required", False)

        if min_required is not None and min_required > 0 and len(matches) == 0:
            if required:
                raise ValueError(
                    f"Card predicate requires at least {min_required} matches."
                )

        return matches

    def search_board(self, predicate: Dict[str, Any]) -> List[str]:
        """
        Find all possible board squares that satisfy the provided predicate.
        Currently supports predicate type "piece" with filters on color
        and/or piece_type.
        """
        if predicate.get("type") != "piece":
            raise NotImplementedError("Only 'piece' predicates are supported.")
        
        chess_board = self.board.board

        filters: Dict[str, Union[str, List[str]]] = predicate.get("filter", {})
        color_filter = filters.get("color", "all")
        if isinstance(color_filter, str):
            if color_filter == "all":
                color_filter = ["friendly", "enemy"]
            else:
                color_filter = [color_filter]

        piece_type_filter = filters.get("piece_type")
        if piece_type_filter:
            piece_type_filter = set(piece_type_filter)

        result_squares: List[str] = []
        for i, row in enumerate(chess_board):
            for j, piece in enumerate(row):
                if piece is None:
                    continue
                if color_filter and piece.color not in color_filter:
                    continue
                if piece_type_filter and piece.__class__.__name__ not in piece_type_filter:
                    continue

                square = Board.array_index_to_square_notation(i, j)
                result_squares.append(square)

        min_required = predicate.get("min")
        required = predicate.get("required", False)

        if min_required is not None and min_required > 0 and len(result_squares) == 0:
            if required:
                raise ValueError(
                    f"Predicate requires at least {min_required} matches."
                )

        return result_squares

    def select(self, predicate: dict, timeout: float = 60.0) -> Optional[dict]:
        self._pending_selection = Event()
        self._selection_result = None
        
        try:
            search_result: Dict[str, Union[str, List[str]]] = self.search(predicate)
        except:
            return None

        self.event_handler.dispatch_event("select", data={
            "room": self.room,
            "select_type": search_result["type"],
            "select_from_item": search_result["result"],
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