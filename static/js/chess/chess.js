class Chess {
  constructor() {
    this.boardState = {};
    this.currentTurn = "w";
  }

  init() {
    this.boardState = {};
    this.currentTurn = "w";
  }

  board() {
    const output = [];
    const files = ["a", "b", "c", "d", "e", "f", "g", "h"];

    for (let row = 0; row < 8; row++) {
      const rowArray = [];
      const rank = 8 - row; // Row 0 is Rank 8, Row 7 is Rank 1

      for (let col = 0; col < 8; col++) {
        const squareName = files[col] + rank;
        const piece = this.boardState[squareName] || null;
        rowArray.push(piece);
      }
      output.push(rowArray);
    }
    return output;
  }

  put(pieceObj, sq) {
    // pieceObj: { type: 'p', color: 'w' }
    this.boardState[sq] = pieceObj;
    return true;
  }

  remove(sq) {
    const piece = this.boardState[sq] || null;
    delete this.boardState[sq];
    return piece;
  }

  get(sq) {
    return this.boardState[sq] || null;
  }

  turn() {
    return this.currentTurn;
  }

  setTurn(color) {
    // color can be "white"/"black" or "w"/"b"
    this.currentTurn = color.startsWith("w") ? "w" : "b";
  }

  // Simple FEN loader to populate the initial boardState state
  load(fen) {
    this.boardState = {};
    const parts = fen.split(" ");
    const rows = parts[0].split("/");
    this.currentTurn = parts[1];

    const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
    rows.forEach((row, rowIndex) => {
      let fileIndex = 0;
      const rank = 8 - rowIndex;
      for (const char of row) {
        if (isNaN(char)) {
          const sq = files[fileIndex] + rank;
          this.boardState[sq] = {
            type: char.toLowerCase(),
            color: char === char.toUpperCase() ? "w" : "b",
          };
          fileIndex++;
        } else {
          fileIndex += parseInt(char);
        }
      }
    });
  }

  // Placeholder to prevent errors if other parts of code call it
  fen() {
    return "";
  }
}
