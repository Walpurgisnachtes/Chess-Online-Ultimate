"""
card_driver.py - Advanced card deck utilities with status tracking and observation mechanics

This module implements core deck and card logic commonly needed in digital card games
(Magic: The Gathering Arena, Hearthstone, Yu-Gi-Oh! Master Duel, etc.). Key features:

- Unique card instances via UUIDs (multiple copies of the same template stay distinct)
- Lightweight status/effect tracking on both cards and the deck itself
- "Observe / look at top N" with automatic anti-cheat shuffle on next draw
- Safe random insertion ("shuffle into deck") and specific card draw mechanics
"""

from __future__ import annotations

from typing import List, Callable, Optional
from random import shuffle, randrange, sample
from copy import deepcopy
from uuid import UUID, uuid4


class StatusControllable:
    """
    Mixin-style base class providing simple string-based status tracking.

    Statuses are useful for temporary flags such as "tapped", "observed", "summoning-sick",
    "revealed", etc.
    """

    def __init__(self) -> None:
        self.status: List[str] = []

    def append_status(self, status: str) -> List[str]:
        """Add a status if not already present. Returns the current status list."""
        if status not in self.status:
            self.status.append(status)
        return self.status

    def has_status(self, status: str = "") -> bool:
        """Return True if the object has the given status."""
        return status in self.status

    def remove_status(self, status: str = "") -> List[str]:
        """
        Remove a status if present.

        Returns:
            A copy of the status list before removal.
        """
        previous = deepcopy(self.status)
        if status in self.status:
            self.status.remove(status)
        return previous

    def clear_status(self) -> List[str]:
        """Clear all statuses and return the previous list."""
        previous = deepcopy(self.status)
        self.status.clear()
        return previous


class Card(StatusControllable):
    """
    A single card instance.

    (template + runtime data).

    The template data (name, id, desc, cost) is shared among all copies.
    Each actual object in play gets its own UUID so it can be tracked individually.
    """

    def __init__(self, name: str, id: int, desc: str, cost: int) -> None:
        super().__init__()
        self.name: str = name
        self.id: int = id              # template identifier
        self.uuid: UUID = UUID(int=0)  # overwritten when added to a deck
        self.desc: str = desc
        self.cost: int = cost

    def __repr__(self) -> str:
        return f"<Card {self.name!r} (id={self.id}) uuid={self.uuid}>"

    def __hash__(self) -> int:
        return hash(self.uuid)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.uuid == other.uuid


class Deck(StatusControllable):
    """
    Advanced deck implementation with many digital-card-game conveniences.

    Features
    --------
    - UUID-tracked card instances
    - Status flags on both deck and cards
    - "Observe top N" → automatic shuffle on next real draw (prevents repeated peeking)
    - Random insertion ("shuffle X into your deck")
    - Specific card draw (e.g., tutor effects that put a known card into hand)
    """

    def __init__(self, cards: List[Card]) -> None:
        """
        Create a deck from a list of card templates.

        Each template is deep-copied, given a fresh UUID, and marked with the
        ``"added_into_deck"`` status.
        """
        super().__init__()
        self.deck_cards: List[Card] = []
        for card in cards:
            self.add(card)

    # ------------------------------------------------------------------ #
    # Basic manipulation
    # ------------------------------------------------------------------ #

    def add(self, card: Card, idx: Optional[int] = None) -> None:
        """
        Insert a deep copy of *card* into the deck.

        Args:
            card: Card template to add.
            idx: Position (0 = top, None = bottom). Defaults to bottom.
        """
        new_card = deepcopy(card)
        new_card.uuid = uuid4()
        new_card.append_status("added_into_deck")

        if idx is None:
            self.deck_cards.append(new_card)
        else:
            self.deck_cards.insert(idx, new_card)

    def shuffle(self) -> None:
        """Shuffle the deck in-place and update relevant statuses."""
        self.append_status("shuffled")
        for c in self.deck_cards:
            c.remove_status("observed")
        shuffle(self.deck_cards)

    def add_into_deck(self, cards: List[Card]) -> None:
        """Randomly scatter cards throughout the deck (no final shuffle)."""
        for card in cards:
            pos = randrange(len(self.deck_cards) + 1)  # +1 allows bottom placement
            self.add(card, pos)

    def shuffle_into_deck(self, cards: List[Card]) -> None:
        """Randomly insert cards and then shuffle the whole deck."""
        self.add_into_deck(cards)
        self.shuffle()

    def remove(self, uuids: List[UUID]) -> None:
        """Remove cards identified by UUID. Removed cards get "removed_from_deck" status."""
        for uuid in uuids:
            card = next((c for c in self.deck_cards if c.uuid == uuid), None)
            if card:
                card.append_status("removed_from_deck")
                self.deck_cards.remove(card)

    # ------------------------------------------------------------------ #
    # Drawing & previewing
    # ------------------------------------------------------------------ #

    def pre_draw(self, num: int = 1) -> List[Card]:
        """Return the top *num* cards without altering the deck or applying statuses."""
        n = min(num, len(self.deck_cards))
        return [self.deck_cards[-i-1] for i in range(n)]

    def draw(self, num: int = 1) -> List[Card]:
        """
        Draw *num* cards from the top.

        If the deck was previously observed (has "observed" status), it is shuffled
        once and the flag cleared before drawing — preventing repeated peeking exploits.
        """
        if self.has_status("observed"):
            self.shuffle()
            self.remove_status("observed")

        drawn = self.pre_draw(num)
        uuids_to_remove: List[UUID] = []
        for card in drawn:
            card.append_status("drawn_from_deck")
            uuids_to_remove.append(card.uuid)

        self.remove(uuids_to_remove)
        return drawn

    def draw_specific(self, cards: List[Card]) -> List[Card]:
        """
        Draw specific card instances that are already known to be in the deck
        (e.g., tutor effects, "search your deck for a card and put it into your hand").

        The deck is shuffled first if it has the "observed" status (same anti-cheat rule).
        The provided card objects **must** be the exact instances currently in the deck.

        Args:
            cards: List of Card objects currently inside this deck.

        Returns:
            The same list (for convenience/chaining).
        """
        if self.has_status("observed"):
            self.shuffle()
            self.remove_status("observed")

        uuids_to_remove: List[UUID] = []
        for card in cards:
            if card in self.deck_cards:  # sanity check
                card.append_status("drawn_from_deck")
                uuids_to_remove.append(card.uuid)

        self.remove(uuids_to_remove)
        return cards

    def draw_5(self) -> List[Card]:
        """Convenience alias for drawing exactly five cards (mulligan / starting hand).
        """
        return self.draw(5)

    # ------------------------------------------------------------------ #
    # Observation / scouting
    # ------------------------------------------------------------------ #

    def observe(self, num: int, predicate: Optional[Callable[[Card], bool]] = None) -> List[Card]:
        """
        Look at the top *num* cards (or *num* cards matching *predicate*).

        The deck receives the "observed" status; the next real draw will force a shuffle.
        Observed cards receive the "observed" status.

        Behaviour when using a predicate:
            - Scans from the top down, collect cards that satisfy the predicate
            - if fewer than *num* matches exist, randomly duplicate already-found cards
              until the requested count is reached (mirrors certain game behaviours).

        Returns:
            List of observed Card references (not copies).
        """
        self.append_status("observed")

        if predicate is None:
            observed = self.pre_draw(num)
        else:
            observed: List[Card] = []
            i = 0
            while len(observed) < num and i < len(self.deck_cards):
                card = self.deck_cards[-i-1]  # top-down
                if predicate(card):
                    observed.append(card)
                i += 1

            # Duplicate randomly if we didn't find enough
            while len(observed) > 0 and len(observed) < num:
                observed.append(sample(observed, 1)[0])

        for card in observed:
            card.append_status("observed")

        return observed