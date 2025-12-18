from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Union, Callable, Iterable, Any, Optional
from card_related.card_driver import Card, Deck
from card_related.system_driver import System
from card_related.static_card_base import StaticCardBase, StaticSystemBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from player_related.player import Player


from controller_related.event_controller import EventHandler

class StaticFilterBase:
    """
    A container for static filtering methods.
    Each method follows the signature: (board, piece) -> bool
    """

    @staticmethod
    def only_of_column(piece: BasePiece, board: Board) -> bool:
        pos = StaticFilterBase._piece_position(piece, board)
        if pos is None:
            return False
        _, col = pos
        coords = [(row, col) for row in range(8)]
        return StaticFilterBase._is_only_piece_at_coords(piece, board, coords)

    @staticmethod
    def only_of_row(piece: BasePiece, board: Board) -> bool:
        pos = StaticFilterBase._piece_position(piece, board)
        if pos is None:
            return False
        row, _ = pos
        coords = [(row, col) for col in range(8)]
        return StaticFilterBase._is_only_piece_at_coords(piece, board, coords)

    @staticmethod
    def only_of_all_diagonal(piece: BasePiece, board: Board) -> bool:
        return (
            StaticFilterBase.only_of_white_diagonal(piece, board)
            and StaticFilterBase.only_of_black_diagonal(piece, board)
        )

    @staticmethod
    def only_of_white_diagonal(piece: BasePiece, board: Board) -> bool:
        pos = StaticFilterBase._piece_position(piece, board)
        if pos is None:
            return False
        row, col = pos
        diff = row - col
        coords = []
        for r in range(8):
            c = r - diff
            if 0 <= c < 8:
                coords.append((r, c))
        return StaticFilterBase._is_only_piece_at_coords(piece, board, coords)

    @staticmethod
    def only_of_black_diagonal(piece: BasePiece, board: Board) -> bool:
        pos = StaticFilterBase._piece_position(piece, board)
        if pos is None:
            return False
        row, col = pos
        total = row + col
        coords = []
        for r in range(8):
            c = total - r
            if 0 <= c < 8:
                coords.append((r, c))
        return StaticFilterBase._is_only_piece_at_coords(piece, board, coords)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _piece_position(piece: BasePiece, board: Board) -> tuple[int, int] | None:
        square = board.get_square_of_piece(piece)
        if not square:
            return None
        return board.square_notation_to_array_index(square)

    @staticmethod
    def _is_only_piece_at_coords(
        piece: BasePiece,
        board: Board,
        coords: list[tuple[int, int]],
    ) -> bool:
        print(f"Checking if piece {piece} is unique in the coordinates {coords}...")
        pieces = StaticFilterBase._piece_at_coords(piece, board, coords)
        return len(pieces) == 1 and pieces[0] == piece

    @staticmethod
    def _piece_at_coords(
        piece: BasePiece,
        board: Board,
        coords: list[tuple[int, int]],
    ) -> list[BasePiece]:
        piece_found = []
        for r, c in coords:
            that_piece = board.board[r][c]
            print(f"r: {r}, c: {c}, that_piece: {that_piece}")
            if not isinstance(that_piece, NonePiece):
                piece_found.append(that_piece)

        print(f"Found {len(piece_found)} pieces in coordinates. {piece_found}\n")
        return piece_found