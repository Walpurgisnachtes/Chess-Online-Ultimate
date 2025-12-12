class DeckLoader {
  constructor() {
    this.decks = [];
  }

  async loadDecks() {
    try {
      const res = await fetch("/api/get_deck");
      this.decks = await res.json();
    } catch (err) {
      console.error(err);
    }
  }
}