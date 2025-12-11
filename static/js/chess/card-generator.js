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

  /**
   * Generates the player's hand in a fan shape and pre-builds preview HTML.
   * @param {Array<{name:string, description:string, img:string}>} cardsData
   */
  generateHandCards(cardsData) {
    const playerArea = document.querySelector("#player-area .hand-area");
    const previewEl = document.getElementById("card-preview");

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
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = index;

      cardDiv.innerHTML = `
        ${data.img ? `<img src="${data.img}" class="friendly-card-img-top card-img-top" loading="lazy">` : ""}
        <div class="card-body py-0">
          <h3 class="card-title fs-6 h-100 d-flex justify-content-center align-items-center text-center">
            ${data.name}
          </h3>
        </div>
      `;

      // ────── PRE-BUILD PREVIEW HTML ONCE ──────
      const description = this.#replaceCardTextSpecialCharacters(data.description || "");

      const previewHTML = `
        ${data.img ? `<img src="${data.img}" class="preview-card-img-top card-img-top pt-3" loading="lazy">` : ""}
        <div class="card-body">
          <h3 class="card-title">${data.name}</h3>
          <p class="card-text">${description || "No description available."}</p>
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
      cardDiv.style.zIndex = i;
      enemyArea.appendChild(cardDiv);
    }
  }

  /**
   * Replaces special tokens in card description.
   * @private
   * @param {string} text
   * @returns {string}
   */
  #replaceCardTextSpecialCharacters(text) {
    if (!text) return "";
    let result = text.replace(/\[LINEBREAK\]/g, "<br>");
    result = result.replace(/\*(.+?)\*/g, '<strong>$1</strong>');
    return result;
  }
}

// Global singleton
var CardGenerationHelper = new CardGenerator();