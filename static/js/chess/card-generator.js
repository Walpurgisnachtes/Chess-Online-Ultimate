/**
 * CardGenerator – responsible for rendering player and enemy hands
 * with a smooth fan layout and a non-spammy card preview.
 */
class CardGenerator {
  /**
   * @private
   * @type {Map<number, string>} Cache of full preview HTML strings keyed by card index
   */
  #previewCache = new Map();

  cardZIndexLevel = 100;

  /**
   * Generates the player's hand in a fan shape and pre-builds preview HTML.
   * @param {Array<{name:string, description:string, img:string}>} cardsData
   */
  generateHandCards(cardsData) {
    const playerArea = document.querySelector("#player-area .hand-area");
    const previewEl = document.getElementById("in-game-preview-card");

    if (!playerArea) return;
    playerArea.innerHTML = "";
    this.#previewCache.clear();

    const count = cardsData.length;
    const totalFanAngle = (count + 1) * 10;
    const startAngle = count > 1 ? -(totalFanAngle / 2) : 0;
    const step = count > 1 ? totalFanAngle / (count - 1) : 0;

    cardsData.forEach((data, index) => {
      const rotation = startAngle + step * index;

      // Create small hand card
      const cardDiv = document.createElement("div");
      cardDiv.className = "card game-card friendly-card";
      cardDiv.dataset.cardType = data.type;
      cardDiv.dataset.cardIdInHand = index;
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = index + this.cardZIndexLevel;

      cardDiv.innerHTML = `
        <div class="card-cost-badge">${data.cost}</div>
        ${
          data.img
            ? `<img src="${data.img}" class="friendly-card-img-top card-img-top" loading="lazy" draggable="false">`
            : ""
        }
        <div class="card-body py-0">
          <h3 class="card-title h-100 d-flex justify-content-center align-items-center text-center text-dark">
            ${data.name}
          </h3>
        </div>
      `;

      // ────── PRE-BUILD PREVIEW HTML ONCE ──────
      const description = this.replaceCardTextSpecialCharacters(
        data.description || ""
      );

      const previewHTML = `
        <div id="previewCostBadge" class="card-cost-badge">${data.cost}</div>
          <img id="previewImg" src="${data.img}" class="in-game-preview-card-img-top card-img-top" draggable="false">
          <div class="card-body">
            <h3 id="previewName" class="card-title">${data.name}</h3>
            <p id="previewDesc" class="card-text">${description}</p>
        </div>
      `;

      this.#previewCache.set(index, previewHTML);

      // ────── HOVER LOGIC (now super cheap) ──────
      cardDiv.addEventListener("mouseenter", () => {
        previewEl.dataset.cardType = data.type;
        previewEl.innerHTML = this.#previewCache.get(index); // cached string → no new img requests
        previewEl.classList.add("show");
      });

      cardDiv.addEventListener("mouseleave", () => {
        previewEl.classList.remove("show");
      });

      this.makeCardDraggable(cardDiv);

      playerArea?.appendChild(cardDiv);
    });
  }

  /**
   * Generates hidden enemy cards (card backs) in an inverted fan.
   * @param {number} count
   */
  generateEnemyHandCards(count) {
    const enemyArea = document.querySelector("#enemy-area .hand-area");
    if (!enemyArea) return;

    enemyArea.innerHTML = "";
    const totalFanAngle = (count + 1) * 10;
    const startAngle = count > 1 ? -(totalFanAngle / 2) : 0;
    const step = count > 1 ? totalFanAngle / (count - 1) : 0;

    for (let i = 0; i < count; i++) {
      const rotation = startAngle + step * i;
      const cardDiv = document.createElement("div");
      cardDiv.className = "game-card enemy-card";
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = i + this.cardZIndexLevel;
      enemyArea.appendChild(cardDiv);
    }
  }

  /**
   * Makes a card element draggable across all screen sizes.
   *
   * It uses touch and mouse events and calculates movement based on the
   * viewport coordinates (clientX/clientY) and the element's current
   * position/size.
   *
   * @param {HTMLElement} cardEl The card element to make draggable (assumed position: absolute).
   */
  makeCardDraggable(cardEl) {
    // Stores the initial offset (x, y) from the mouse/touch point
    // to the top-left corner of the card when dragging starts.
    let offsetX, offsetY;
    const boardEl = document.querySelector("#chessboard-core");
    // Stores the original z-index of the card before dragging.
    let originZ = cardEl.style.zIndex || this.cardZIndexLevel;

    const overlapWithBoard = () => {
      const boardRect = boardEl.getBoundingClientRect();
      const cardRect = cardEl.getBoundingClientRect();
      return !(
        cardRect.right < boardRect.left ||
        cardRect.left > boardRect.right ||
        cardRect.bottom < boardRect.top ||
        cardRect.top > boardRect.bottom
      );
    };

    // --- Event Listeners and Setup ---

    // 1. Unified Event Listener for both MouseDown and TouchStart
    // This function runs when the drag operation officially begins.
    const onDragStart = (e) => {
      // Prevent default behavior to avoid issues like image dragging or text selection
      e.preventDefault();

      // Get the coordinate source (handles both MouseEvent and TouchEvent)
      const clientX = e.clientX || e.touches[0].clientX;
      const clientY = e.clientY || e.touches[0].clientY;

      // Ensure the element has its initial position properties set
      // if they are not already. We will use getBoundingClientRect()
      // for the most accurate current position relative to the viewport.
      const rect = cardEl.getBoundingClientRect();

      // 🚨 IMPORTANT: Calculate the offset from the click point to the card's top-left.
      // This is crucial to prevent the card from "jumping" when the drag starts.
      offsetX = clientX - rect.left;
      offsetY = clientY - rect.top;

      // 2. Start the Drag State

      // Apply dragging styles as per requirements:
      cardEl.style.zIndex = this.cardZIndexLevel * 2;
      cardEl.style.transformOrigin = "none";

      // 🚨 CRITICAL CONVERSION:
      // If the card was positioned using `transform` before the drag (e.g., for centering),
      // we must calculate its absolute `left`/`top` equivalent *before* setting the drag state.
      // We use its current *viewport* position (rect.left/top) and subtract
      // the parent's position to get the final px values.

      // Get the parent's bounding box for accurate offset calculation.
      const parentRect = cardEl.parentElement.getBoundingClientRect();

      // Set initial left/top based on its current visual position.
      // This effectively "locks" its current position into the `left`/`top` properties.
      const newLeft = rect.left - parentRect.left;
      const newTop = rect.top - parentRect.top;

      cardEl.style.left = `${newLeft}px`;
      cardEl.style.top = `${newTop}px`;

      // Clear any potentially conflicting transform applied before the drag
      cardEl.style.transform = "unset";

      // 3. Attach Move and End Handlers to the document/window
      // Attaching to the window ensures the drag continues even if the cursor
      // leaves the card element itself (e.g., fast movement).
      window.addEventListener("mousemove", onDragMove, { passive: true });
      window.addEventListener("touchmove", onDragMove, { passive: false }); // Needs to be non-passive for e.preventDefault()
      window.addEventListener("mouseup", onDragEnd);
      window.addEventListener("touchend", onDragEnd);
    };

    // 4. Drag Move Handler
    const onDragMove = (e) => {
      // Get the coordinate source
      const clientX = e.clientX || e.touches[0].clientX;
      const clientY = e.clientY || e.touches[0].clientY;

      // Get the parent's bounding box for accurate relative positioning
      const parentRect = cardEl.parentElement.getBoundingClientRect();

      // Calculate the new position relative to the parent, compensating for the
      // initial offset (offsetX/offsetY).
      const newLeft = clientX - parentRect.left - offsetX;
      const newTop = clientY - parentRect.top - offsetY;

      // Apply movement as per requirements:
      cardEl.style.left = `${newLeft}px`;
      cardEl.style.top = `${newTop}px`;
    };

    // 5. Drag End Handler
    const onDragEnd = () => {
      // Reset everything as per requirements:
      if (overlapWithBoard()) {
        window.dispatchEvent(
          new CustomEvent("playCard", {
            detail: {
              cardIdInHand: cardEl.dataset.cardIdInHand,
            },
          })
        );
      }
      cardEl.style.left = ``;
      cardEl.style.top = ``;
      cardEl.style.zIndex = originZ;
      cardEl.style.transformOrigin = "";
      cardEl.style.transform = ""; // Resetting transform is standard practice

      // Remove the move and end handlers from the window
      window.removeEventListener("mousemove", onDragMove);
      window.removeEventListener("touchmove", onDragMove);
      window.removeEventListener("mouseup", onDragEnd);
      window.removeEventListener("touchend", onDragEnd);
    };

    // --- Initial Event Listener Assignment ---
    cardEl.addEventListener("mousedown", onDragStart);
    cardEl.addEventListener("touchstart", onDragStart, { passive: false });
  }

  /**
   * Replaces special tokens in card description.
   * @param {string} text
   * @returns {string}
   */
  replaceCardTextSpecialCharacters(text) {
    if (!text) return "";
    let result = text.replace(/\[LINEBREAK\]/g, "<br>");
    result = result.replace(/\*(.+?)\*/g, "<strong>$1</strong>");
    return result;
  }
}

// Global singleton
var CardGenerationHelper = new CardGenerator();
