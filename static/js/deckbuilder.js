// static/js/deckbuilder.js
class DeckBuilder {
  constructor() {
    this.allCards = [];
    this.myDecks = [];
    this.currentDeckId = null;
    this.currentDeckCards = [];

    this.init();
  }

  async init() {
    await this.loadDecks();
    this.bindEvents();
  }

  async loadDecks() {
    try {
      const res = await fetch("/api/get_deck");
      this.myDecks = await res.json();
      this.renderDeckList();
    } catch (err) {
      alert("Failed to load decks");
      console.error(err);
    }
  }

  renderDeckList() {
    const container = document.getElementById("deckList");
    container.innerHTML = `
      <div class="col-md-6 col-lg-4">
        <div class="card game-card deck-nav-card new-deck-btn text-center py-5" data-action="new">
          <i class="fas fa-plus fa-4x text-muted mb-3"></i>
          <h5>New Deck</h5>
        </div>
      </div>
    `;

    _.forEach(this.myDecks, (deck, idx) => {
      const el = document.createElement("div");
      el.className = "col-md-6 col-lg-4";
      el.innerHTML = `
        <div class="card game-card deck-nav-card text-center py-5" data-deck-index="${idx}">
          <div class="text-center">
            <i class="fas fa-scroll fa-4x text-primary mb-3"></i>
            <h5>${deck.name || "Untitled Deck"}</h5>
            <small class="text-muted">${deck.cards?.length || 0} cards</small>
          </div>
        </div>
      `;
      container.appendChild(el);
    });
  }

  bindEvents() {
    // New deck or open existing
    document.getElementById("deckList").addEventListener("click", (e) => {
      const card = e.target.closest(".deck-nav-card");
      if (!card) return;

      if (card.dataset.action === "new") {
        this.createNewDeck();
      } else {
        const idx = card.dataset.deckIndex;
        if (idx !== undefined) this.openDeck(parseInt(idx));
      }
    });

    document.getElementById("backBtn").onclick = () =>
      this.switchLayer("layer-decknav");
    document.getElementById("saveDeckBtn").onclick = () => this.saveDeck();
    document
      .getElementById("searchInput")
      .addEventListener("input", () => this.renderCollection());
  }

  createNewDeck() {
    this.currentDeckId = null;
    this.currentDeckCards = [];
    document.getElementById("deckNameDisplay").textContent = "New Deck";
    this.loadCardCollection();
    this.switchLayer("layer-builder");
  }

  openDeck(index) {
    const deck = this.myDecks[index];
    this.currentDeckId = index;
    this.currentDeckCards = deck.cards ? [...deck.cards] : [];
    document.getElementById("deckNameDisplay").textContent =
      deck.name || "Untitled Deck";
    this.loadCardCollection();
    this.switchLayer("layer-builder");
  }

  async loadCardCollection() {
    try {
      const res = await fetch("/api/localization/en/cards");
      const data = await res.json();
      this.allCards = Object.values(data);
      this.renderCollection();
      this.renderCurrentDeck();
    } catch (err) {
      console.error(err);
    }
  }

  renderCollection() {
    const container = document.getElementById("cardCollection");
    const query = document.getElementById("searchInput").value.toLowerCase();
    container.innerHTML = "";

    this.allCards
      .filter((card) => card.name.toLowerCase().includes(query))
      .forEach((card) => {
        const div = document.createElement("div");
        div.className = "card collection-card game-card position-relative";
        div.innerHTML = `
          <div class="card-cost-badge">${card.cost}</div>
          ${
            card.img
              ? `<img src="${card.img}" class="collection-card-img-top card-img-top" loading="lazy">`
              : ""
          }
          <div class="card-body p-2 d-flex align-items-center justify-content-center text-center">
            <h6 class="mb-1">${card.name}</h6>
          </div>
        `;
        div.onclick = () => this.addCardToDeck(card);
        div.onmouseenter = () => this.showPreview(card);
        div.onmouseleave = () => this.hidePreview();
        container.appendChild(div);
      });
  }

  renderDeckBuilderAlert(message) {
    errorToastManager.showError(message);
  }

  addCardToDeck(card) {
    // Reject if current deck contain 20 cards already
    if (this.currentDeckCards.length >= 20) {
      this.renderDeckBuilderAlert("Deck is full (20 cards max)");
      return;
    }
    // Reject if current deck contain 3 copies of this cards already
    if (_.filter(this.currentDeckCards, (c) => c.id == card.id).length >= 3) {
      this.renderDeckBuilderAlert(
        "Each deck may contain a maximum of 3 copies of any individual card."
      );
      return;
    }
    this.currentDeckCards.push(card);
    this.renderCurrentDeck();
  }

  removeCardFromDeck(index) {
    this.currentDeckCards.splice(index, 1);
    this.renderCurrentDeck();
  }

  renderCurrentDeck() {
    const container = document.getElementById("currentDeck");
    container.innerHTML = "";

    const countMap = {};
    this.currentDeckCards.forEach(
      (c) => (countMap[c.id] = (countMap[c.id] || 0) + 1)
    );

    // Show unique cards with count
    Object.keys(countMap).forEach((id) => {
      const card = this.currentDeckCards.find((c) => c.id == id);
      const count = countMap[id];

      const div = document.createElement("div");
      div.className = "deck-card pb-2 row";
      div.innerHTML = `
        <div class="card deck-card-minimize bg-light text-dark col">
          <div class="card-body p-2 text-center">
            <h6 class="mb-0">${card.name}</h6>
          </div>
          <span class="count-badge">${count}</span>
        </div>
        <button class="remove-btn col d-flex justify-content-center" data-index="${this.currentDeckCards.indexOf(
          card
        )}">×</button>
      `;
      div.querySelector(".remove-btn").onclick = (e) => {
        e.stopPropagation();
        this.removeCardFromDeck(parseInt(e.target.dataset.index));
      };
      div.querySelector(".deck-card-minimize").onmouseenter = () =>
        this.showPreview(card);
      div.querySelector(".deck-card-minimize").onmouseleave = () =>
        this.hidePreview();
      container.appendChild(div);
    });

    document.getElementById(
      "deckCount"
    ).textContent = `${this.currentDeckCards.length} / 20`;
    document.getElementById("saveDeckBtn").disabled =
      this.currentDeckCards.length === 0;
  }

  showPreview(card) {
    document.getElementById("previewImg").src = card.img || "";
    document.getElementById("previewName").textContent = card.name;
    document.getElementById("previewDesc").innerHTML =
      card.description || "No description.";
    document.getElementById("largePreview").style.display = "block";
  }

  hidePreview() {
    document.getElementById("largePreview").style.display = "none";
  }

  switchLayer(id) {
    document
      .querySelectorAll(".layer")
      .forEach((l) => l.classList.remove("active"));
    document.getElementById(id).classList.add("active");
  }

  async saveDeck() {
    const name = prompt(
      "Enter deck name:",
      document.getElementById("deckNameDisplay").textContent.trim()
    );
    if (!name) return;

    const deckData = {
      id: this.currentDeckId ?? this.myDecks.length,
      name: name,
      cards: this.currentDeckCards,
    };

    try {
      const res = await fetch("/api/save_deck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(deckData),
      });
      const result = await res.json();
      if (result.success) {
        alert("Deck saved successfully!");
        this.myDecks = result.decks;
        this.switchLayer("layer-decknav");
        this.renderDeckList();
      }
    } catch (err) {
      alert("Save failed");
      console.error(err);
    }
  }
}

// Start when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.deckBuilder = new DeckBuilder();
});
