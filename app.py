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

    standard_check = board.is_check()

    theocracy_check = False
    if opponent_skill == 'theocracy':
        board_copy = board.copy()
        theocracy_check = is_king_attacked_by_theocracy(board_copy)

    is_in_check_overall = standard_check or theocracy_check

    immunity = False
    if your_skill == 'theocracy':
        immunity = immunity or is_protected_by_theocracy(board, board.turn)
            
    return is_in_check_overall and not immunity

def is_checkmate(board, your_skill, opponent_skill):
        if not is_check(board, your_skill, opponent_skill):
            return False
        return not any(board.legal_moves())

def is_path_clear(board, from_sq, to_sq):
    for sq in get_squares_between(from_sq, to_sq):
        if board.piece_at(sq):
            return False
    return True

def is_path_clear_blitzkrieg(board, from_sq, to_sq, turn_color):
    for sq in get_squares_between(from_sq, to_sq):
        if board.piece_at(sq).color != turn_color:
            return False
    return True

def is_protected_by_theocracy(board, turn_color):
    return board.pieces(chess.BISHOP, turn_color).__len__() > 0

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

def is_move_legal(board: chess.Board, move: chess.Move, your_skill: str, opponent_skill: str, *args, **kwargs) -> bool:
    """
    Checks if a move is legal, considering standard rules and custom skills.
    This version is fixed to prevent the board.turn side-effect bug.
    """
    
    # --- Step 0: Handle Special Cases like Rampage's Second Move ---
    is_second_move = kwargs.get("second_move", False)
    if is_second_move:
        # For a second move, only the skill's specific rules apply.
        # We assume the rampage function also checks for basic legality.
        if your_skill == 'rampage':
            # We pass the original board turn here.
            return is_legal_second_move_no_capture_and_check(board, move.from_square, move.to_square, board.turn)
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

def apply_skills(board, skills):
    for color_key, skill in skills.items():
        color = chess.WHITE if color_key == 'white' else chess.BLACK
        if skill == 'theocracy':
            for sq in chess.SQUARES:
                piece = board.piece_at(sq)
                if piece and piece.color == color and piece.piece_type == chess.QUEEN:
                    board.remove_piece_at(sq)

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
        games[room] = {'board': None, 'turn': 'w', 'players': {}, 'usernames': {}, 'skills': {}}
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
            apply_skills(board, game['skills'])
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
    if color != turn_color:
        emit('message', {'msg': 'Not your turn'}, to=sid)
        return
    from_sq = chess.parse_square(move_data['from'])
    to_sq = chess.parse_square(move_data['to'])
    move = chess.Move(from_sq, to_sq)
    if is_promotion(game['board'], from_sq, to_sq):
        move.promotion = chess.QUEEN
    
    if is_move_legal(game['board'], move, game['skills'][color], game['skills'][opponent_color]):
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
        game['board'].push(move)
        if is_checkmate(game['board'], game['skills'][color], game['skills'][opponent_color]):
            winner = opponent_color
            leaderboard = load_leaderboard()
            leaderboard[game['usernames'][winner]] += 1
            save_leaderboard(leaderboard)
            emit('game_over', {'winner': winner, 'msg': f'{winner.capitalize()} wins by checkmate!'}, room=room)
            del games[room]
            return
        game['turn'] = 'b' if game['turn'] == 'w' else 'w'
        emit('move_made', {
            'fen': game['board'].fen(),
            'turn': game['turn'],
            'move': {
                'from': move_data['from'],
                'to': move_data['to'],
                'promotion': promotion,
                'captured_sq': captured_sq,
                'rook_from': rook_from,
                'rook_to': rook_to
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