from enum import IntEnum, StrEnum, auto

class StatusCountdownMethod(IntEnum):
    ON_TURN_END = auto()
    ON_BOTH_TURN_END = auto()
    INFINITE = auto()

class PieceName(StrEnum):
    """Enum representing standard and special chess piece types."""
    KING = "king"
    QUEEN = "queen"
    BISHOP = "bishop"
    KNIGHT = "knight"
    ROOK = "rook"
    PAWN = "pawn"
    UNKNOWN = auto()  # Placeholder for undefined or custom pieces
