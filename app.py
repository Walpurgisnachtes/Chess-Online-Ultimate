from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, join_room, emit
import os
import json
import chess
import secrets

import backend.read_localized_text as localized_text

app = Flask(__name__)
app.json.sort_keys = False
app.secret_key = secrets.token_bytes(32)
socketio = SocketIO(app)

# Simulated database using text files
USERS_FILE = 'users.txt'
LEADERBOARD_FILE = 'leaderboard.txt'

games = {}  # room: {'board': chess.Board(), 'turn': 'w', 'players': {'white': sid, 'black': sid}, 'usernames': {'white': username, 'black': username}, 'skills': {'white': skill, 'black': skill}}

def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'w') as f:
            json.dump({}, f)

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_leaderboard():
    with open(LEADERBOARD_FILE, 'r') as f:
        return json.load(f)

def save_leaderboard(leaderboard):
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(leaderboard, f)

def replace_skills_placeholder_in_localized_text(texts_dict):
    for text_key in texts_dict:
        text_object = texts_dict[text_key]
        text_content = text_object["description"]
        texts_dict[text_key]["description"] = \
            text_content.replace("[linebreak]", "<br />").replace("[username]", session["username"])
    return texts_dict

def is_queen_like_move(from_sq, to_sq):
    file1 = chess.square_file(from_sq)
    rank1 = chess.square_rank(from_sq)
    file2 = chess.square_file(to_sq)
    rank2 = chess.square_rank(to_sq)
    return file1 == file2 or rank1 == rank2 or abs(file1 - file2) == abs(rank1 - rank2)

def get_squares_between(from_sq, to_sq):
    squares = []
    file1 = chess.square_file(from_sq)
    rank1 = chess.square_rank(from_sq)
    file2 = chess.square_file(to_sq)
    rank2 = chess.square_rank(to_sq)
    file_diff = file2 - file1
    rank_diff = rank2 - rank1
    steps = max(abs(file_diff), abs(rank_diff))
    if steps <= 1:
        return []
    file_step = file_diff / steps
    rank_step = rank_diff / steps
    current_file = file1
    current_rank = rank1
    for _ in range(1, steps):
        current_file += file_step
        current_rank += rank_step
        sq = chess.square(round(current_file), round(current_rank))
        squares.append(sq)
    return squares

def handle_revive_skill(board: chess.Board, captured_piece: chess.Piece, captured_on_square: int, game: dict):
    
    ORIGINAL_SQUARES = {
        chess.WHITE: {
            chess.ROOK: [chess.A1, chess.H1],
            chess.KNIGHT: [chess.B1, chess.G1],
            'BISHOP_SQUARES': {
                "LIGHT": chess.F1,
                "DARK": chess.C1
            }
        },
        chess.BLACK: {
            chess.ROOK: [chess.A8, chess.H8],
            chess.KNIGHT: [chess.B8, chess.G8],
            'BISHOP_SQUARES': {
                "LIGHT": chess.C8,
                "DARK": chess.F8
            }
        }
    }

    def get_square_color(sq):
        if isinstance(sq, str):
            sq = chess.parse_square(sq)
        
        if sq < 0 or sq > 63:
            raise ValueError("Invalid square")
        
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)
        return "LIGHT" if (file_idx + rank_idx) % 2 == 0 else "DARK"
        
    if captured_piece is None:
        return

    reviving_player_color = captured_piece.color
    color_key = "white" if reviving_player_color == chess.WHITE else "black"
    
    if game.get('revive', {}).get(color_key, False):
        return

    piece_type = captured_piece.piece_type
    if piece_type not in [chess.KNIGHT, chess.BISHOP, chess.ROOK]:
        return

    revival_squares = []
    if piece_type == chess.KNIGHT or piece_type == chess.ROOK:
        revival_squares = ORIGINAL_SQUARES[reviving_player_color][piece_type]
    elif piece_type == chess.BISHOP:
        square_color = get_square_color(captured_on_square)
        bishop_home_square = ORIGINAL_SQUARES[reviving_player_color]['BISHOP_SQUARES'][square_color]
        revival_squares.append(bishop_home_square)

    for square in revival_squares:
        if board.piece_at(square) is None:
            board.set_piece_at(square, captured_piece)
            
            if 'revive' not in game:
                game['revive'] = {"white": False, "black": False}
            game['revive'][color_key] = True
            return

def is_check(board, your_skill, opponent_skill):
    def is_king_attacked_by_theocracy(board_to_check: chess.Board) -> bool:
        king_square = board_to_check.king(board_to_check.turn)
        if king_square is None:
            return False
            
        opponent_color = not board_to_check.turn
        enemy_bishops = board_to_check.pieces(chess.BISHOP, opponent_color)

        for bishop_square in enemy_bishops:
            # Phantom Piece Technique:
            # 1. Temporarily replace the bishop with a queen.
            original_piece = board_to_check.piece_at(bishop_square)
            board_to_check.set_piece_at(bishop_square, chess.Piece(chess.QUEEN, opponent_color))

            # 2. Check if this "phantom queen" attacks the king.
            is_attacked = board_to_check.is_attacked_by(opponent_color, king_square)

            # 3. CRITICAL: Restore the board to its original state.
            board_to_check.set_piece_at(bishop_square, original_piece)

            if is_attacked:
                # An enemy bishop is checking the king like a queen.
                return True
        
        return False

    def is_king_attacked_by_blitzkrieg(board_to_check: chess.Board) -> bool:
        """
        Checks if the king is attacked by an enemy rook that can jump friendly pieces.
        """
        king_square = board_to_check.king(board_to_check.turn)
        if king_square is None: return False
        
        opponent_color = not board_to_check.turn
        enemy_rooks = board_to_check.pieces(chess.ROOK, opponent_color)

        for rook_square in enemy_rooks:
            # Check horizontal and vertical paths from the rook
            # A Blitzkrieg attack is valid if the path to the king is either empty
            # or contains ONLY pieces of the same color as the rook.
            
            # Get all squares between the rook and the king (if they are aligned)
            # The `chess.SquareSet` intersection is a powerful way to do this.
            squares_between = chess.SquareSet(chess.between(rook_square, king_square))
            
            # If they are not aligned, squares_between will be empty, and the loop won't run.
            is_blocked = False
            for sq in squares_between:
                piece = board_to_check.piece_at(sq)
                if piece and piece.color != opponent_color:
                    # Path is blocked by a piece that is NOT friendly to the rook.
                    is_blocked = True
                    break
            
            if not is_blocked:
                # If the path is clear (or only has friendly pieces), we check if the king
                # is actually on the same rank or file. We can use the standard attacker check for this.
                if bool(board_to_check.attackers(opponent_color, king_square) & chess.SquareSet([rook_square])):
                    return True
        return False

    standard_check = board.is_check()

    theocracy_check = False
    if opponent_skill == 'theocracy':
        board_copy = board.copy()
        theocracy_check = is_king_attacked_by_theocracy(board_copy)

    blitzkrieg_check = False
    if opponent_skill == 'blitzkrieg':
        # No need to copy the board, our helper function only reads data.
        blitzkrieg_check = is_king_attacked_by_blitzkrieg(board)

    is_in_check_overall = standard_check or theocracy_check or blitzkrieg_check

    immunity = False
    if your_skill == 'theocracy':
        immunity = immunity or is_protected_by_theocracy(board, board.turn)
            
    return is_in_check_overall and not immunity


def is_checkmate(game: dict, board: chess.Board, your_skill: str, opponent_skill: str) -> bool:
    """
    Determines if the current player is in checkmate, considering all custom skills.

    This function is correct because it does not rely on board.legal_moves.
    Instead, it checks all possible moves with a custom is_move_legal function.
    """
    # Condition 1: The player must be in check to be checkmated.
    if not is_check(board, your_skill, opponent_skill):
        return False

    # Condition 2: The player must have NO legal moves to escape the check.
    current_player_color = board.turn
    
    # Get a list of all squares occupied by the current player's pieces.
    my_piece_squares = [sq for sq in chess.SQUARES if board.piece_at(sq) and board.piece_at(sq).color == current_player_color]

    for from_square in my_piece_squares:
        # Iterate through every possible destination square on the board
        for to_square in chess.SQUARES:
            if from_square == to_square:
                continue

            # Create a move object.
            move = chess.Move(from_square, to_square)

            # Use the comprehensive is_move_legal function. This is the key to the solution.
            # It must be able to validate standard moves, Blitzkrieg jumps, Theocracy moves, etc.,
            # and ensure the king is not in check after the move.
            if is_move_legal(game, board, move, your_skill, opponent_skill):
                # If we find even ONE legal move, it is not checkmate.
                # print(f"DEBUG: Found legal escape move: {move}") # Optional: for debugging
                return False

    # If the function has looped through every possible move and found none to be legal,
    # then it is truly checkmate.
    return True

def is_path_clear(board, from_sq, to_sq):
    for sq in get_squares_between(from_sq, to_sq):
        if board.piece_at(sq):
            return False
    return True

def is_path_clear_blitzkrieg(board, from_sq, to_sq, turn_color):
    for sq in get_squares_between(from_sq, to_sq):
        if board.piece_at(sq) and board.piece_at(sq).color != turn_color:
            return False
    return True

def is_protected_by_theocracy(board, turn_color):
    return len(board.pieces(chess.BISHOP, turn_color)) > 0

def is_legal_second_move_no_capture(board, move):
    if board.is_capture(move):
        return False
    return True

def is_legal_second_move_no_check(board, move):
    if board.gives_check(move):
        return False
    return True

def is_legal_second_move_no_capture_and_check(board, move):
    if board.is_capture(move):
        return False
    if board.gives_check(move):
        return False
    return True

def is_movable_under_subjects(board, your_skill, opponent_skill, from_sq, to_sq, turn_color):
    def check_in_front_of(pawn_sq: str, piece_sq: str, pawn_color: chess.Color) -> bool:
        try:
            pawn_square_index = chess.parse_square(pawn_sq)
            piece_square_index = chess.parse_square(piece_sq)
        except ValueError:
            return False

        pawn_file = chess.square_file(pawn_square_index)
        piece_file = chess.square_file(piece_square_index)

        if pawn_file != piece_file:
            return False

        pawn_rank = chess.square_rank(pawn_square_index)
        piece_rank = chess.square_rank(piece_square_index)

        if pawn_color == chess.WHITE:
            return piece_rank > pawn_rank
        else:
            return piece_rank < pawn_rank

    from_square_index = chess.parse_square(from_sq)
    to_square_index = chess.parse_square(to_sq)
    move = chess.Move(from_square_index, to_square_index)

    moving_piece = board.piece_at(from_square_index)
    if not moving_piece:
        return True

    if moving_piece.piece_type == chess.KING and is_check(board, your_skill, opponent_skill):
        return True

    enemy_color = not turn_color
    enemy_pawns = board.pieces(chess.PAWN, enemy_color)
    
    subjects_skill_applying_pawn_squares = set()
    for pawn_square_index in enemy_pawns:
        pawn_sq_name = chess.square_name(pawn_square_index)
        is_applying_subjects = check_in_front_of(
            pawn_sq=pawn_sq_name,
            piece_sq=from_sq,
            pawn_color=enemy_color
        )
        if is_applying_subjects:
            subjects_skill_applying_pawn_squares.add(pawn_square_index)
    
    if not subjects_skill_applying_pawn_squares:
        return True
    
    is_a_capture = board.is_capture(move)

    if is_a_capture and to_square_index in subjects_skill_applying_pawn_squares:
        return True
    else:
        return False

def is_promotion(board, from_sq, to_sq):
    piece = board.piece_at(from_sq)
    if piece and piece.piece_type == chess.PAWN:
        rank = chess.square_rank(to_sq)
        if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
            return True
    return False

def is_move_legal(game: dict, board: chess.Board, move: chess.Move, your_skill: str, opponent_skill: str, *args, **kwargs) -> bool:
    """
    Checks if a move is legal, considering standard rules and custom skills.
    This version is fixed to prevent the board.turn side-effect bug.
    """
    
    # --- Step 0: Handle Special Cases like Rampage's Second Move ---
    is_second_move = kwargs.get("second_move", False)
    
    if is_second_move:
        # For a second move, only the skill's specific rules apply.
        if your_skill == 'rampage':
            if move.from_square != game["data"]["rampage"]:
                return False
            
            return is_legal_second_move_no_capture_and_check(board, move)
        
        elif your_skill == 'blitzkrieg':
            rook_position = board.pieces(chess.ROOK, board.turn)
            
            if len(rook_position) < 2:
                return False
            
            try:
                rook_position.remove(game["data"]["blitzkrieg"])
                movable_rook_under_blitzkrieg = rook_position.pop()
            except:
                return False
            
            if move.from_square != movable_rook_under_blitzkrieg:
                return False
        
        else:
            # No other skill grants a second move.
            return False

    # --- Step 1: Determine if the move has a basis for legality (Standard or Custom) ---
    
    # This is the SAFE way to check for standard legality without side effects.
    is_standard_legal = move in board.legal_moves
    
    is_custom_legal = False
    moving_piece = board.piece_at(move.from_square)

    # If the move isn't standard, check if a skill makes it legal.
    if not is_standard_legal and moving_piece:
        if your_skill == 'theocracy' and moving_piece.piece_type == chess.BISHOP:
            # Check if a bishop is making a queen-like move on a clear path.
            # (Assuming these helpers exist and are correct)
            if is_queen_like_move(move.from_square, move.to_square) and is_path_clear(board, move.from_square, move.to_square):
                is_custom_legal = True
        
        elif your_skill == 'blitzkrieg' and moving_piece.piece_type == chess.ROOK:
            # Check if a rook is making a valid blitzkrieg move.
            # (Assuming this helper exists)
            if is_path_clear_blitzkrieg(board, move.from_square, move.to_square, board.turn):
                is_custom_legal = True
    
    # If the move is neither standard-legal nor made legal by a skill, it's invalid.
    if not is_standard_legal and not is_custom_legal:
        return False

    # --- Step 2: Check for blocking conditions ---

    # Block moving onto a piece of the same color.
    target_piece = board.piece_at(move.to_square)
    if target_piece and target_piece.color == board.turn:
        return False

    # Block capturing a king protected by Theocracy immunity.
    if target_piece and target_piece.piece_type == chess.KING:
        # We need to check the opponent's immunity.
        if is_protected_by_theocracy(board, not board.turn):
            return False
            
    # Check if the move is blocked by the opponent's 'Subjects' skill.
    if opponent_skill == 'subjects':
        if not is_movable_under_subjects(board, your_skill, opponent_skill, move.from_square, move.to_square, board.turn):
            return False
            
    # --- Step 3: Final check - does the move leave the king in check? ---
    # This is the most important check and must be done last.
    # The push/pop pattern is the correct and safe way to test this.
    try:
        board.push(move)
        # After pushing, board.turn is now the opponent's color.
        # is_check needs to check if the *previous* player is now in check.
        # So we create a temporary board with the turn flipped back.
        board_after_move = board.copy()
        board_after_move.turn = not board.turn # Check from the perspective of the player who just moved
        
        # The is_check function should be designed to check the player whose turn it is.
        # So we need to call it on the copied board with the turn flipped back.
        if is_check(board_after_move, your_skill, opponent_skill):
            # The move resulted in the player being in check (e.g., moving a pinned piece).
            board.pop()
            return False
            
    finally:
        # Ensure the board is always restored, even if an error occurs.
        board.pop()

    # If all checks passed, the move is fully legal.
    return True

def check_extra_move(game: dict, board: chess.Board, move: chess.Move, your_skill: str, opponent_skill: str, *args, **kwargs) -> bool:
    # By default, no extra move is granted.
    extra_move_granted = False

    # --- Check for Rampage Skill ---
    if your_skill == 'rampage':
        if get_skill_count(game, your_skill, board.turn) > 0:
            return False
        
        moving_piece = board.piece_at(move.from_square)
        
        # Conditions: 1. Piece is a Knight, 2. Move is a capture.
        if moving_piece and moving_piece.piece_type == chess.KNIGHT:
            if board.is_capture(move):
                extra_move_granted = True

    # --- Check for Blitzkrieg Skill ---
    elif your_skill == 'blitzkrieg':
        if get_skill_count(game, your_skill, board.turn) > 0:
            return False
        
        if len(board.pieces(chess.ROOK, board.turn)) < 2:
            return False
        
        moving_piece = board.piece_at(move.from_square)

        # Conditions: 1. Piece is a Rook, 2. Move is NOT a capture.
        if moving_piece and moving_piece.piece_type == chess.ROOK:
            if not board.is_capture(move):
                # Condition 3: Move does NOT result in a check.
                board.push(move)
                is_check_after_move = is_check(board, your_skill, opponent_skill)
                board.pop()

                if not is_check_after_move:
                    extra_move_granted = True

    return extra_move_granted    

def apply_skills_before_start(board, skills):
    for color_key, skill in skills.items():
        color = chess.WHITE if color_key == 'white' else chess.BLACK
        if skill == 'theocracy':
            for sq in chess.SQUARES:
                piece = board.piece_at(sq)
                if piece and piece.color == color and piece.piece_type == chess.QUEEN:
                    board.remove_piece_at(sq)

def increment_skill_count(gameData, skill_name, turn_color):
    color_key = "white" if turn_color else "black"
    
    if skill_name not in gameData:
        gameData[skill_name] = {"white": 0, "black": 0}
    gameData[skill_name][color_key] += 1

def get_skill_count(gameData, skill_name, turn_color):
    color_key = "white" if turn_color else "black"
    
    if skill_name not in gameData:
        gameData[skill_name] = {"white": 0, "black": 0}
    return gameData[skill_name][color_key]

def reset_skill_count(gameData, skill_name, turn_color):
    color_key = "white" if turn_color else "black"
    
    if skill_name not in gameData:
        gameData[skill_name] = {"white": 0, "black": 0}
    gameData[skill_name][color_key] = 0

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/api/localization/<language>/skills', methods=['GET'])
def get_skills(language):
    skills = localized_text.get_all_skills(language)
    skills = replace_skills_placeholder_in_localized_text(skills)
    return jsonify(skills)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('lobby'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            return render_template('register.html', error="Username already exists")
        users[username] = password
        save_users(users)
        leaderboard = load_leaderboard()
        leaderboard[username] = 0
        save_leaderboard(leaderboard)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/lobby', methods=['GET', 'POST'])
def lobby():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        room = request.form['room']
        skill = request.form['skill']
        session['skill'] = skill
        return redirect(url_for('chess_room', room=room))
    return render_template('lobby.html', username=session['username'])

@app.route('/chess/<room>')
def chess_room(room):
    if 'username' not in session:
        return redirect(url_for('login'))
    skill = session.get('skill', 'none')
    return render_template('chess.html', room=room, username=session['username'], skill=skill)

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    leaderboard = load_leaderboard()
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    return render_template('leaderboard.html', leaderboard=sorted_leaderboard, username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('skill', None)
    return redirect(url_for('login'))

@socketio.on('join')
def on_join(data):
    room = data['room']
    username = data['username']
    skill = data['skill']
    join_room(room)
    if room not in games:
        games[room] = {'board': None, 'turn': 'w', 'players': {}, 'usernames': {}, 'skills': {}, 'data': {}}
    game = games[room]
    if len(game['players']) < 2:
        color = 'white' if len(game['players']) == 0 else 'black'
        game['players'][color] = request.sid
        game['usernames'][color] = username
        game['skills'][color] = skill
        emit('message', {'msg': f'Joined as {color}'}, to=request.sid)
        if len(game['players']) == 1:
            emit('waiting', to=request.sid)
        if len(game['players']) == 2:
            board = chess.Board()
            apply_skills_before_start(board, game['skills'])
            game['board'] = board
            game['turn'] = 'w'
            for col, sid in game['players'].items():
                opponent = game['usernames']['black' if col == 'white' else 'white']
                emit('start', {'color': col, 'opponent': opponent, 'fen': board.fen()}, to=sid)
            emit('turn', {'turn': 'white'}, room=room)
    else:
        emit('message', {'msg': 'Room full'}, to=request.sid)

@socketio.on('make_move')
def on_make_move(data):
    room = data['room']
    move_data = data['move']
    if room not in games:
        return
    game = games[room]
    sid = request.sid
    for col, s in game['players'].items():
        if s == sid:
            color = col
            break
    else:
        return
    turn_color = 'white' if game['turn'] == 'w' else 'black'
    opponent_color = 'black' if game['turn'] == 'w' else 'white'
    your_skill = game['skills'][color]
    opponent_skill = game['skills'][opponent_color]
    if color != turn_color:
        emit('message', {'msg': 'Not your turn'}, to=sid)
        return
    from_sq = chess.parse_square(move_data['from'])
    to_sq = chess.parse_square(move_data['to'])
    move = chess.Move(from_sq, to_sq)
    if is_promotion(game['board'], from_sq, to_sq):
        move.promotion = chess.QUEEN
    
    is_second_move = get_skill_count(game, your_skill, color) > 0
    
    if is_move_legal(
        game,
        game['board'], 
        move, 
        your_skill, 
        opponent_skill,
        second_move=is_second_move
    ):
        # Prepare move details for client animation
        promotion = move.promotion.str.lower() if move.promotion else None
        captured_sq = None
        rook_from = None
        rook_to = None
        is_en = game['board'].is_en_passant(move)
        if is_en:
            direction = -8 if game['board'].turn == chess.WHITE else 8
            captured_sq = chess.square_name(to_sq + direction)
        elif game['board'].is_capture(move):
            captured_sq = move_data['to']
        if game['board'].is_castling(move):
            is_white = game['board'].turn == chess.WHITE
            kingside = to_sq == chess.G1 if is_white else to_sq == chess.G8
            if kingside:
                rook_from = chess.square_name(chess.H1 if is_white else chess.H8)
                rook_to = chess.square_name(chess.F1 if is_white else chess.F8)
            else:
                rook_from = chess.square_name(chess.A1 if is_white else chess.A8)
                rook_to = chess.square_name(chess.D1 if is_white else chess.D8)
                
        is_extra_move = check_extra_move(game, game['board'], move, your_skill, opponent_skill)
        
        game['board'].push(move)
        is_opponent_in_check = False
        
        if is_extra_move:
            game['board'].turn = not game['board'].turn
            
            if your_skill in ["rampage", "blitzkrieg"]:
                increment_skill_count(game, your_skill, color)
                
                if your_skill == "rampage":
                    game["data"]["rampage"] = move.to_square
                if your_skill == "blitzkrieg":
                    game["data"]["blitzkrieg"] = move.to_square
        else:
            game['turn'] = 'b' if game['turn'] == 'w' else 'w'
            is_opponent_in_check = is_check(game['board'], opponent_skill, your_skill)
            if your_skill in ["rampage", "blitzkrieg"]:
                reset_skill_count(game, your_skill, color)
        
        if is_checkmate(game, game['board'], opponent_skill, your_skill):
            winner = color
            leaderboard = load_leaderboard()
            leaderboard[game['usernames'][winner]] += 1
            save_leaderboard(leaderboard)
            emit('game_over', {'winner': winner, 'msg': f'{winner.capitalize()} wins by checkmate!'}, room=room)
            del games[room]
            return
        emit('move_made', {
            'fen': game['board'].fen(),
            'turn': game['turn'],
            'move': {
                'from': move_data['from'],
                'to': move_data['to'],
                'promotion': promotion,
                'captured_sq': captured_sq,
                'rook_from': rook_from,
                'rook_to': rook_to,
                'in_check': is_opponent_in_check
            }
        }, room=room)

@socketio.on('resign')
def on_resign(data):
    room = data['room']
    if room not in games:
        return
    game = games[room]
    sid = request.sid
    for col, s in game['players'].items():
        if s == sid:
            loser = col
            break
    else:
        return
    winner = 'black' if loser == 'white' else 'white'
    leaderboard = load_leaderboard()
    leaderboard[game['usernames'][winner]] += 1
    save_leaderboard(leaderboard)
    emit('game_over', {'winner': winner, 'msg': f'{winner.capitalize()} wins by resignation!'}, room=room)
    del games[room]

if __name__ == '__main__':
    init_files()
    socketio.run(app, host='0.0.0.0', debug=True)