// static/js/chess-main.js

async function waitForLogin() {
  while (true) {
    const res = await fetch("/api/session");
    const data = await res.json();
    if (data.logged_in) {
      return data.username;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
}

class ChessLogicLocalController {
  constructor() {
    this.language = "en";
    this.socket = null;
    this.roomName = "Room 114514";
    this.game = new Chess();
    this.selectedSquare = null;
    this.myColor = null;
    this.in_check = false;
    this.is_hand_hidden = false;
  }

  async init() {
    await waitForLogin();

    BoardGenerationHelper.generateChessBoard();

    this.socket = io();
    this.bindSocketIOEvents();

    this.setRoomName();
    this.joinRoom();
  }

  bindSocketIOEvents() {
    this.socket.on("connect", () => {
      console.log("Connect successfully.");
    });

    this.socket.on("waiting", () => {
      console.log("waiting...");
    });

    this.socket.on("client_game_data_got", async (clientData) => {
      const cardDataArray = clientData.friendlyHand;
      const enemyHandCount = clientData.enemyHandCount;
      if (_.isArray(cardDataArray)) {
        CardGenerationHelper.generateHandCards(cardDataArray);
        CardGenerationHelper.generateEnemyHandCards(enemyHandCount);
      } else {
        await this.disconnect("Session expired. Please log in again.");
      }
    });

    this.socket.on("start", async (data) => {
      await this.socket.emit("get_client_game_data", {});
      this.startGame(data);
    });

    this.socket.on("move_made", async (data) => {
      const move = data.move;

      // Critical: Check if the move was successful on the server
      if (!move.success) {
        await this.disconnect("Session expired. Please log in again.");
      }

      // Valid move — proceed with animation and update
      this.in_check = move.enemy_in_check || false;

      // Animate the move
      await BoardGenerationHelper.animatePieceMove(
        move.from,
        move.to,
        move.promotion || null,
        this.game.turn() === "w" ? "w" : "b" // color of the piece that just moved
      );

      // Update internal game state and re-render board
      this.game.load(data.fen); // assuming server still sends fen
      BoardGenerationHelper.render(this.game);
      this.updateTurnStatus();
      BoardGenerationHelper.clearHighlights();

      this.selectedSquare = null; // reset selection
    });

    this.socket.on("game_over", async (data) => {
      await modal.messageOnly(data.msg);
      window.location.href = "/home";
    });

    this.socket.on("message", async (data) => {
      await modal.messageOnly(data.msg);
    });

    this.socket.on("error", async (data) => {
      await this.disconnect("Session expired. Please log in again.");
    });
  }

  startGame(data) {
    this.myColor = data.color;

    const waitingScreen = document.getElementById("waiting-screen");
    if (waitingScreen) {
      waitingScreen.style.opacity = "0";
      waitingScreen.style.transition = "opacity 0.6s ease-out";
      setTimeout(() => {
        waitingScreen.style.display = "none";
      }, 600);
    }

    const gameScreen = document.getElementById("game-screen");
    if (gameScreen) {
      gameScreen.style.display = "block";
    }

    const changeHandVisibilityBtn = gameScreen.querySelector(
      "#change-hand-visibility-btn"
    );
    changeHandVisibilityBtn.addEventListener("click", () =>
      this.changeHandVisibility()
    );
    document.addEventListener("keyup", (event) => {
      if (event.key === "c") this.changeHandVisibility();
    });

    this.game.load(
      data.fen || "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    );
    BoardGenerationHelper.render(this.game);
    this.updateTurnStatus();
    this.attachSquareClicks();
  }

  setRoomName() {
    const roomNameHolder = document.getElementById("room-name-holder");
    this.roomName = window.localStorage.getItem("localRoomName");
    roomNameHolder.textContent = `Room Name: ${this.roomName}`;
  }

  joinRoom() {
    this.socket.emit("join", {
      room: this.roomName,
    });
    console.log("joined");
  }

  changeHandVisibility() {
    if (this.is_hand_hidden) {
      const handWrappers = document.querySelectorAll(".hand-area-wrapper");
      _.forEach(handWrappers, (e) => {
        e.classList.remove("hidden");
      });
      this.is_hand_hidden = false;
    } else {
      const handWrappers = document.querySelectorAll(".hand-area-wrapper");
      _.forEach(handWrappers, (e) => {
        e.classList.add("hidden");
      });
      this.is_hand_hidden = true;
    }
  }

  attachSquareClicks() {
    document.querySelectorAll(".square").forEach((square) => {
      square.onclick = (e) => this.handleSquareClick(e);
    });
  }

  handleSquareClick(event) {
    const square = event.currentTarget;
    const row = parseInt(square.dataset.row);
    const col = parseInt(square.dataset.col);
    const squareName = String.fromCharCode(97 + col) + (8 - row);

    if (this.game.turn() !== this.myColor[0]) return;

    if (this.selectedSquare) {
      let promotion = null;
      const piece = this.game.get(this.selectedSquare);
      if (piece?.type === "p") {
        const rank = squareName[1];
        if (
          (this.myColor === "white" && rank === "8") ||
          (this.myColor === "black" && rank === "1")
        ) {
          promotion = "q";
        }
      }

      this.socket.emit("make_move", {
        move: { from: this.selectedSquare, to: squareName, promotion },
      });

      BoardGenerationHelper.clearHighlights();
      this.selectedSquare = null;
    } else {
      BoardGenerationHelper.clearHighlights();
      const piece = this.game.get(squareName);
      if (piece && piece.color === this.game.turn()) {
        this.selectedSquare = squareName;
        BoardGenerationHelper.highlightSquare(row, col);
      }
    }
  }

  updateTurnStatus() {
    if (!document.getElementById("turn-status")) return;
    const turnText =
      this.game.turn() === this.myColor[0] ? "Your turn" : "Opponent's turn";
    const checkText = this.in_check
      ? " <span class='text-danger fw-bold'>(CHECK!)</span>"
      : "";
    document.getElementById("turn-status").innerHTML = turnText + checkText;
  }

  async disconnect(msg) {
    await modal.error(msg);
    //window.location.href = "/login";
  }
}

$(document).ready(async function () {
  const controller = new ChessLogicLocalController();
  await controller.init();

  document.getElementById("resign")?.addEventListener("click", () => {
    controller.socket.emit("resign", {});
  });
});
