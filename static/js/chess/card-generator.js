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

    if (!playerArea) playerArea.innerHTML = "";
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

  makeCardDraggable(cardEl) {
    const offsetParent = cardEl.offsetParent || document.body;
    const boardEl = document.querySelector("#game-board");

    const getParentRect = () => offsetParent.getBoundingClientRect();

    const getCardPosition = () => {
      const cardRect = cardEl.getBoundingClientRect();
      const parentRect = getParentRect();
      return {
        left: cardRect.left - parentRect.left + offsetParent.scrollLeft,
        top: cardRect.top - parentRect.top + offsetParent.scrollTop,
      };
    };

    let origin = getCardPosition();
    let originZIndex = "0";
    let pointerStart = { x: 0, y: 0 };
    let dragging = false;

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

    const onPointerMove = (event) => {
      if (!dragging) return;

      // const dx = event.clientX - pointerStart.x;
      // const dy = event.clientY - pointerStart.y;
      // console.log(`
      //   x: clientX: ${event.clientX} pageX: ${event.pageX} pointerStart.x: ${
      //   pointerStart.x
      // } dx: ${dx} finX:${origin.left + dx}
      //   y: clientY: ${event.clientY} pageY: ${event.pageY} pointerStart.y: ${
      //   pointerStart.y
      // } dy: ${dy} finY: ${origin.top + dy}`);

      // Hard code for my macBook
      if (window.innerWidth < 1200) {
        cardEl.style.left = `${event.clientX - 100}px`;
        cardEl.style.top = `${event.clientY - window.innerHeight}px`;
      } else {
        cardEl.style.left = `${event.clientX - 250}px`;
        cardEl.style.top = `${event.clientY - window.innerHeight + 200}px`;
      }
    };

    const onPointerUp = (event) => {
      if (!dragging) return;

      dragging = false;
      cardEl.releasePointerCapture(event.pointerId);
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
      cardEl.style.cursor = "";

      cardEl.style.left = ``;
      cardEl.style.top = ``;
      cardEl.style.transformOrigin = "";
      cardEl.style.transform = "";
      cardEl.style.zIndex = originZIndex;

      if (overlapWithBoard()) {
        window.dispatchEvent(
          new CustomEvent("playCard", {
            detail: {
              cardIdInHand: cardEl.dataset.cardIdInHand,
            },
          })
        );
      } else {
        // Snap back with a quick transition

        const handleReset = () => {
          cardEl.style.transition = "";
          cardEl.removeEventListener("transitionend", handleReset);
        };
        cardEl.addEventListener("transitionend", handleReset);
      }
    };

    cardEl.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      dragging = true;

      origin = getCardPosition();
      originZIndex = cardEl.style.zIndex;
      pointerStart = { x: event.clientX, y: event.clientY };

      cardEl.style.touchAction = "none";
      cardEl.style.cursor = "grabbing";

      cardEl.style.left = `${origin.left}px`;
      cardEl.style.top = `${origin.top}px`;
      cardEl.style.transformOrigin = "unset";
      cardEl.style.transform = "none";
      cardEl.style.zIndex = "200";

      cardEl.setPointerCapture(event.pointerId);
      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
    });
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
