from typing import List, Optional
import re

from pathlib import Path
import sys
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    parent_dir = str(Path(__file__).resolve().parents[1])
    sys.path.append(parent_dir)
    __package__ = "backend.chess_related"
    
from piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_utils import *

class Board:
    """
    Represents an 8x8 chess board with support for chess variants.
    Uses standard algebraic notation (e.g., 'e4', 'a1', 'h8').
    """

    def __init__(self):
        self.board: List[List[Optional[BasePiece]]] = [
            [NonePiece() for _ in range(8)] for _ in range(8)
        ]

    def find_by_square(self, square: str) -> Optional[BasePiece]:
        """
        Find and return the piece at a given algebraic notation square.

        Args:
            square: Algebraic notation (e.g., 'e4', 'a1', 'h8', 'B6'). Case-insensitive.

        Returns:
            BasePiece | NonePiece: The piece at the square, or NonePiece if empty/invalid.
            Returns None only if the square notation is completely invalid.

        Raises:
            ValueError: If the square notation is malformed (optional — here we return None instead)
        """
        if not square or not isinstance(square, str):
            return None

        # Normalize and validate algebraic notation
        square = square.strip().lower()
        match = re.match(r"^([a-h])([1-8])$", square)
        if not match:
            return None  # Invalid square format

        file_char, rank_char = match.groups()
        file_idx = ord(file_char) - ord('a')  # 'a' → 0, 'b' → 1, ..., 'h' → 7
        rank_idx = int(rank_char) - 1         # '1' → 0, '2' → 1, ..., '8' → 7

        # Final bounds check (redundant but safe)
        if not (0 <= file_idx <= 7 and 0 <= rank_idx <= 7):
            return None

        return self.board[rank_idx][file_idx]
    
    def place_piece(self, piece: BasePiece, square: str) -> bool:
        """
        Place a piece on the board at the given square.

        Returns:
            bool: True if placement succeeded
        """
        target = self.find_by_square(square)
        if target is None:
            return False  # Invalid square

        file_idx = ord(square[0].lower()) - ord('a')
        rank_idx = int(square[1]) - 1
        self.board[rank_idx][file_idx] = piece
        return True

    def remove_piece(self, square: str) -> Optional[BasePiece]:
        """
        Remove and return the piece from the given square (for capture/drop).

        Returns:
            The removed piece, or None if square was empty or invalid
        """
        piece = self.find_by_square(square)
        if piece is None or piece is NonePiece():
            return None

        file_idx = ord(square[0].lower()) - ord('a')
        rank_idx = int(square[1]) - 1
        if 0 <= rank_idx < 8 and 0 <= file_idx < 8:
            self.board[rank_idx][file_idx] = NonePiece()
        return piece

    def is_empty(self, square: str) -> bool:
        """Check if a square is empty."""
        piece = self.find_by_square(square)
        return piece is None or isinstance(piece, NonePiece)

    def __str__(self) -> str:
        """Pretty-print the board (useful for debugging)."""
        lines = ["  a b c d e f g h"]
        for rank in range(7, -1, -1):
            row = [f"{rank + 1}"]
            for file in range(8):
                piece = self.board[rank][file]
                symbol = "·" if isinstance(piece, NonePiece) else piece.name[0].upper()
                row.append(symbol)
            row.append(f"{rank + 1}")
            lines.append(" ".join(row))
        lines.append("  a b c d e f g h")
        return "\n".join(lines)
    
if __name__ == "__main__":
    board = Board()
    queen = QueenPiece()
    board.place_piece(queen, "d1")
    
    print(board.find_by_square("d1"))   # → Queen
    print(board.find_by_square("e4"))   # → NonePiece
    print(board.find_by_square("z9"))   # → None (invalid)
    
    print(board)