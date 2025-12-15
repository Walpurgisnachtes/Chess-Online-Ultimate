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
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = index + this.cardZIndexLevel;

      cardDiv.innerHTML = `
        <div class="card-cost-badge">${data.cost}</div>
        ${
          data.img
            ? `<img src="${data.img}" class="friendly-card-img-top card-img-top" loading="lazy">`
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
          <img id="previewImg" src="${data.img}" class="in-game-preview-card-img-top card-img-top">
          <div class="card-body">
            <h3 id="previewName" class="card-title">${data.name}</h3>
            <p id="previewDesc" class="card-text">${description}</p>
        </div>
      `;

      this.#previewCache.set(index, previewHTML);

      // ────── HOVER LOGIC (now super cheap) ──────
      cardDiv.addEventListener("mouseenter", () => {
        previewEl.innerHTML = this.#previewCache.get(index); // cached string → no new img requests
        previewEl.classList.add("show");
      });

      cardDiv.addEventListener("mouseleave", () => {
        previewEl.classList.remove("show");
      });

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
