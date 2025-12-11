"""
player_related/player.py

Model class representing a player in the card game system.
Part of the MVC architecture (Model layer only).
"""

from copy import deepcopy
from typing import List, Dict, Any

from card_related.card_driver import Deck, Card


class Player:
    """
    Represents a single player in the card game.

    Pure Model class — holds state only. All game mechanics that belong to the deck
    (drawing, shuffling, etc.) are delegated to the ``Deck`` instance.

    Attributes:
        username (str): Player's display name.
        sid (str): Flask-SocketIO session ID (from ``request.sid``).
        system_id (int): Persistent unique identifier (e.g., database ID).
        original_deck (Deck): The deck chosen by the player (immutable reference).
        deck (Deck): Working copy of the deck used during the game.
        hand (List[Card]): Cards currently in the player's hand.
        graveyard (List[Card]): Cards that have been played or discarded.
        status (Dict[str, Any]): Active status effects (e.g. poison, stunned, buffs).
                                Keys are status names, values are arbitrary data
                                (counters, expiration turns, etc.).
    """

    def __init__(
        self,
        username: str,
        request_sid: str,
        system_id: int,
        deck: Deck
    ) -> None:
        """
        Create a new Player instance.

        Args:
            username: Visible name of the player.
            request_sid: SocketIO session ID (obtained from ``request.sid`` in the controller).
            system_id: Unique persistent ID used across matches and in the database.
            deck: The Deck this player will use for the game.
        """
        self.username = username
        self.sid = request_sid
        self.system_id = system_id

        self.original_deck = deck
        self.deck: Deck = deepcopy(deck)

        self.hand: List[Card] = []
        self.graveyard: List[Card] = []

        # Status effects container — empty dict by default
        self.status: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    #                       Game state management                        #
    # ------------------------------------------------------------------ #

    def reset_for_new_game(self) -> None:
        """
        Reset the player's mutable game state for a new match.
        Keeps username, sid, system_id, and chosen deck.
        """
        self.hand.clear()
        self.graveyard.clear()
        self.deck = deepcopy(self.original_deck)
        self.status.clear()

    def get_state(self) -> Dict[str, Any]:
        """
        Return a serializable snapshot of the player's public state.
        Used by controllers to broadcast updates to clients.

        Returns:
            Dictionary containing only information that should be visible to others.
        """
        return {
            "username": self.username,
            "system_id": self.system_id,
            "sid": self.sid,
            "hand_size": len(self.hand),
            "deck_size": len(self.deck.cards),
            "graveyard_size": len(self.graveyard),
            "status": self.status,                    # visible status effects
        }

    # ------------------------------------------------------------------ #
    #                       Dunder methods                                #
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return f"<Player {self.username} (id={self.system_id}) sid={self.sid}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Player):
            return False
        return self.system_id == other.system_id

    def __hash__(self) -> int:
        return hash(self.system_id)