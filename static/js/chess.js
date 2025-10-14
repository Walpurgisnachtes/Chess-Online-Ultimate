// static/js/chess.js
const boardElement = document.getElementById("chessboard");
const game = new Chess();
let selectedSquare = null;
let myColor = null;
let socket = null;

const pieceNames = {
  p: "pawn",
  n: "knight",
  b: "bishop",
  r: "rook",
  q: "queen",
  k: "king",
};

function clearHighlights() {
  document
    .querySelectorAll(".selected")
    .forEach((el) => el.classList.remove("selected"));
}

function getSquareEl(row, col) {
  return document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
}

function animatePieceMove(
  fromSquareEl,
  toSquareEl,
  pieceEl,
  isPromotion = false,
  promotionType = null,
  pieceColor = null
) {
  if (!pieceEl) return;
  fromSquareEl.removeChild(pieceEl);
  pieceEl.style.position = "absolute";
  pieceEl.style.left = `${fromSquareEl.offsetLeft}px`;
  pieceEl.style.top = `${fromSquareEl.offsetTop}px`;
  pieceEl.style.transition = "none";
  pieceEl.classList.add("move-animation");
  boardElement.appendChild(pieceEl);
  void pieceEl.offsetWidth;
  pieceEl.style.transition = "left 0.5s ease-in-out, top 0.5s ease-in-out";
  pieceEl.style.left = `${toSquareEl.offsetLeft}px`;
  pieceEl.style.top = `${toSquareEl.offsetTop}px`;
  pieceEl.addEventListener(
    "transitionend",
    () => {
      pieceEl.classList.remove("move-animation");
      pieceEl.style.position = "";
      pieceEl.style.left = "";
      pieceEl.style.top = "";
      pieceEl.style.transition = "";
      if (isPromotion && promotionType) {
        const promoName = pieceNames[promotionType];
        const pieceColorSide = pieceColor == "w" ? "white" : "black";
        pieceEl.src = `/static/img/piece/${promoName}_${pieceColorSide}.png`;
      }
      toSquareEl.appendChild(pieceEl);
    },
    { once: true }
  );
}

function renderBoard() {
  boardElement.innerHTML = "";
  const board = game.board();
  for (let i = 0; i < 8; i++) {
    for (let j = 0; j < 8; j++) {
      const square = document.createElement("div");
      square.className = `square ${
        (i + j) % 2 === 0 ? "bg-gray-200" : "bg-gray-600"
      }`;
      square.dataset.row = i;
      square.dataset.col = j;
      const piece = board[i][j];
      if (piece) {
        const img = document.createElement("img");
        const typeName = pieceNames[piece.type];
        const pieceColorSide = piece.color == "w" ? "white" : "black";
        img.src = `/static/img/piece/${typeName}_${pieceColorSide}.png`;
        img.className = "piece";
        square.appendChild(img);
      }
      square.addEventListener("click", handleSquareClick);
      boardElement.appendChild(square);
    }
  }
}

function updateTurnStatus() {
  document.getElementById("turn-status").innerText =
    game.turn() === myColor[0] ? "Your turn" : "Opponent's turn";
}

function handleSquareClick(event) {
  const square = event.currentTarget;
  const row = parseInt(square.dataset.row);
  const col = parseInt(square.dataset.col);
  const squareName = String.fromCharCode(97 + col) + (8 - row);

  if (game.turn() !== myColor[0]) return;

  if (selectedSquare) {
    let promotion = null;
    const piece = game.get(selectedSquare);
    if (piece && piece.type === "p") {
      const toRank = squareName[1];
      if (
        (game.turn() === "w" && toRank === "8") ||
        (game.turn() === "b" && toRank === "1")
      ) {
        promotion = "q";
      }
    }
    socket.emit("make_move", {
      room,
      move: { from: selectedSquare, to: squareName, promotion },
    });
    clearHighlights();
    selectedSquare = null;
  } else {
    clearHighlights();
    const piece = game.get(squareName);
    if (piece && piece.color === game.turn()) {
      selectedSquare = squareName;
      square.classList.add("selected");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  socket = io();

  socket.on("connect", () => {
    socket.emit("join", { room, username, skill });
  });

  socket.on("waiting", () => {
    // Already shown
  });

  socket.on("start", (data) => {
    myColor = data.color;
    document.getElementById(
      "status"
    ).innerHTML = `Playing as ${myColor} against ${data.opponent}`;
    document.getElementById("waiting-screen").style.display = "none";
    document.getElementById("game-screen").style.display = "block";
    game.load(data.fen);
    renderBoard();
    updateTurnStatus();
  });

  socket.on("move_made", (data) => {
    const move = data.move;
    const fromSquare = move.from;
    const toSquare = move.to;
    const fromRow = 8 - parseInt(fromSquare[1]);
    const fromCol = fromSquare.charCodeAt(0) - 97;
    const toRow = 8 - parseInt(toSquare[1]);
    const toCol = toSquare.charCodeAt(0) - 97;
    const fromSquareEl = getSquareEl(fromRow, fromCol);
    const toSquareEl = getSquareEl(toRow, toCol);
    const pieceEl = fromSquareEl.querySelector(".piece");
    const mover = game.turn(); // before update, the mover who just moved
    let animations = [];

    // Main piece move
    if (pieceEl) {
      const promise = new Promise((resolve) => {
        animatePieceMove(
          fromSquareEl,
          toSquareEl,
          pieceEl,
          !!move.promotion,
          move.promotion,
          mover
        );
        pieceEl.addEventListener("transitionend", resolve, { once: true });
      });
      animations.push(promise);
    }

    // Capture
    if (move.captured_sq) {
      const capSquare = move.captured_sq;
      const capRow = 8 - parseInt(capSquare[1]);
      const capCol = capSquare.charCodeAt(0) - 97;
      const capSquareEl = getSquareEl(capRow, capCol);
      const capPiece = capSquareEl.querySelector(".piece");
      if (capPiece) {
        const promise = new Promise((resolve) => {
          capPiece.classList.add("capture-animation");
          capPiece.addEventListener(
            "animationend",
            () => {
              capPiece.remove();
              resolve();
            },
            { once: true }
          );
        });
        animations.push(promise);
      }
    }

    // Rook castling
    if (move.rook_from && move.rook_to) {
      const rookFrom = move.rook_from;
      const rookTo = move.rook_to;
      const rookFromRow = 8 - parseInt(rookFrom[1]);
      const rookFromCol = rookFrom.charCodeAt(0) - 97;
      const rookToRow = 8 - parseInt(rookTo[1]);
      const rookToCol = rookTo.charCodeAt(0) - 97;
      const rookFromEl = getSquareEl(rookFromRow, rookFromCol);
      const rookToEl = getSquareEl(rookToRow, rookToCol);
      const rookPieceEl = rookFromEl.querySelector(".piece");
      if (rookPieceEl) {
        const promise = new Promise((resolve) => {
          animatePieceMove(rookFromEl, rookToEl, rookPieceEl);
          rookPieceEl.addEventListener("transitionend", resolve, {
            once: true,
          });
        });
        animations.push(promise);
      }
    }

    Promise.all(animations).then(() => {
      game.load(data.fen);
      updateTurnStatus();
      clearHighlights();
    });
  });

  socket.on("game_over", (data) => {
    alert(data.msg);
    window.location.href = "/leaderboard";
  });

  socket.on("message", (data) => {
    alert(data.msg);
  });

  document.getElementById("resign").addEventListener("click", () => {
    socket.emit("resign", { room });
  });

  // For testing
  document.getElementById("end-game").addEventListener("click", () => {
    fetch("/update_win", { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          alert("Win recorded! Redirecting to leaderboard.");
          window.location.href = "/leaderboard";
        }
      });
  });
});
