// static/js/deckbuilder.js
class DeckBuilder {
  constructor() {
    this.allCards = [];
    this.myDecks = [];
    this.currentDeckId = null;
    this.currentDeckName = null;
    this.currentDeckCardIDs = [];
    this.currentDeckCards = [];

    this.isPreviewOpen = false; // Track preview state

    this.init();
  }

  async init() {
    await this.loadDecks();
    this.bindEvents();
    this.bindGlobalClick();
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
      <div class="col-md-6 col-lg-4 card game-card deck-nav-card new-deck-btn text-center py-5 mx-5 position-relative" data-action="new">
        <i class="fas fa-plus fa-4x text-muted mb-3"></i>
        <h5>New Deck</h5>
      </div>
    `;

    _.forEach(this.myDecks, (deck, idx) => {
      const el = document.createElement("div");
      el.className =
        "col-md-6 col-lg-4 card game-card deck-nav-card text-center py-5 mx-5 position-relative";
      el.dataset.deckIndex = idx;
      el.innerHTML = `
        <div class="text-center">
          <i class="fas fa-scroll fa-4x text-primary mb-3"></i>
          <h5>${deck.name || "Untitled Deck"}</h5>
          <small class="text-muted">${deck.deck?.length || 0} cards</small>
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
    document.getElementById("deleteDeckBtn").onclick = () => this.deleteDeck();
    document
      .getElementById("searchInput")
      .addEventListener("input", () => this.renderCollection());
  }

  bindGlobalClick() {
    document.addEventListener("click", (e) => {
      // Close preview if preview is open and click is outside → close it
      if (this.isPreviewOpen && !e.target.closest("#largePreview")) {
        this.hidePreview();
      }

      // Block card adding when preview is open (extra safety)
      if (this.isPreviewOpen && e.target.closest(".collection-card")) {
        e.stopPropagation();
        e.preventDefault();
      }
    });

    // Don't close preview when clicking inside it
    document.getElementById("largePreview")?.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }

  createNewDeck() {
    this.currentDeckId = null;
    this.currentDeckCards = [];
    this.currentDeckCardIDs = [];
    document.getElementById("deckNameDisplay").textContent = "New Deck";
    document.getElementById("deleteDeckBtn").classList.add("visually-hidden");
    this.loadCardCollection();
    this.switchLayer("layer-builder");
  }

  openDeck(index) {
    const deck = this.myDecks[index];
    this.currentDeckId = index;
    this.currentDeckName = deck.name;
    this.currentDeckCardIDs = deck.deck ? [...deck.deck] : [];
    document.getElementById("deckNameDisplay").textContent =
      deck.name || "Untitled Deck";
    document
      .getElementById("deleteDeckBtn")
      .classList.remove("visually-hidden");
    this.loadCardCollection();
    this.switchLayer("layer-builder");
  }

  async loadCardCollection() {
    try {
      const res = await fetch("/api/localization/en/cards");
      const data = await res.json();
      this.allCards = Object.values(data);
      this.renderCollection();
      this.formatCurrentDeck();
      this.renderCurrentDeck();
    } catch (err) {
      console.error(err);
    }
  }

  formatCurrentDeck() {
    this.currentDeckCards = [];
    let cardCache = {
      id: "",
      card: null,
    };
    _.forEach(this.currentDeckCardIDs, (id) => {
      let card = null;
      if (cardCache.id === id) {
        card = cardCache.card;
      } else {
        card = _.find(this.allCards, (c) => c.id === id);
        cardCache.id = id;
        cardCache.card = card;
      }

      this.currentDeckCards.push(card);
    });
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
        div.dataset.cardType = card.type;
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

        // Left click: add to deck
        div.onclick = (e) => {
          e.preventDefault(); // Prevent right-click context menu interference
          if (this.isPreviewOpen) return;
          this.addCardToDeck(card);
        };

        // Right click: show preview
        div.oncontextmenu = (e) => {
          e.preventDefault();
          this.showPreview(card);
          return false;
        };

        container.appendChild(div);
      });
  }

  renderDeckBuilderAlert(message) {
    errorToastManager.showError(message);
  }

  addCardToDeck(card) {
    // If preview is open → do NOTHING on left click
    if (this.isPreviewOpen) {
      return;
    }
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
      const index = this.currentDeckCards.indexOf(card);

      const div = document.createElement("div");
      div.className = "deck-card pb-2 row";
      div.innerHTML = `
        <div class="card deck-card-minimize bg-light text-dark col">
          <div class="card-cost-badge">${card.cost}</div>
          <div class="card-body py-2 ps-5 text-left">
            <h6 class="mb-0">${card.name}</h6>
          </div>
          <span class="count-badge" data-card-type="${card.type}">${count}</span>
        </div>
        <button class="remove-btn col d-flex justify-content-center" data-index="${index}">×</button>
      `;

      div.querySelector(".remove-btn").onclick = (e) => {
        e.stopPropagation();
        this.removeCardFromDeck(index);
      };

      // Right-click on deck card → show preview
      div.querySelector(".deck-card-minimize").oncontextmenu = (e) => {
        e.preventDefault();
        this.showPreview(card);
        return false;
      };

      container.appendChild(div);
    });

    document.getElementById(
      "deckCount"
    ).textContent = `${this.currentDeckCards.length} / 20`;
    document.getElementById("saveDeckBtn").disabled =
      this.currentDeckCards.length === 0;
  }

  showPreview(card) {
    const previewCard = document.getElementById("largePreview");
    const description = CardGenerationHelper.replaceCardTextSpecialCharacters(
      card.description || ""
    );

    previewCard.querySelector("#previewImg").src = card.img || "";
    previewCard.querySelector("#previewName").textContent = card.name;
    previewCard.querySelector("#previewCostBadge").textContent = card.cost;
    previewCard.querySelector("#previewDesc").innerHTML =
      description || "No description.";

    previewCard
      .querySelector("#deck-builder-preview-card")
      .classList.add("show");

    previewCard.querySelector("#deck-builder-preview-card").dataset.cardType =
      card.type;

    this.isPreviewOpen = true;
  }

  hidePreview() {
    const previewCard = document.getElementById("largePreview");
    previewCard
      .querySelector("#deck-builder-preview-card")
      .classList.remove("show");
    this.isPreviewOpen = false;
  }

  switchLayer(id) {
    document
      .querySelectorAll(".layer")
      .forEach((l) => l.classList.remove("active"));
    document.getElementById(id).classList.add("active");
  }

  async saveDeck() {
    var deckName = "";
    if (this.currentDeckId) {
      deckName = this.currentDeckName;
    } else {
      deckName = await modal.enterData("Enter deck name:", "Enter Deck Name");
    }

    const deckData = {
      id: this.currentDeckId ?? this.myDecks.length,
      name: deckName,
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
        this.myDecks = result.decks;
        this.switchLayer("layer-decknav");
        this.renderDeckList();
      }
    } catch (err) {
      await modal.error("Save failed");
      console.error(err);
    }
  }

  async deleteDeck() {
    if (this.currentDeckId === null) {
      await modal.error("No deck selected.");
      return;
    }

    const deck = this.myDecks[this.currentDeckId];
    const deckName = deck.name || "Untitled Deck";

    const confirmed = await modal.confirm(
      `<strong>Delete deck "${deckName}"?</strong><br><br>
     <small>This deck will be lost forever.</small><br>
     This action cannot be undone.`,
      "Delete Deck?",
      "Delete",
      true // danger mode
    );

    if (!confirmed) return;

    try {
      const res = await fetch("/api/delete_deck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: this.currentDeckId }),
      });

      const result = await res.json();

      if (result.success) {
        this.myDecks = result.decks;
        this.switchLayer("layer-decknav");
        this.renderDeckList();
      } else {
        await modal.error(
          "Failed to delete: " + (result.error || "Server error")
        );
      }
    } catch (err) {
      console.error(err);
      await modal.error("Network error. Could not delete deck.");
    }
  }
}

// Start when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.deckBuilder = new DeckBuilder();
});
