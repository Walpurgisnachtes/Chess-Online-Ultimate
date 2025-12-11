/**
 * ChessBoardGenerator
 * 
 * Utility class responsible for dynamically generating an 8×8 chessboard
 * in the DOM. Designed to work with the existing CSS grid layout in
 * `fan-shape-cards.css` and `chess.html`.
 * 
 * Features:
 * - Creates 64 squares with correct light/dark coloring
 * - Adds data-row and data-col attributes for easy move calculation
 * - Fully compatible with dark/light mode
 * - No external dependencies
 * 
 * Usage:
 *   BoardGenerationHelper.generateChessBoard();
 * 
 * @class ChessBoardGenerator
 * @example
 * // Call once after DOM is loaded
 * document.addEventListener("DOMContentLoaded", () => {
 *   BoardGenerationHelper.generateChessBoard();
 * });
 */
class ChessBoardGenerator {
  /**
   * Generates the full 8×8 chessboard inside the element with class ".chessboard"
   * 
   * The board is built row by row (rank 8 to rank 1), column by column (a to h).
   * Each square gets:
   *   - CSS classes: "square", "light" or "dark"
   *   - data attributes: data-row (0–7), data-col (0–7)
   * 
   * Row 0 = rank 8 (top of board), Row 7 = rank 1 (bottom)
   * Col 0 = file a, Col 7 = file h
   * 
   * @public
   * @returns {void}
   * @throws {Error} If no element with class "chessboard" is found
   */
  generateChessBoard() {
    const board = document.querySelector(".chessboard");

    if (!board) {
      throw new Error(
        'Chessboard container not found. Make sure <div class="chessboard"></div> exists in the DOM.'
      );
    }

    // Clear any existing content (idempotent)
    board.innerHTML = "";

    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const square = document.createElement("div");

        // Base styling
        square.classList.add("square");

        // Store position for game logic (0-based indexing)
        square.dataset.row = row;
        square.dataset.col = col;

        // Standard chessboard coloring: a1 is dark
        // (row + col) even → light, odd → dark
        if ((row + col) % 2 === 0) {
          square.classList.add("light");
        } else {
          square.classList.add("dark");
        }

        // Optional: uncomment to show coordinates during development
        // square.textContent = `${String.fromCharCode(97 + col)}${8 - row}`;

        board.appendChild(square);
      }
    }
  }
}

/**
 * Global singleton instance of ChessBoardGenerator.
 * 
 * Exported for use across modules or direct call in inline scripts.
 * 
 * @global
 * @type {ChessBoardGenerator}
 * @example
 * // Most common usage
 * BoardGenerationHelper.generateChessBoard();
 */
var BoardGenerationHelper = new ChessBoardGenerator();