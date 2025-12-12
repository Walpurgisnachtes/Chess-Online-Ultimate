// Reuse DeckBuilder logic to load and display decks
class LobbyDeckSelector {
  constructor() {
    this.myDecks = [];
    this.selectedDeckName = null;
    this.selectedDeckIndex = null;
    this.isAnyDeckActive = false;
  }

  async loadAndShowDecks() {
    try {
      const deckLoader = new DeckLoader();
      await deckLoader.loadDecks();
      this.myDecks = deckLoader.decks;

      this.renderDeckList();
      this.renderSelectActiveDeckBtn();
    } catch (err) {
      document.getElementById("deckSelectionList").innerHTML = `
        <div class="col-12 text-center text-danger">
          <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
          <p>Failed to load decks</p>
        </div>
      `;
      console.error(err);
    }
  }

  renderDeckList() {
    const container = document.getElementById("deckSelectionList");

    if (this.myDecks.length === 0) {
      container.innerHTML = `
        <div class="card game-card deck-nav-card text-center py-5 mx-5 position-relative">
          <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
          <p class="text-muted">No decks found</p>
          <a href="/deckbuilder" class="btn btn-outline-primary mt-3">
            <i class="fas fa-plus me-2"></i>Create Your First Deck
          </a>
        </div>
      `;
      document.getElementById("confirmSelectDeck").disabled = true;
      return;
    }

    container.innerHTML = "";
    this.myDecks.forEach((deck, index) => {
      const cardCount = deck.deck?.length || 0;
      const isActive = deck.active === "true";
      if (isActive) {
        this.isAnyDeckActive = true;
        this.selectedDeckName = deck.name;
      }

      const div = document.createElement("div");
      div.className = `card game-card ${
        cardCount == 20 ? "deck-select-card" : ""
      } deck-nav-card text-center py-5 mx-5 position-relative border ${
        isActive ? "border-primary shadow" : "border-light"
      }`;
      div.dataset.deckIndex = index;
      div.innerHTML = `
          <div class="card-body text-center py-4">
            <i class="fas fa-scroll fa-3x mb-3 ${
              isActive ? "text-primary" : "text-muted"
            }"></i>
            <h6 class="card-title mb-2">${deck.name || "Untitled Deck"}</h6>
            ${
              cardCount < 20
                ? '<small class="text-warning">Not enough cards</small>'
                : ""
            }
          </div>
      `;
      if (cardCount == 20) {
        div.addEventListener("click", async () => {
          this.selectedDeckIndex = index;
          await this.setActiveDeck();
        });
      }
      container.appendChild(div);
    });
  }

  renderSelectActiveDeckBtn() {
    const selectActiveDeckBtn = document.getElementById("select-active-deck-btn");
    const deckTitle = selectActiveDeckBtn.querySelector(".card-title");
    if (this.isAnyDeckActive) {
      deckTitle.innerHTML = `${this.selectedDeckName}`;
    }
  }

  async setActiveDeck() {
    const currentActiveElement = document.activeElement;
    currentActiveElement.blur();
    bootstrap.Modal.getInstance(
      document.getElementById("selectDeckModal")
    ).hide();
    try {
      const res = await fetch("/api/set_active_deck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: this.selectedDeckIndex,
        }),
      });
      const result = await res.json();
      if (result.success) {
        await modal.messageOnly("Set active deck success!");
      } else {
        await modal.error(
          `Set active deck failed!<br/>Reason: ${result.error}`
        );
      }
    } catch (err) {
      await modal.error("Save failed");
      console.error(err);
    }
  }
}

$(document).ready(async function () {
  const socket = io();

  // Initialize selector
  const deckSelector = new LobbyDeckSelector();
  await deckSelector.loadAndShowDecks();

  // Open modal → load decks
  document
    .getElementById("selectDeckModal")
    .addEventListener("show.bs.modal", () => {
      deckSelector.loadAndShowDecks();
    });

  document.getElementById("confirmCreateRoom").addEventListener("click", () => {
    const roomName = document.getElementById("roomNameInput").value.trim();
    const skill = document.getElementById("skillInput").value;

    if (!roomName) {
      alert("Please enter a room name!");
      return;
    }

    // Redirect to chess room
    window.location.href = `/chess/${encodeURIComponent(
      roomName
    )}?skill=${skill}`;
  });

  socket.on("connect", () => {
    console.log("Connected to server");
    // You can emit 'request_rooms' here if you implement live lobby
  });
});
