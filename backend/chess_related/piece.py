"""
Chess Variant Piece System
==========================

A flexible and extensible framework for defining chess-like pieces with custom
movement rules, capture behavior, and game-specific properties. Designed for
chess variants (e.g., Chess960, Crazyhouse, Shogi-inspired games, or completely
custom board games).

Features:
- Piece movement defined via composition of base movement types
- Configurable capture rules (capturable, lose-on-capture, removable)
- Enum-based piece naming for type safety
- Easy extension for new piece types and rules

Example:
    >>> queen = QueenPiece()
    >>> print(queen)
    Queen
    >>> queen.move_rule
    ['bishop', 'rook']
"""

from __future__ import annotations

from typing import List, Optional
from random import shuffle, randrange, sample
from copy import deepcopy
from enum import StrEnum, auto


class PieceName(StrEnum):
    """Enum representing standard and special chess piece types."""
    KING = "king"
    QUEEN = "queen"
    BISHOP = "bishop"
    KNIGHT = "knight"
    ROOK = "rook"
    PAWN = "pawn"
    UNKNOWN = auto()  # Placeholder for undefined or custom pieces


class BasePiece:
    """
    Base class for all game pieces.

    Defines core attributes and behavior shared across all piece types.
    Movement capability is defined by a list of base movement rules
    (e.g., a Queen moves as Bishop + Rook).

    Attributes:
        name (str): Human-readable name of the piece (e.g., "queen")
        move_rule (List[str]): List of base movement types this piece can use
        status (List[str]): Game-specific status flags (e.g., "promoted", "checked")
        is_capturable (bool): Can this piece be captured by opponents?
        is_lose_on_capture (bool): Does capturing this piece end the game? (e.g., King)
        is_removable (bool): Can this piece be permanently removed from play?
    """

    def __init__(
        self,
        piece_name: PieceName,
        move_rule: List[PieceName],
        *,
        is_capturable: bool = True,
        is_lose_on_capture: bool = False,
        is_removable: bool = True
    ) -> None:
        """
        Initialize a new piece.

        Args:
            piece_name: The type/name of the piece
            move_rule: List of primitive movement types this piece combines
            is_capturable: Whether opponents can capture this piece
            is_lose_on_capture: True for kings — game ends if captured
            is_removable: Whether the piece can be taken off the board permanently
        """
        self._name = piece_name.value
        self._move_rule = [p.value for p in move_rule]
        self.status: List[str] = []
        self.is_capturable = is_capturable
        self.is_lose_on_capture = is_lose_on_capture
        self.is_removable = is_removable

    @property
    def name(self) -> str:
        """Get the name of the piece (e.g., 'queen')."""
        return self._name

    @property
    def move_rule(self) -> List[str]:
        """Get the list of base movement rules this piece uses."""
        return self._move_rule

    def add_status(self, status: str) -> None:
        """Add a gameplay status flag to this piece."""
        if status not in self.status:
            self.status.append(status)

    def remove_status(self, status: str) -> None:
        """Remove a gameplay status flag from this piece."""
        self.status = [s for s in self.status if s != status]

    def has_status(self, status: str) -> bool:
        """Check if the piece currently has a specific status."""
        return status in self.status

    def __str__(self) -> str:
        """Return capitalized name for display (e.g., 'Queen')."""
        return self.name.capitalize()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def detail(self) -> str:
        """
        Return a detailed string representation of the piece.

        Useful for debugging and logging in variant engines.
        """
        return f"""
{self}
    Move rule(s): {', '.join(self.move_rule) or 'None'}
    Status: {', '.join(self.status) or 'None'}
    Capturable: {self.is_capturable}
    Game-ending on capture: {self.is_lose_on_capture}
    Removable from board: {self.is_removable}
""".strip()


class KingPiece(BasePiece):
    """Standard king piece — game ends if captured."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.KING,
            move_rule=[PieceName.KING],
            is_capturable=True,
            is_lose_on_capture=True,
            is_removable=False
        )


class QueenPiece(BasePiece):
    """Standard queen — combines rook and bishop movement."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.QUEEN,
            move_rule=[PieceName.BISHOP, PieceName.ROOK]
        )


class BishopPiece(BasePiece):
    """Standard bishop — diagonal movement only."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.BISHOP,
            move_rule=[PieceName.BISHOP]
        )


class KnightPiece(BasePiece):
    """Standard knight — L-shaped jumps."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.KNIGHT,
            move_rule=[PieceName.KNIGHT]
        )


class RookPiece(BasePiece):
    """Standard rook — horizontal and vertical movement."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.ROOK,
            move_rule=[PieceName.ROOK]
        )


class PawnPiece(BasePiece):
    """Standard pawn — forward movement, diagonal capture."""

    def __init__(self) -> None:
        super().__init__(
            piece_name=PieceName.PAWN,
            move_rule=[PieceName.PAWN]
        )


# --------------------------------------------------------------------------- #
# Demo / Test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    queen = QueenPiece()
    king = KingPiece()
    pawn = PawnPiece()

    print("=== Piece Details ===")
    print(queen.detail())
    print(king.detail())
    print(pawn.detail())

    # Example of status tracking
    pawn.add_status("promotable")
    pawn.add_status("en_passant_vulnerable")
    print("Pawn with status:")
    print(pawn.detail())