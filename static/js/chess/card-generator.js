class CardGenerator {
  /**
   * @param {Array} cardsData - Array of objects { title, text, img }
   */
  generateHandCards(cardsData) {
    // Target the specific hand area inside the player's row
    const playerArea = document.querySelector("#player-area .hand-area");
    const previewEl = document.getElementById("card-preview");

    playerArea.innerHTML = "";
    const count = cardsData.length;

    const totalFanAngle = (cardsData.length + 1) * 10;

    // Math for fan distribution
    const startAngle = count > 1 ? -(totalFanAngle / 2) : 0;
    const step = count > 1 ? totalFanAngle / (count - 1) : 0;

    cardsData.forEach((data, index) => {
      const rotation = startAngle + step * index;

      // Create the small fan card
      const cardDiv = document.createElement("div");
      // NOTE: Using 'hand-card' is fine, but you might want a player-specific class
      cardDiv.className = "card game-card friendly-card";
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = index;

      cardDiv.innerHTML = `
        ${
          data.img
            ? `<img src="${data.img}" class="friendly-card-img-top card-img-top">`
            : ""
        }
        <div class="card-body py-0">
          <h3 class="card-title fs-6 h-100 d-flex justify-content-center align-items-center text-center">${
            data.name
          }</h3>
        </div>
        
    `;

      // --- INTERACTION LOGIC ---
      cardDiv.addEventListener("mouseenter", () => {
        const description = this.#replaceCardTextSpecialCharacters(
          data.description
        );

        // Build the Large Card HTML
        previewEl.innerHTML = `
        ${
          data.img
            ? `<img src="${data.img}" class="preview-card-img-top card-img-top pt-3">`
            : ""
        }
        <div class="card-body">
          <h3 class="card-title">${data.name}</h3>
          <p class="card-text">${description || "No description available."}</p>
        </div>
      `;
        previewEl.classList.add("show");
      });

      cardDiv.addEventListener("mouseleave", () => {
        previewEl.classList.remove("show");
      });

      playerArea.appendChild(cardDiv);
    });
  }

  /**
   * Generates hidden enemy cards in an inverted fan shape.
   * @param {Number} count - The number of cards to display.
   */
  generateEnemyHandCards(count) {
    // Target the specific hand area inside the enemy's row
    const enemyArea = document.querySelector("#enemy-area .hand-area");

    // Create a placeholder array for iteration
    const cardsData = Array(count).fill({});

    const totalFanAngle = (count + 1) * 10;

    enemyArea.innerHTML = "";

    // Math for fan distribution
    const startAngle = count > 1 ? -(totalFanAngle / 2) : 0;
    const step = count > 1 ? totalFanAngle / (count - 1) : 0;

    cardsData.forEach((_, index) => {
      const rotation = startAngle + step * index;

      // Create the hidden card element
      const cardDiv = document.createElement("div");
      // NOTE: Using 'enemy-card' is fine, but you might want a specific class
      cardDiv.className = "game-card enemy-card";
      cardDiv.style.setProperty("--rot", `${rotation}deg`);
      cardDiv.style.zIndex = index;

      // No content needed, as they are hidden card backs

      enemyArea.appendChild(cardDiv);
    });
  }

  /**
   * Replace special characters in text into respective formats
   * @param {Number} text - The text to be modified.
   */
  #replaceCardTextSpecialCharacters(text) {
    // Replace [LINEBREAK] into <br>
    var linebreak_replaced_text = _.replace(text, "[LINEBREAK]", "<br>");

    // Replace *Word* into <strong>Word</strong>
    function boldAsterisks(text) {
      return text.replace(/\*(.+?)\*/g, '<strong>$1</strong>');
    }
    var strong_font_replaced_text = boldAsterisks(linebreak_replaced_text);

    return strong_font_replaced_text;
  }
}

var CardGenerationHelper = new CardGenerator();
