from misc.enums import StatusCountdownMethod

class StatusEffect:
    """
    Represents a single status effect applied to a piece.

    Supports stacking (e.g., multiple poison layers), timed duration,
    and configurable countdown behavior.

    Attributes:
        name (str): Unique identifier of the status (e.g., "poisoned", "promotable")
        stack (int): Number of times this status is stacked (default: 1)
        duration (int): Number of turns remaining (0 = permanent)
        countdown_method (StatusCountdownMethod): When the duration decreases
    """

    def __init__(
        self,
        name: str,
        stack: int = 1,
        duration: int = 1,
        countdown_method: StatusCountdownMethod = StatusCountdownMethod.ON_TURN_END
    ) -> None:
        """
        Create a new status effect.

        Args:
            name: Identifier for the status
            stack: Stack count (useful for intensifying effects)
            duration: Turns remaining (-1 = infinite)
            countdown_method: When to decrement duration
        """
        self.name = name
        self.stack = max(1, stack)  # Ensure at least 1
        self.duration = duration
        self.countdown_method = countdown_method

    def decrement_duration(self) -> bool:
        """
        Decrement duration if applicable.

        Returns:
            bool: True if the status has expired (duration reached 0)
        """
        if self.duration > -1:
            self.duration -= 1
            return self.duration <= 0
        return False

    def __repr__(self) -> str:
        if self.duration > 0:
            return f"StatusEffect({self.name!r}, stack={self.stack}, expires_in={self.duration})"
        return f"StatusEffect({self.name!r}, stack={self.stack})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StatusEffect):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)
