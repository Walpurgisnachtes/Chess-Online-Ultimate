// static/js/chess-main.js

async function waitForLogin() {
  let i = 0;
  while (true) {
    if (i >= 5) {
      await modal.messageOnly("You are disconnected!");
      window.location.href = "/login";
    }
    const res = await fetch("/api/session");
    const data = await res.json();
    if (data.logged_in) {
      return data.username;
    }
    await new Promise((r) => setTimeout(r, 200 * 2 ** i));
    i += 1;
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
    this.is_moved = false;
    this.is_hand_hidden = false;

    this.isChoosingPiece = false;
    this.chosenPieces = [];
    this.minChosenPiece = 0;
    this.maxChosenPiece = 0;
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

    this.socket.on("client_game_data_got", async (data) => {
      const cardDataArray = data.friendlyHand;
      const enemyHandCount = data.enemyHandCount;
      if (_.isArray(cardDataArray)) {
        this.setPlayerName(data.friendlyName, data.enemyName);
        CardGenerationHelper.generateHandCards(cardDataArray);
        CardGenerationHelper.generateEnemyHandCards(enemyHandCount);
        this.updatePrestige(data.friendlyPrestige, data.enemyPrestige);
      } else {
        await this.disconnect("Session expired. Please log in again.");
      }
    });

    this.socket.on("start", async (data) => {
      await this.socket.emit("get_client_game_data", {});
      this.startGame(data);
    });

    this.socket.on("move_fails", async (data) => {
      console.log("move fails?", data);
    });

    this.socket.on("move_made", async (data) => {
      `
      'move': {
        'from': move_data['from'],
        'to': move_data['to'],
        'promotion': promotion,
        'en_passant': en_passant,
        'success': success
      }
      `;

      const move = data.move;

      // Critical: Check if the move was successful on the server
      if (!move.success) {
        await this.disconnect("Session expired. Please log in again.");
        return;
      }

      const { from, to, promotion, en_passant, success } = move;
      this.is_moved = true;
      // Animate the move
      // await BoardGenerationHelper.animatePieceMove(
      //   move.from,
      //   move.to,
      //   move.promotion || null,
      //   this.game.turn() === "w" ? "w" : "b" // color of the piece that just moved
      // );

      // Update internal state
      const fromPiece = this.game.get(from);

      this.game.remove(from);
      if (en_passant) {
        this.game.remove(en_passant);
      }

      this.game.put(fromPiece, to);

      BoardGenerationHelper.render(this.game);
      this.updateTurnStatus();
      BoardGenerationHelper.clearHighlights();
      this.selectedSquare = null;
    });

    this.socket.on("place_piece", async (data) => {
      // data { name: "knight"}
      const pieceName = data.piece;
      const pieceColor = data.color === "white" ? "w" : "b";
      const positions = data.position;
      const pieceNameMapper = {
        pawn: "p",
        knight: "n",
        bishop: "b",
        rook: "r",
        queen: "q",
        king: "k",
      };

      _.forEach(positions, async (sq) => {
        const type = pieceNameMapper[pieceName];
        if (!type) {
          this.disconnect("Session expired. Please log in again.");
          return;
        }
        const color = pieceColor;
        this.game.put({ type, color }, sq);
      });

      BoardGenerationHelper.render(this.game);
      BoardGenerationHelper.clearHighlights();
    });

    this.socket.on("remove_piece", async (data) => {
      const squares = data.position;
      _.forEach(squares, (sq) => {
        this.game.remove(sq);
      });

      BoardGenerationHelper.render(this.game);
      BoardGenerationHelper.clearHighlights();
    });

    this.socket.on("turn_end", async (data) => {
      console.log(`Turn end. Now is ${data.current_color} side's turn`);
      this.game.setTurn(data.current_color); // Simplified
      this.is_moved = false;
      this.updateTurnStatus();
    });

    this.socket.on("open_selector", async (data) => {
      `
      {
        "select_type": data["select_type"],
        "select_from_item": data["select_from_item"],
        "min": data["min"],
        "max": data["max"],
        "current_player": data["current_player"]
      }
      `;
      this.resetChosenPieces();

      this.changeHandVisibility("hidden");

      if (data.select_type == "card") {
      } else if (data.select_type == "piece") {
        this.isChoosingPiece = true;
        this.chosenPieces = [];
        this.minChosenPiece = _.toInteger(data.min);
        this.maxChosenPiece = _.toInteger(data.max);
        BoardGenerationHelper.show_select_piece_screen(data.select_from_item);
      }
    });

    this.socket.on("accept_play_card", async (data) => {
      this.updateTurnStatus();
    });

    this.socket.on("update_hand", async (data) => {
      const cardDataArray = data.friendlyHand;
      const enemyHandCount = data.enemyHandCount;
      if (_.isArray(cardDataArray)) {
        CardGenerationHelper.generateHandCards(cardDataArray);
        CardGenerationHelper.generateEnemyHandCards(enemyHandCount);
      } else {
        await this.disconnect("Session expired. Please log in again.");
      }
    });

    this.socket.on("update_prestige", async (data) => {
      const enemyColor = this.myColor == "white" ? "black" : "white";
      this.updatePrestige(data[this.myColor], data[enemyColor]);
    });

    this.socket.on("turn_end", async (data) => {
      console.log(`Turn end. Now is ${data.current_color} side's turn`);
      this.setTurn(data.current_color);
      this.is_moved = false;
      this.updateTurnStatus();
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

    BoardGenerationHelper.generatePromotionScreen(this.myColor);

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

    const turnSwitcher = document.getElementById("game-status");
    turnSwitcher.addEventListener("click", async (e) => {
      console.log(turnSwitcher, turnSwitcher.disabled);
      if (turnSwitcher.disabled) return;
      await this.socket.emit("request_turn_end", {});
    });

    const choosePieceConfirmBtn = document.getElementById(
      "submit-selected-piece-btn"
    );
    choosePieceConfirmBtn.addEventListener("click", async () => {
      const chosenPieceLength = this.chosenPieces.length;
      if (
        this.isChoosingPiece &&
        chosenPieceLength >= this.minChosenPiece &&
        chosenPieceLength <= this.maxChosenPiece
      ) {
        await this.socket.emit("chosen_by_selector", {
          selected: this.chosenPieces,
        });
        this.changeHandVisibility("show");
        this.resetChosenPieces();
        BoardGenerationHelper.hide_select_piece_screen();
      }
    });

    window.addEventListener("playCard", (e) => {
      this.playCard(e.detail.cardIdInHand);
    });

    this.game.load(
      data.fen || "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    );
    BoardGenerationHelper.render(this.game);
    this.updateTurnStatus();
    this.attachSquareClicks();
  }

  setPlayerName(friendlyName, enemyName) {
    const friendlyNameEl = document.getElementById("friendly-name");
    const enemyNameEl = document.getElementById("enemy-name");

    friendlyNameEl.textContent = friendlyName;
    enemyNameEl.textContent = enemyName;
  }

  setTurn(color) {
    // This is now just a pass-through to the game object
    this.game.setTurn(color);
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

  changeHandVisibility(status = "toggle") {
    const hideHand = () => {
      const handWrappers = document.querySelectorAll(".hand-area-wrapper");
      _.forEach(handWrappers, (e) => {
        e.classList.add("hidden");
      });
      this.is_hand_hidden = true;
    };

    const showHand = () => {
      const handWrappers = document.querySelectorAll(".hand-area-wrapper");
      _.forEach(handWrappers, (e) => {
        e.classList.remove("hidden");
      });
      this.is_hand_hidden = false;
    };

    switch (status) {
      case "toggle":
        this.is_hand_hidden ? showHand() : hideHand();
        break;
      case "hidden":
        hideHand();
        break;
      case "show":
        showHand();
      default:
        break;
    }
  }

  resetChosenPieces() {
    this.isChoosingPiece = false;
    this.chosenPieces = [];
    this.minChosenPiece = 0;
    this.maxChosenPiece = 0;
  }

  playCard(cardIdInHand) {
    console.log(`I will play card ${cardIdInHand}`);
    this.socket.emit("played_card", {
      played_card_in_hand_index: cardIdInHand,
    });
  }

  attachSquareClicks() {
    document.querySelectorAll(".square").forEach((square) => {
      square.onclick = (e) => this.handleSquareClick(e);
    });
  }

  // TODO: Promotion Logic
  async handleSquareClick(event) {
    const square = event.currentTarget;
    const row = parseInt(square.dataset.row);
    const col = parseInt(square.dataset.col);
    const squareName = BoardGenerationHelper.coordsToAlgebraic(row, col);

    if (this.game.turn() !== this.myColor[0] && !this.isChoosingPiece) return;

    if (this.isChoosingPiece) {
      if (this.game.get(squareName)) {
        if (_.includes(this.chosenPieces, squareName)) {
          _.pull(this.chosenPieces, squareName);
        } else if (this.chosenPieces.length < this.maxChosenPiece) {
          this.chosenPieces.push(squareName);
        }
        BoardGenerationHelper.clearHighlights();
        _.forEach(this.chosenPieces, (squareNameChosen) => {
          const { row, col } =
            BoardGenerationHelper.algebraicToCoords(squareNameChosen);
          BoardGenerationHelper.highlightSquare(row, col);
        });
      }
    } else if (this.selectedSquare) {
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

      console.log(
        `Requested Move: from: ${this.selectedSquare} to: ${squareName} promotion: ${promotion}`
      );

      await this.socket.emit("make_move", {
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

  updatePrestige(friendlyPrestige, enemyPrestige) {
    const myPrestigeEl = document.getElementById("friendly-prestige-area");
    const enemyPrestigeEl = document.getElementById("enemy-prestige-area");

    myPrestigeEl.textContent = friendlyPrestige;
    enemyPrestigeEl.textContent = enemyPrestige;
  }

  updateTurnStatus() {
    const turnStatus = document.getElementById("game-status");
    if (!turnStatus) return;
    const turnPlayerStatus = turnStatus.querySelector("#turn-player-status");
    const isMyTurn = this.game.turn() === this.myColor[0];
    const turnText = isMyTurn
      ? `${isMyTurn && this.is_moved ? "Press to End Turn" : "Your turn"}`
      : "Opponent's turn";
    turnPlayerStatus.innerHTML = turnText;
    turnStatus.disabled = !isMyTurn || !this.is_moved;
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
