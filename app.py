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

def is_path_clear(board, from_sq, to_sq):
    for sq in get_squares_between(from_sq, to_sq):
        if board.piece_at(sq):
            return False
    return True

def is_promotion(board, from_sq, to_sq):
    piece = board.piece_at(from_sq)
    if piece and piece.piece_type == chess.PAWN:
        rank = chess.square_rank(to_sq)
        if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
            return True
    return False

def is_majesty_legal(board, move, is_majesty):
    if board.is_legal(move):
        return True
    if not is_majesty:
        return False
    if board.piece_at(move.from_square).piece_type != chess.KING:
        return False
    if not is_queen_like_move(move.from_square, move.to_square):
        return False
    if not is_path_clear(board, move.from_square, move.to_square):
        return False
    target = board.piece_at(move.to_square)
    if target and target.color == board.turn:
        return False
    if board.is_attacked_by(not board.turn, move.to_square):
        return False
    board.push(move)
    in_check = board.is_check()
    board.pop()
    if in_check:
        return False
    return True

def apply_skills(board, skills):
    for color_key, skill in skills.items():
        if skill == 'majesty':
            color = chess.WHITE if color_key == 'white' else chess.BLACK
            for sq in chess.SQUARES:
                piece = board.piece_at(sq)
                if piece and piece.color == color and piece.piece_type != chess.KING:
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
    if color != turn_color:
        emit('message', {'msg': 'Not your turn'}, to=sid)
        return
    from_sq = chess.parse_square(move_data['from'])
    to_sq = chess.parse_square(move_data['to'])
    move = chess.Move(from_sq, to_sq)
    if is_promotion(game['board'], from_sq, to_sq):
        move.promotion = chess.QUEEN
    is_majesty = game['skills'][color] == 'majesty'
    if is_majesty_legal(game['board'], move, is_majesty):
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
        if game['board'].is_checkmate():
            winner = color
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