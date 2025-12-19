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
from chess_related.status_effect import StatusEffect

from controller_related.event_controller import EventHandler
from controller_related.static_filter_base import StaticFilterBase

from misc.enums import StatusCountdownMethod, PieceName

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
        self.card_event_handler = EventHandler()
        self.current_player = self.PLAYER_COLOR_WHITE
        
        self.board.card_event_handler = self.card_event_handler
        
        self.filters: StaticFilterBase = []
        
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
    
    def resolve_player_colors(self, player_color: str) -> List[str]:
        friendly = self.current_player
        enemy = self.PLAYER_COLOR_BLACK if friendly == self.PLAYER_COLOR_WHITE else self.PLAYER_COLOR_WHITE
        
        mapping = {
            "all": [friendly, enemy],
            "friendly": [friendly],
            "enemy": [enemy]
        }
        
        # Returns the mapped list, or the specific color in a list if not found in mapping
        return mapping.get(player_color, [player_color])
    
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
        interpreted_color_filter = self.resolve_player_colors(color_filter)
        
        piece_type_filter = filters.get("piece_type", None)
        if piece_type_filter:
            piece_type_filter = set(piece_type_filter)
        
        custom_filters = filters.get("custom", [])

        result_squares: List[str] = []
        for i, row in enumerate(chess_board):
            for j, piece in enumerate(row):
                if isinstance(piece, NonePiece):
                    continue
                if interpreted_color_filter and piece.color not in interpreted_color_filter:
                    continue
                if piece_type_filter and piece.__class__.__name__ not in piece_type_filter:
                    continue
                if len(custom_filters) > 0 and not self.pass_custom_filters(piece, custom_filters):
                    continue

                square = self.board.array_index_to_square_notation(i, j)
                result_squares.append(square)

        print(result_squares)
        min_required = predicate.get("min")
        required = predicate.get("required", False)

        if min_required is not None and min_required > 0 and len(result_squares) < min_required:
            if required:
                raise ValueError(
                    f"Predicate requires at least {min_required} matches."
                )

        return result_squares

    def select(self, predicate: dict, timeout: float = 120.0) -> Optional[List[str]]:
        self._pending_selection = Event()
        self._selection_result = None
        
        try:
            search_result: Dict[str, Union[str, List[str]]] = self.search(predicate)
        except Exception as e:
            print(f"No valid target in search result... Error: {e}")
            return None

        self.event_handler.dispatch_event("select", data={
            "room": self.room,
            "select_type": search_result["type"],
            "select_from_item": search_result["result"],
            "min": predicate["min"],
            "max": predicate["max"],
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

    def cancel_selection(self):
        self._selection_result = None
        if self._pending_selection:
            self._pending_selection.resolved = True
    
    def try_play_card_with_index_in_hand(self, hand_index: int) -> Dict[str, Union[str, bool]]:
        """
        Validate and begin playing a card from the current player's hand.
        Returns True if card is accepted and execution begins.
        """
        try:
            hand_index = int(hand_index)
        except (ValueError, TypeError):
            return False

        current_player = self.players[self.current_player]
        if hand_index < 0 or hand_index >= len(current_player.hand):
            return False

        card_instance = current_player.hand[hand_index]
        if not card_instance:
            return False

        # Get prototype from StaticCardBase
        # card_prototype = StaticCardBase.instance().get_by_id(card_instance.id)
        card_prototype = StaticCardBase.instance().get_by_id("10003")
        if not card_prototype:
            return False

        # Check prestige (mana) cost
        if current_player.prestige < card_prototype.cost:
            return False

        # Deduct cost
        current_player.prestige -= card_prototype.cost
        self.card_event_handler.dispatch_event("card_play_prestige_reduced", data={
            "card_id": [card_prototype.id],
        })

        # Remove from hand (will go to graveyard later)
        current_player.graveyard.append(current_player.hand[hand_index])
        del current_player.hand[hand_index]
        self.card_event_handler.dispatch_event("card_sent_graveyard", data={
            "card_id": [card_prototype.id],
        })

        # Dispatch acceptance event → app.py emits to frontend
        self.event_handler.dispatch_event("card_play_accepted", data={
            "room": self.room,
            "player_color": self.current_player,
            "card_id": card_prototype.id,
            "hand_index": hand_index  # For frontend animation
        })

        # Now execute the card effect
        self.execute_card(card_prototype)

        return True

    def execute_card(self, card_prototype):
        """
        Create card instance and run its exec()
        """
        # Dynamically load card class
        card_class_name = f"Card{card_prototype.id}"
        try:
            card_module = import_module(f"cards.{card_class_name}")
            card_class = getattr(card_module, card_class_name)
        except (ImportError, AttributeError):
            print(f"[ERROR] Card {card_prototype.id} class not found")
            return

        # Instantiate and execute
        card_obj: Card = card_class(controller=self)
        card_obj.exec()
        
        self.event_handler.dispatch_event("update_hand", data={
            "room": self.room,
            "white_hand": self.players.get(self.PLAYER_COLOR_WHITE).hand,
            "black_hand": self.players.get(self.PLAYER_COLOR_BLACK).hand
        })

    def move_piece(self, move_object: Dict[str, str]) -> Dict[str, bool]:
        from_where = move_object.get("from", "a8")
        to_where = move_object.get("to", "a1")
        promotion = move_object.get("promotion", None)
        result = {
            'success': False,
            'en_passant': '', 
            'win': False
        }

        # 1. Get the piece from the board
        piece = self.board.get_piece_at_square(from_where)
        print(f"Piece: {piece.__class__.__name__}, Color: {piece.color}")
        if not piece or piece.color != self.current_player:
            print("not passing piece color check")
            return result
        is_movable = piece.has_status("movable") or piece.has_status("card_given_movable")
        if not is_movable:
            print("not passing movable piece check")
            return result

        # 2. Check if move is possible under current moving rules
        if not self.is_valid_move(piece, from_where, to_where):
            print("not passing piece valid move check")
            return result

        # 3. Check for capture
        target_piece = self.board.get_piece_at_square(to_where)
        captured = False
        if target_piece:
            if target_piece.color == self.current_player or not target_piece.is_capturable:
                print("not passing piece capturable check")
                print(target_piece.color, self.current_player, target_piece.is_capturable)
                return result
            captured = True

        # 4. Success — prepare result
        result["success"] = True

        # 5. If captured and is_lose_on_capture, add win
        if captured and target_piece.is_lose_on_capture:
            result['win'] = True

        # Handle en passant
        en_passant_square = None
        if piece._name == PieceName.PAWN:
            en_passant_square = self.get_en_passant_square(from_where, to_where, piece.color)
            result['en_passant'] = en_passant_square    
        
        # Handle promotion if applicable
        if piece._name == PieceName.PAWN and self.is_promotion_rank(to_where, piece.color) and promotion != "none":
            self.board.move_piece(from_where, to_where, en_passant_square, promotion=promotion if promotion != "none" else None)
        
        self.board.move_piece(from_where, to_where, en_passant_square)
        
        for row in self.board.board:
            for piece in row:
                if not piece or isinstance(piece, NonePiece):
                    continue
                self.remove_piece_status(piece, "movable", stack=-1)
        self.remove_piece_status(piece, "card_given_movable", stack=-1)

        return result

    def check_property_bound_with_status(self, piece: BasePiece):
        piece.is_capturable = not piece.has_status("uncapturable")
        piece.is_removable = not piece.has_status("unremovable")

    def is_valid_move(self, piece: BasePiece, from_square: str, to_square: str) -> bool:
        """
        Validate if the move is legal based on the piece's current move_rule list.
        Does NOT hardcode rules — dynamically checks each rule in the list.
        """
        from_row, from_col = self.board.square_notation_to_array_index(from_square)
        to_row, to_col = self.board.square_notation_to_array_index(to_square)

        for rule in piece._move_rule:
            if self.check_move_by_rule(rule, from_row, from_col, to_row, to_col, piece.color):
                return True
        return False

    def get_en_passant_square(self, from_square: str, to_square: str, color: str) -> Optional[str]:
        from_row, from_col = self.board.square_notation_to_array_index(from_square)
        to_row, to_col = self.board.square_notation_to_array_index(to_square)
        direction = -1 if color == self.PLAYER_COLOR_WHITE else 1
        
        dr = to_row - from_row
        dc = to_col - from_col
        
        if abs(dc) == 1 and dr == direction:
            en_passant_col = to_col - direction
            en_passant_square = self.board.array_index_to_square_notation(to_row, en_passant_col)
            en_passant_piece = self.board.get_piece_at_square(en_passant_square)
            if en_passant_piece.has_status("en_passant"):
                return en_passant_square
        
        return None

    def check_move_by_rule(self, rule: str, fr: int, fc: int, tr: int, tc: int, color: str) -> bool:
        """
        Dynamic move validation per rule type.
        Checks path clear for unlimited moves.
        """
        dr = tr - fr
        dc = tc - fc
        
        print(f"""
Checking rule \"{color} {rule}\" 
[row] from {fr} to {tr} dr {dr}
[col] from {fc} to {tc} dr {dc}
""")

        if rule == PieceName.BISHOP:
            if abs(dr) != abs(dc) or dr == 0: return False
            return self.is_path_clear(fr, fc, tr, tc)

        elif rule == PieceName.ROOK:
            if (dr != 0 and dc != 0) or (dr == 0 and dc == 0): return False
            return self.is_path_clear(fr, fc, tr, tc)

        elif rule == PieceName.KNIGHT:
            return (abs(dr) == 2 and abs(dc) == 1) or (abs(dr) == 1 and abs(dc) == 2)

        elif rule == PieceName.KING:
            return max(abs(dr), abs(dc)) == 1

        elif rule == PieceName.PAWN:
            direction = -1 if color == self.PLAYER_COLOR_WHITE else 1
            if dc == 0:  # forward pushes
                target_piece = self.board.get_piece_at_square(
                    self.board.array_index_to_square_notation(tr, tc)
                )
                target_mid_piece = self.board.get_piece_at_square(
                    self.board.array_index_to_square_notation(fr + direction, fc)
                )
                if (dr == direction and isinstance(target_piece, NonePiece)):
                    return True
                if (
                    dr == 2 * direction
                    and fr == (6 if color == self.PLAYER_COLOR_WHITE else 1)
                    and isinstance(target_mid_piece, NonePiece)
                    and isinstance(target_piece, NonePiece)
                ):
                    return True

            elif abs(dc) == 1 and dr == direction:
                target_square = self.board.array_index_to_square_notation(tr, tc)
                target_piece = self.board.get_piece_at_square(target_square)
                if target_piece:
                    return True
                else:
                    target_en_passant_square = self.board.array_index_to_square_notation(fr, tc)
                    target_en_passant_piece = self.board.get_piece_at_square(target_en_passant_square)
                    if target_en_passant_piece.has_status("en_passant"):
                        return True

            return False

        elif rule == PieceName.REDUCED_BISHOP:
            return abs(dr) == abs(dc) == 1  # 1 square diagonal

        elif rule == PieceName.REDUCED_ROOK:
            return (abs(dr) == 1 and dc == 0) or (abs(dc) == 1 and dr == 0)  # 1 square orthogonal

        # Add more rules as needed (e.g., "jinetes" modifies piece.move_rule dynamically)

        return False  # Unknown rule

    def is_path_clear(self, fr: int, fc: int, tr: int, tc: int) -> bool:
        """
        Check if path between squares is empty (for sliding pieces)
        """
        dr = (tr - fr) // max(1, abs(tr - fr))  # Step direction row
        dc = (tc - fc) // max(1, abs(tc - fc))  # Step direction col

        cr, cc = fr + dr, fc + dc

        print("Checking if path clear...")
        
        while (cr, cc) != (tr, tc):
            target_piece = self.board.get_piece_at_square(self.board.array_index_to_square_notation(cr, cc))
            if not isinstance(target_piece, NonePiece):
                print(f"Path is not clear at {self.board.array_index_to_square_notation(cr, cc)} with Piece {target_piece}")
                return False
            cr += dr
            cc += dc
        return True

    def is_promotion_rank(self, square: str, color: str) -> bool:
        rank = int(square[1])
        return (color == self.PLAYER_COLOR_WHITE and rank == 8) or (color == self.PLAYER_COLOR_BLACK and rank == 1)

    def pass_custom_filters(self, piece, filter_names) -> bool:
        return any(
            getattr(StaticFilterBase, name)(piece, self.board)
            for name in filter_names
            if hasattr(StaticFilterBase, name) and callable(getattr(StaticFilterBase, name))
        )

    def game_start(self):
        for color, player in self.players.items():
            self.card_event_handler.dispatch_event("game_start")
            self.card_event_handler.dispatch_event("game_start_draw")
            player.deck.shuffle()
            drawn_cards = player.deck.draw_5()
            player.hand = drawn_cards
            self.card_event_handler.dispatch_event("card_drawn", data={
                "card_id": [card.id for card in drawn_cards],
                "player_color": color
            })
            
            player.prestige = 5
        self.board.setup_standard_position()
        self.turn_start()

    def turn_start(self):
        for row in self.board.board:
            for piece in row:
                if not piece or isinstance(piece, NonePiece):
                    continue
                self.add_piece_status(piece, StatusEffect("movable"))
                
        self.card_event_handler.dispatch_event("turn_start", data={})

    def remove_piece(self, piece_pos_square: str):
        self.board.remove_piece(piece_pos_square)
        self.event_handler.dispatch_event(
            event_name="remove_piece", 
            data={
                "room": self.room,
                "position": piece_pos_square
            })

    def draw(self, player_color: str, amount: int):
        interpreted_color_filter = self.resolve_player_colors(player_color)
        
        for player_color in interpreted_color_filter:
            player = self.players[player_color]
            
            drawn_cards = player.deck.draw(amount)
            player.hand.extend(drawn_cards)
            self.card_event_handler.dispatch_event("card_drawn", data={
                "card_id": [card.id for card in drawn_cards],
            })

    def add_piece_status(self, piece: BasePiece, status: StatusEffect) -> None:
        """Attach a status to a piece and propagate related side effects."""
        piece.add_status(status)
        self.check_property_bound_with_status(piece)
        self.card_event_handler.dispatch_event(
            "piece_status_added",
            data={"piece": piece, "status": status},
        )

    def remove_piece_status(
        self,
        piece: BasePiece,
        status_name: str,
        stack: int = 0,
        duration: int = 0,
    ) -> None:
        """
        Remove or tick down a status on a piece.

        * If `stack` is non-zero, delegate to the piece to trim stacks first.
        * Afterwards, decrement duration (if any remains) and drop the status entirely
        once its duration expires or stacks vanish.
        """
        status = piece.get_status_effect(status_name)
        if status is None:
            self.check_property_bound_with_status(piece)
            return

        if stack:
            piece.remove_status(status_name, stack)
            status = piece.get_status_effect(status_name)
            if status is None:
                self.check_property_bound_with_status(piece)
                return  # Status fully removed by stack depletion.

        # Duration-based removal.
        should_remove = status.decrement_duration(duration) if duration else False
        if should_remove:
            piece.remove_status(status_name)
        self.check_property_bound_with_status(piece)

    def turn_end(self):
        """Resolve end-of-turn status countdowns, fire events, and swap the active player."""
        self.card_event_handler.dispatch_event("turn_end", data={})

        for row in self.board.board:
            for piece in row:
                if not piece or isinstance(piece, NonePiece):
                    continue

                for status in list(piece.status):
                    should_tick = (
                        status.countdown_method == StatusCountdownMethod.ON_TURN_END
                        and piece.color == self.current_player
                    ) or (
                        status.countdown_method == StatusCountdownMethod.ON_BOTH_TURN_END
                    )

                    if should_tick:
                        self.remove_piece_status(piece, status.name, duration=1)

        self.current_player = (
            self.PLAYER_COLOR_WHITE
            if self.current_player == self.PLAYER_COLOR_BLACK
            else self.PLAYER_COLOR_BLACK
        )
