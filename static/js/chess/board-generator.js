/**
 * ChessBoardGenerator
 *
 * Handles ALL chessboard-related DOM operations:
 * - Generates the 8x8 grid
 * - Renders pieces from a Chess.js game instance
 * - Updates the board after moves
 * - Provides utility methods for square selection/highlights
 *
 * Usage:
 *   BoardGenerationHelper.generateBoard();
 *   BoardGenerationHelper.render(game); // game = new Chess()
 *   BoardGenerationHelper.highlightSquare(row, col);
 */
class ChessBoardGenerator {
  constructor() {
    this.pieceNames = {
      p: "pawn",
      n: "knight",
      b: "bishop",
      r: "rook",
      q: "queen",
      k: "king",
    };
    this.promotion = null;
    this._modalEl = null;
    this.modal = null;

    // NEW: State for tracking the selected piece/square
    this._selectedSquare = null; // Stores algebraic notation (e.g., 'e2')
  }

  /**
   * Generate the empty 8x8 chessboard grid
   */
  generateChessBoard() {
    const board = document.querySelector(".chessboard");

    if (!board) {
      throw new Error(
        'Chessboard container not found. Make sure <div class="chessboard"></div> exists.'
      );
    }

    board.innerHTML = "";

    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const square = document.createElement("div");
        square.classList.add("square");
        square.classList.add((row + col) % 2 === 0 ? "light" : "dark");
        square.dataset.row = row;
        square.dataset.col = col;

        // Set algebraic notation for easy lookup/event handling
        square.dataset.square = this.coordsToAlgebraic(row, col);

        board.appendChild(square);
      }
    }
    // NEW: Attach the click listeners once the board is generated
    this.attachEventListeners();
  }

  /**
   * Attaches the click handler to all squares on the board.
   */
  attachEventListeners() {
    const squares = document.querySelectorAll(".chessboard .square");
    squares.forEach((square) => {
      // Bind the click handler to the class instance
      square.addEventListener("click", this.handleSquareClick.bind(this));
    });
  }

  /**
   * NEW: Handles clicks on the squares to manage piece selection and movement.
   * @param {MouseEvent} e - The click event
   */
  handleSquareClick(e) {
    const squareEl = e.currentTarget;
    const toSquare = squareEl.dataset.square;
    const hasPiece = squareEl.querySelector(".piece");

    if (this._selectedSquare) {
      // Case 1: A piece is already selected, this click is the destination ('to')
      const fromSquare = this._selectedSquare;

      // Remove selection highlight
      this.clearHighlights("selected");
      this._selectedSquare = null;
    } else if (hasPiece) {
      // Case 2: No piece selected, this click is the source ('from')
      this._selectedSquare = toSquare;

      // Highlight the selected square
      const { row, col } = this.algebraicToCoords(toSquare);
      this.highlightSquare(row, col, "selected");
    }
    // Case 3: No piece selected, and clicked on an empty square -> Do nothing
  }

  generatePromotionScreen(colorSide) {
    this._modalEl = document.getElementById("promotion-selection-modal");
    this.modal = new bootstrap.Modal(this._modalEl);
    const promotionModal = document.getElementById(
      "promotion-select-modal-body"
    );
    const promotablePieces = ["knight", "bishop", "rook", "queen"];
    _.forEach(promotablePieces, (typeName) => {
      const btn = document.createElement("button");
      btn.className = "card promotion-select-card btn";
      var formattedTypeName =
        typeName.charAt(0).toUpperCase() + typeName.slice(1);
      btn.innerHTML = `
        <img src="/static/img/piece/${typeName}_${colorSide}.png" class="card-img-top" loading="lazy" draggable="false">
        <div class="card-body py-0">
          <h6 class="card-title h-100 d-flex justify-content-center align-items-center text-center">
            ${formattedTypeName}
          </h6>
        </div>`;
      btn.addEventListener("click", () => {
        this.promotion = typeName;
        this.hide_promotion_screen();
      });
      promotionModal.appendChild(btn);
    });
  }

  show_promotion_screen() {
    this._modalEl.setAttribute("aria-modal", "true");
    this.modal.show();
  }

  show_select_piece_screen(squares) {
    _.forEach(squares, (sq) => {
      const { row, col } = this.algebraicToCoords(sq);
      const sqEl = this.getSquareEl(row, col);
      sqEl.classList.add("select-screen-choosable");
    });

    const selectScreen = document.getElementById("select-piece-screen");
    if (selectScreen) {
      selectScreen.classList.remove("opacity-hidden");
    }

    window["blockDragging"] = true;
  }

  hide_select_piece_screen() {
    this.clearHighlights("selected");
    this.clearHighlights("select-screen-choosable");

    const selectScreen = document.getElementById("select-piece-screen");
    if (selectScreen) {
      selectScreen.classList.add("opacity-hidden");
    }
  }

  removeFocus() {
    const currentActiveElement = document.activeElement;
    currentActiveElement.blur();
  }

  hide_promotion_screen() {
    this.removeFocus();
    this.modal.hide();
  }

  /**
   * Get DOM element for a specific square
   */
  getSquareEl(row, col) {
    return document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
  }

  /**
   * Convert algebraic notation (e.g. "e4") to row/col
   */
  algebraicToCoords(square) {
    if (!square || square.length !== 2) return null;
    const col = square.charCodeAt(0) - 97; // a=0, b=1...
    const row = 8 - parseInt(square[1]); // 8=0, 7=1...
    return { row, col };
  }

  /**
   * Convert row/col to algebraic notation (e.g. 0,4 -> "e8")
   */
  coordsToAlgebraic(row, col) {
    if (row < 0 || row > 7 || col < 0 || col > 7) return null;
    const file = String.fromCharCode(97 + col);
    const rank = 8 - row;
    return `${file}${rank}`;
  }

  /**
   * Render the full board from a Chess.js game instance
   * @param {Chess} game - Instance of Chess.js
   */
  render(game) {
    const board = game.board();
    const boardEl = document.querySelector(".chessboard");
    if (!boardEl) return;

    // Clear existing pieces
    boardEl.querySelectorAll(".piece").forEach((p) => p.remove());

    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const piece = board[row][col];
        const squareEl = this.getSquareEl(row, col);
        if (!squareEl || !piece) continue;

        const img = document.createElement("img");
        const typeName = this.pieceNames[piece.type];
        const colorSide = piece.color === "w" ? "white" : "black";
        img.src = IMAGE_BASE_URL + `/piece/${typeName}_${colorSide}.png`;
        img.className = "piece";
        img.draggable = false;
        squareEl.appendChild(img);
      }
    }
  }

  /**
   * Highlight a square (e.g. selected piece)
   */
  highlightSquare(row, col, className = "selected") {
    const square = this.getSquareEl(row, col);
    if (square) square.classList.add(className);
  }

  /**
   * Remove all highlights
   */
  clearHighlights(className = "selected") {
    document
      .querySelectorAll(`.${className}`)
      .forEach((el) => el.classList.remove(className));
  }

  /**
   * Animate a piece move (used in move_made)
   * !!! Forbidden !!!
   */
  animatePieceMove(from, to, promotion = null, pieceColor = null) {
    const fromCoords = this.algebraicToCoords(from);
    const toCoords = this.algebraicToCoords(to);
    if (!fromCoords || !toCoords) return Promise.resolve();

    const fromEl = this.getSquareEl(fromCoords.row, fromCoords.col);
    const toEl = this.getSquareEl(toCoords.row, toCoords.col);
    const pieceEl = fromEl.querySelector(".piece");
    if (!pieceEl) return Promise.resolve();

    const cloned = pieceEl.cloneNode(true);
    cloned.style.position = "absolute";
    cloned.style.left = `${fromEl.offsetLeft}px`;
    cloned.style.top = `${fromEl.offsetTop}px`;
    cloned.style.transition = "none";
    cloned.style.zIndex = "1000";

    document.getElementById("game-board").appendChild(cloned);

    requestAnimationFrame(() => {
      cloned.style.transition = "left 0.5s ease-in-out, top 0.5s ease-in-out";
      cloned.style.left = `${toEl.offsetLeft}px`;
      cloned.style.top = `${toEl.offsetTop}px`;
    });

    return new Promise((resolve) => {
      cloned.addEventListener(
        "transitionend",
        () => {
          if (promotion) {
            const promoName = this.pieceNames[promotion];
            const colorSide = pieceColor === "w" ? "white" : "black";
            const targetImg = toEl.querySelector(".piece");
            if (targetImg) {
              targetImg.src = `/static/img/piece/${promoName}_${colorSide}.png`;
            }
          }
          cloned.remove();
          resolve();
        },
        { once: true }
      );
    });
  }
}

// Global singleton
var BoardGenerationHelper = new ChessBoardGenerator();
