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

        // Optional: show coordinates for debugging
        // square.textContent = `${String.fromCharCode(97 + col)}${8 - row}`;

        board.appendChild(square);
      }
    }
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
        img.src = `/static/img/piece/${typeName}_${colorSide}.png`;
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
