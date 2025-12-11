"""
Chess Variant Piece System
==========================

A flexible and extensible framework for defining chess-like pieces with custom
movement rules, capture behavior, and rich status effect system. Designed for
advanced chess variants (Chess960, Crazyhouse, Capablanca, Shogi-inspired, or
fully custom fairy chess engines).

Features:
- Movement defined via composition of primitive move types
- Full control over capture semantics (capturable, game-ending, removable)
- Powerful StatusEffect system with stacking, duration, and countdown control
- Clean separation of concerns and easy extension
"""

from __future__ import annotations

from typing import List, Optional

from chess_related.status_effect import StatusEffect
from misc.enums import PieceName, StatusCountdownMethod


class BasePiece:
    """
    Base class for all game pieces in chess variants.

    Uses compositional movement rules and a rich status effect system
    supporting stacking and timed effects.

    Attributes:
        name (str): Lowercase piece name (e.g., "queen")
        move_rule (List[str]): Primitive movement types this piece uses
        status (List[StatusEffect]): Active status effects with metadata
        is_capturable (bool): Can be captured
        is_lose_on_capture (bool): Game ends if captured (e.g., king)
        is_removable (bool): Can be permanently removed
    """

    def __init__(
        self,
        piece_name: PieceName,
        move_rule: List[PieceName],
        *,
        spawning_point: str = "",
        is_capturable: bool = True,
        is_lose_on_capture: bool = False,
        is_removable: bool = True
    ) -> None:
        self._name = piece_name.value
        self._move_rule = [p.value for p in move_rule]
        self.status: List[StatusEffect] = []
        self.spawning_point = spawning_point
        self.is_capturable = is_capturable
        self.is_lose_on_capture = is_lose_on_capture
        self.is_removable = is_removable

    @property
    def name(self) -> str:
        """Lowercase name of the piece."""
        return self._name

    @property
    def move_rule(self) -> List[str]:
        """List of primitive movement types."""
        return self._move_rule

    # ────────────────────────────── Status Management ────────────────────────────── #

    def add_status(self, status: StatusEffect) -> StatusEffect:
        """
        Add or stack a status effect.

        Returns:
            StatusEffect: The created or updated effect
        """
        name = status.name
        stack = status.stack
        duration = status.duration
        countdown_method = status.countdown_method
        
        existing = self.get_status_effect(name)
        if existing:
            existing.stack += stack
            if duration > existing.duration:
                existing.duration = duration
                existing.countdown_method = countdown_method
            return existing

        self.status.append(status)
        return status

    def remove_status(self, name: str, stacks: int = 0) -> int:
        """
        Remove stacks of a status.

        Args:
            name: Status to reduce/remove
            stacks: Number of stacks to remove (0 = remove all)

        Returns:
            int: Remaining stacks (0 if fully removed)
        """
        effect = self.get_status_effect(name)
        if not effect:
            return 0

        if stacks <= 0 or stacks >= effect.stack:
            self.status = [s for s in self.status if s.name != name]
            return 0

        effect.stack -= stacks
        return effect.stack

    def has_status(self, name: str) -> bool:
        """Check if piece has a status (any stack count)."""
        return any(s.name == name for s in self.status)

    def get_status_effect(self, name: str) -> Optional[StatusEffect]:
        """Get the StatusEffect object by name, if present."""
        for effect in self.status:
            if effect.name == name:
                return effect
        return None

    def get_status_stack(self, name: str) -> int:
        """Get current stack count of a status (0 if absent)."""
        effect = self.get_status_effect(name)
        return effect.stack if effect else 0

    # ────────────────────────────── Representation ────────────────────────────── #

    def __str__(self) -> str:
        return self.name.capitalize()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

    def detail(self) -> str:
        """Rich debug representation showing all status details."""
        lines = [
            f"{self}",
            f"  Move rule(s): {', '.join(self.move_rule) or 'None'}",
            "  Status effects:"
        ]

        if not self.status:
            lines.append("    None")
        else:
            for s in self.status:
                duration_str = f" ({s.duration} turns)" if s.duration > 0 else " (permanent)"
                lines.append(f"    • {s.name} [x{s.stack}]{duration_str}")
                if s.countdown_method != StatusCountdownMethod.ON_TURN_END:
                    lines[-1] += f" [{s.countdown_method.value}]"

        lines += [
            f"  Capturable: {self.is_capturable}",
            f"  Game-ending on capture: {self.is_lose_on_capture}",
            f"  Removable: {self.is_removable}"
        ]

        return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────────── #
# Standard Chess Pieces
# ────────────────────────────────────────────────────────────────────────────── #

class KingPiece(BasePiece):
    """King — loss condition piece."""
    def __init__(self) -> None:
        super().__init__(PieceName.KING, [PieceName.KING], is_lose_on_capture=True, is_removable=False)

class QueenPiece(BasePiece):
    """Queen = Rook + Bishop."""
    def __init__(self) -> None:
        super().__init__(PieceName.QUEEN, [PieceName.BISHOP, PieceName.ROOK])

class BishopPiece(BasePiece):
    def __init__(self) -> None:
        super().__init__(PieceName.BISHOP, [PieceName.BISHOP])

class KnightPiece(BasePiece):
    def __init__(self) -> None:
        super().__init__(PieceName.KNIGHT, [PieceName.KNIGHT])

class RookPiece(BasePiece):
    def __init__(self) -> None:
        super().__init__(PieceName.ROOK, [PieceName.ROOK])

class PawnPiece(BasePiece):
    def __init__(self) -> None:
        super().__init__(PieceName.PAWN, [PieceName.PAWN])

class NonePiece(BasePiece):
    def __init__(self):
        super().__init__(PieceName.UNKNOWN, [])

# ────────────────────────────────────────────────────────────────────────────── #
# Demo / Test
# ────────────────────────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    pawn = PawnPiece()
    pawn.add_status(StatusEffect("en_passant_vulnerable", duration=-1))
    pawn.add_status(StatusEffect("poisoned", stack=2, duration=3))
    

    print("=== Initial State ===")
    print(pawn.detail())