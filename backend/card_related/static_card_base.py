"""
card_related/static_card_base.py

Singleton registry that holds all card templates (master copies) in the game.

These are the immutable "blueprints" that decks are built from.
Every Card in a player's deck/hand/graveyard is a deep copy of one of these templates,
with a unique `uuid` assigned at runtime.

This is a pure Model component — loaded once at server start, shared globally.
"""

from typing import List, Optional

from card_related.card_driver import Card


class StaticCardBase:
    """
    Global singleton containing every card template used in the game.

    Cards registered here must be created with their final template values
    (name, id, desc, cost). The `uuid` field will always be a dummy value
    (UUID(int=0)) because real UUIDs are assigned only on instances inside decks.

    Usage:
        from card_related.static_card_base import StaticCardBase

        fire_slime = Card(name="Fire Slime", id=101, desc="Deals 2 damage on death.", cost=2)
        StaticCardBase.register(fire_slime)
    """

    _instance: Optional["StaticCardBase"] = None

    def __new__(cls) -> "StaticCardBase":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "initialized"):
            self.card_base: List[Card] = []
            self._by_name: dict[str, Card] = {}
            self._by_id: dict[int, Card] = {}
            self.initialized = True

    # ------------------------------------------------------------------ #
    #                         Registration                               #
    # ------------------------------------------------------------------ #

    def register(self, card: Card) -> None:
        """
        Register a card template into the global database.

        Args:
            card: Card instance with valid name, id, desc, cost.

        Raises:
            ValueError: If a card with the same name or id already exists.
        """
        if card.name in self._by_name:
            raise ValueError(f"Card with name '{card.name}' is already registered.")
        if card.id in self._by_id:
            raise ValueError(f"Card with id {card.id} is already registered.")

        # Store references
        self.card_base.append(card)
        self._by_name[card.name] = card
        self._by_id[card.id] = card

    def register_many(self, cards: List[Card]) -> None:
        """Register multiple card templates at once."""
        for card in cards:
            self.register(card)

    # ------------------------------------------------------------------ #
    #                           Lookup                                   #
    # ------------------------------------------------------------------ #

    @classmethod
    def instance(cls) -> "StaticCardBase":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_by_name(self, name: str) -> Optional[Card]:
        """Retrieve a card template by exact name (case-sensitive)."""
        return self._by_name.get(name)

    def get_by_id(self, card_id: int) -> Optional[Card]:
        """Retrieve a card template by its template id."""
        return self._by_id.get(card_id)

    def search(self, query: str) -> List[Card]:
        """
        Case-insensitive partial search by card name.

        Example: StaticCardBase.search("dragon") → all cards with "dragon" in name.
        """
        lower_query = query.lower()
        return [c for c in self.card_base if lower_query in c.name.lower()]

    # ------------------------------------------------------------------ #
    #                           Utility                                   #
    # ------------------------------------------------------------------ #

    def all_cards(self) -> List[Card]:
        """Return a copy of the full list of registered card templates."""
        return self.card_base[:]

    def clear(self) -> None:
        """Remove all cards. Only for unit tests."""
        self.card_base.clear()
        self._by_name.clear()
        self._by_id.clear()

    def __len__(self) -> int:
        return len(self.card_base)

    def __repr__(self) -> str:
        return f"<StaticCardBase cards={len(self.card_base)}>"