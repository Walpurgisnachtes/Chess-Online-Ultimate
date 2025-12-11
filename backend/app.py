from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, join_room, emit
import os
import json
import secrets
from typing import List, Dict, Union, Callable, Optional 

import read_localized_text as localized_text

from card_related.card_driver import Card, Deck
from card_related.static_card_base import StaticCardBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from player_related.player import Player

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CSS_DIR = os.path.join("static", "css")
IMG_DIR = os.path.join("static", "img")
JS_DIR = os.path.join("static", "js")
TEMP_DIR = "templates"
DATABASE_DIR = os.path.join("database", "website")


app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.json.sort_keys = False
app.secret_key = secrets.token_bytes(32)
socketio = SocketIO(app)


# Simulated database
USERS_FILE = 'users.txt'
LEADERBOARD_FILE = 'leaderboard.txt'
PLAYER_DECK_FILE = 'player_decks.txt'

games: Dict[str, Dict[str, Union[str, Board, Player]]] = {}

def get_full_file_path(dirname: str, filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), dirname, filename)

def init_files():
    if not os.path.exists(get_full_file_path(DATABASE_DIR, USERS_FILE)):
        with open(get_full_file_path(DATABASE_DIR, USERS_FILE), 'w') as f:
            json.dump({}, f)
    if not os.path.exists(get_full_file_path(DATABASE_DIR, LEADERBOARD_FILE)):
        with open(get_full_file_path(DATABASE_DIR, LEADERBOARD_FILE), 'w') as f:
            json.dump({}, f)

def load_users():
    with open(get_full_file_path(DATABASE_DIR, USERS_FILE), 'r') as f:
        return json.load(f)

def save_users(users):
    with open(get_full_file_path(DATABASE_DIR, USERS_FILE), 'w') as f:
        json.dump(users, f)

def load_leaderboard():
    with open(get_full_file_path(DATABASE_DIR, LEADERBOARD_FILE), 'r') as f:
        return json.load(f)

def save_leaderboard(leaderboard):
    with open(get_full_file_path(DATABASE_DIR, LEADERBOARD_FILE), 'w') as f:
        json.dump(leaderboard, f)

def replace_placeholders_in_localized_text(texts_dict: Dict[str, Dict[str, str]], username: str = "Player"):
    for text_key in texts_dict:
        text_object = texts_dict[text_key]
        if "description" not in text_object:
            continue
        text_content = text_object["description"]
        
        replaced = text_content \
            .replace("[linebreak]", "<br />") \
            .replace("[username]", username)
        
        texts_dict[text_key]["description"] = replaced
    
    return texts_dict

def get_data_with_localization(language: str, get_method: Callable[..., Dict[str, Dict[str, str]]], **kwargs):
    username = kwargs["username"] if "username" in kwargs else "Player"
    
    data = localized_text.get_all_data(get_method, language)
    data = replace_placeholders_in_localized_text(data, username)
    return data


def server_start():
    """
    Called once at server startup.
    Loads all cards from localization files and registers them globally.
    Prints all loaded cards for verification.
    """
    # 1. Load raw data
    data = get_data_with_localization("en", localized_text.get_cards)
    cards_data = list(data.values())

    print(f"Found {len(cards_data)} card definitions in localization file.\n")

    # 2. Convert to Card objects safely
    card_objects = []
    for card in cards_data:
        card_obj = Card(
            name=card['name'],
            id=int(card['id']),
            desc=card.get('description', 'No description'),
            cost=int(card.get('cost') or 0)  # safe int conversion
        )
        card_objects.append(card_obj)

    # 3. Register all cards
    card_base = StaticCardBase.instance()
    card_base.register_many(card_objects)

    # 4. FINAL DEBUG: Print every card using its __str__
    print("=" * 60)
    print("ALL CARDS LOADED AND REGISTERED")
    print("=" * 60)
    for card in card_objects:
        print(card)  # This calls card.__str__() automatically
    print("=" * 60)
    print(f"Total cards registered: {len(card_base)}")
    print("Server startup complete!\n")

@app.route('/')
def no_path():
    return redirect(url_for("home"))

@app.route('/home')
def home():
    if 'username' in session:
        return redirect(url_for('lobby'))
    return redirect(url_for('login'))
    
@app.route('/lobby')
def lobby():
    if 'username' not in session:
        flash("Please log in first")
        return redirect(url_for('login'))
    return render_template('lobby.html', username=session['username'])

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


@app.route('/chess')
def chess():
    return render_template("chess.html")

@app.route('/api/session')
def get_session():
    session["username"] = "Matthew"
    return jsonify({
        "logged_in": "username" in session,
        "username": session.get("username")
    })

@app.route('/api/request_rooms')
def get_rooms():
    pass

@app.route('/api/localization/<language>/skills', methods=['GET'])
def get_skills(language: str):    
    username = session.get("username", "Player")
    skills = get_data_with_localization(language, localized_text.get_skills, username=username)
    return jsonify(skills)

@app.route('/api/localization/<language>/cards', methods=['GET'])
def get_cards(language: str):
    """Get player current hand cards"""
    username = session.get("username", "Player")
    cards = get_data_with_localization(language, localized_text.get_cards, username=username)
    return jsonify(cards)

@app.route('/api/get_deck')
def get_deck():
    try:
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
            decks = json.load(f)
        return jsonify(decks)
    except:
        return jsonify({})

@app.route('/api/save_deck', methods=['POST'])
def save_deck():
    data = request.get_json()
    decks = session.get('user_decks', [])
    
    if data.get('id') is not None and data['id'] < len(decks):
        decks[data['id']] = data
    else:
        decks.append(data)
    
    session['user_decks'] = decks
    return jsonify({"success": True, "decks": decks})

@app.route('/chess/<room>')
def chess_room(room):
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chess.html', room=room, username=session['username'])

@app.route('/deckbuilder')
def deckbuilder():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('deck_builder.html')

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
    return redirect(url_for('login'))

@socketio.on('join')
def on_join(data):
    room = data['room']
    username = data['username']
    skill = data['skill']
    join_room(room)
    if room not in games:
        games[room] = {
            'board': None, 
            'turn': 'white', 
            'players': {}
        }
    game = games[room]
    if len(game['players']) < 2:
        color = 'white' if len(game['players']) == 0 else 'black'
        game['players'][color] = Player(
            username=username, 
            request_sid=request.sid,
            system_id=skill,
            deck=None
        )
        emit('message', {'msg': f'Joined as {color}'}, to=request.sid)
        if len(game['players']) == 1:
            emit('waiting', to=request.sid)
        if len(game['players']) == 2:
            board = Board()
            game['board'] = board
            game['turn'] = 'white'
            for col, player in game['players'].items():
                sid = player.sid
                opponent = game['usernames']['black' if col == 'white' else 'white']
                emit('start', {'color': col, 'opponent': opponent}, to=sid)
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
    
    promotion = None
    is_opponent_in_check = False
    
    emit('move_made', {
        'room': room,
        'move': {
            'from': move_data['from'],
            'to': move_data['to'],
            'promotion': promotion,
            'enemy_in_check': is_opponent_in_check
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
    server_start()
    socketio.run(app, host='0.0.0.0', debug=True)