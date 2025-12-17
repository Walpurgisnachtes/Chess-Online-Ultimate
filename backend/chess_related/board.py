from typing import List, Tuple, Dict, Optional
from uuid import UUID, uuid4
import re

from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from misc.enums import PieceName

from controller_related.event_controller import EventHandler
class Board:
    """
    Represents an 8x8 chess board with support for chess variants.
    Uses standard algebraic notation (e.g., 'e4', 'a1', 'h8').
    """

    def __init__(self):
        self.BOARD_DIMENSION = 8
        self.board: List[List[Optional[BasePiece]]] = [
            [NonePiece() for _ in range(8)] for _ in range(8)
        ]
        self.card_event_handler: EventHandler = None
        
    def setup_standard_position(self):
        # Black back row (row 0)
        self.board[0] = [
            RookPiece("black"),
            KnightPiece("black"),
            BishopPiece("black"),
            QueenPiece("black"),
            KingPiece("black"),
            BishopPiece("black"),
            KnightPiece("black"),
            RookPiece("black")
        ]

        # Black pawns (row 1)
        self.board[1] = [PawnPiece("black") for _ in range(8)]

        # Empty rows (2-5)
        for row in range(2, 6):
            self.board[row] = [NonePiece() for _ in range(8)]

        # White pawns (row 6)
        self.board[6] = [PawnPiece("white") for _ in range(8)]

        # White back row (row 7)
        self.board[7] = [
            RookPiece("white"),
            KnightPiece("white"),
            BishopPiece("white"),
            QueenPiece("white"),
            KingPiece("white"),
            BishopPiece("white"),
            KnightPiece("white"),
            RookPiece("white")
        ]
    
    def array_index_to_square_notation(self, i: int, j: int) -> str:
        """
        Convert zero-based array coordinates (row i, column j) into
        algebraic chess notation (e.g., a8, h1).

        Top-left array cell (0, 0) maps to a8 by default.
        """
        if not (0 <= i < self.BOARD_DIMENSION and 0 <= j < self.BOARD_DIMENSION):
            raise ValueError(f"Board indices out of range: ({i}, {j})")

        column_char = chr(ord("a") + j)
        row = self.BOARD_DIMENSION - i
        return f"{column_char}{row}"
    
    def square_notation_to_array_index(self, square: str) -> Tuple[int, int]:
        """
        Convert algebraic chess notation (e.g., 'a8', 'h1') back into
        zero-based array coordinates (row i, column j).

        This assumes the same orientation as `array_index_to_square_notation`:
        - Top-left board cell is (0, 0) and corresponds to 'a8'.
        - Columns run 'a' through 'h' (or up to BOARD_DIMENSION columns).
        - Rows run BOARD_DIMENSION down to 1 from top to bottom.

        Returns:
            A tuple (i, j) where:
                i = row index (0-based, top-down)
                j = column index (0-based, left-right)

        Raises:
            ValueError: if the notation is malformed or out of range.
        """
        square = square.strip().lower()

        if not re.fullmatch(r"[a-z]\d+", square):
            raise ValueError(f"Invalid square notation: '{square}'")

        column_char = square[0]
        row_str = square[1:]

        j = ord(column_char) - ord("a")
        if not (0 <= j < self.BOARD_DIMENSION):
            raise ValueError(f"Column out of range: '{column_char}'")

        try:
            row = int(row_str)
        except ValueError:
            raise ValueError(f"Row is not a number: '{row_str}'") from None

        if not (1 <= row <= self.BOARD_DIMENSION):
            raise ValueError(f"Row out of range: {row}")

        i = self.BOARD_DIMENSION - row
        return i, j

    def get_piece_at_square(self, square: str) -> Optional[BasePiece]:
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
        row_idx, column_idx = self.square_notation_to_array_index(square)
        
        # Final bounds check (redundant but safe)
        if not (0 <= column_idx <= 7 and 0 <= row_idx <= 7):
            return None

        return self.board[row_idx][column_idx]
    
    def get_piece_by_uuid(self, uuid: UUID) -> Optional[BasePiece]:
        for row_index, row in enumerate(self.board):
            for col_index, element in enumerate(row):
                if not isinstance(element, NonePiece) and element.uuid == uuid:
                    return element
        
        # If the loop finishes without finding the element
        return None 
    
    def move_piece(self, from_sq: str, to_sq: str, en_passant_square: str = None, promotion: str = None) -> bool:
        promotion_dict: Dict[PieceName, BasePiece] = {
            PieceName.BISHOP: BishopPiece,
            PieceName.KNIGHT: KnightPiece,
            PieceName.ROOK: RookPiece,
            PieceName.QUEEN: QueenPiece,
        }
        
        moving_piece = self.remove_piece(from_sq)
        if not moving_piece:
            return False
        target_piece = self.remove_piece(to_sq)
        
        en_passant_piece = None
        if en_passant_square:
            en_passant_piece = self.remove_piece(en_passant_square)
        
        if promotion:
            promoted_to: BasePiece = promotion_dict.get(promotion, None)
            if promoted_to:
                moving_piece = promoted_to
        
        self.place_piece(moving_piece, to_sq)
        
        if en_passant_piece:
            print(f"{from_sq} -> {to_sq} <{target_piece}> <{en_passant_piece}> = <{moving_piece}>")
        else:
            print(f"{from_sq} -> {to_sq} <{target_piece}> = <{moving_piece}>")
    
    def place_piece(self, piece: BasePiece, square: str, uuid: Optional[UUID] = None) -> bool:
        """
        Place a piece on the board at the given square.

        Returns:
            bool: True if placement succeeded
        """
        target = self.get_piece_at_square(square)
        if target is None:
            return False  # Invalid square

        row_idx, column_idx = self.square_notation_to_array_index(square)
        self.board[row_idx][column_idx] = piece
        
        if not uuid:
            piece.uuid = uuid
        else:
            piece.uuid = uuid4()
        
        if self.card_event_handler:
            self.card_event_handler.dispatch_event("piece_placed", data={
                "square": square,
                "piece": piece
            })
        
        return True

    def remove_piece(self, square: str) -> Optional[BasePiece]:
        """
        Remove and return the piece from the given square (for capture/drop).

        Returns:
            The removed piece, or None if square was empty or invalid
        """
        piece = self.get_piece_at_square(square)
        if piece is None or piece is NonePiece():
            return None

        row_idx, column_idx = self.square_notation_to_array_index(square)
        if 0 <= row_idx < 8 and 0 <= column_idx < 8:
            self.board[row_idx][column_idx] = NonePiece()
        
        if self.card_event_handler:
            self.card_event_handler.dispatch_event("piece_placed", data={
                "square": square,
                "piece": piece
            })
            
        return piece

    def is_empty(self, square: str) -> bool:
        """Check if a square is empty."""
        piece = self.get_piece_at_square(square)
        return piece is None or isinstance(piece, NonePiece)

    def __str__(self) -> str:
        """Pretty-print the board (useful for debugging)."""
        lines = ["  a b c d e f g h"]
        for row in range(7, -1, -1):
            this_row = [f"{row + 1}"]
            for column in range(8):
                piece = self.board[row][column]
                symbol = "·" if isinstance(piece, NonePiece) else piece.name[0].upper()
                this_row.append(symbol)
            this_row.append(f"{row + 1}")
            lines.append(" ".join(this_row))
        lines.append("  a b c d e f g h")
        return "\n".join(lines)
    
if __name__ == "__main__":
    board = Board()
    queen = QueenPiece()
    board.place_piece(queen, "d1")
    
    print(board.get_piece_at_square("d1"))   # → Queen
    print(board.get_piece_at_square("e4"))   # → NonePiece
    print(board.get_piece_at_square("z9"))   # → None (invalid)
    
    print(board)