from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, join_room, emit, disconnect
from copy import deepcopy
import os
import json
import secrets
from typing import List, Dict, Union, Callable, Any, Optional

import read_localized_text as localized_text

from card_related.card_driver import Card, Deck
from card_related.system_driver import System
from card_related.static_card_base import StaticCardBase, StaticSystemBase

from chess_related.board import Board
from chess_related.piece import BasePiece, KingPiece, QueenPiece, BishopPiece, KnightPiece, RookPiece, PawnPiece, NonePiece
from chess_related.chess_utils import *

from controller_related.event_controller import EventHandler

from player_related.player import Player
from controller import GameController

# Directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
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
socketio = SocketIO(app, async_mode='eventlet')

global_event_handler = EventHandler()


# Simulated database
USERS_FILE = 'users.json'
LEADERBOARD_FILE = 'leaderboard.json'
PLAYER_DECK_FILE = 'player_decks.json'

games: Dict[str, Dict[str, Union[str, Board, Dict[str, Player], GameController]]] = {}

# Decorators
def set_event_handler(event_name: str):
    """
    Decorator to register a function as an event listener.
    Usage:
        @set_event_handler("select")
        def handle_select_event(data):
            ...
    """
    def decorator(func):
        global_event_handler.on(event_name, func)
        return func  # Return the original function (useful if needed elsewhere)
    return decorator

# Helper functions

def get_full_file_path(dirname: str, filename: str) -> str:
    return os.path.join(BASE_DIR, dirname, filename)

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

def change_json_card_object_into_card_id_list(cards: List) -> List[str]:
    return [card["id"] for card in cards]

def change_json_card_id_list_into_card_object(card_ids: List[str]) -> List[Card]:
    card_base = StaticCardBase.instance()
    card_list: List[Card] = []
    for card_id in card_ids:
        card = card_base.get_by_id(card_id)
        if card:
            card_list.append(card)
        else:
            return []
    return card_list

def change_card_objects_into_json_card_object(cards: List[Card]) -> List[Dict[str, str]]:
    return [
        {
            "name": card.name,
            "description": card.desc,
            "img": card.img,
            "cost": card.cost,
            "type": card.type,
            "id": card.id
        } for card in cards
    ]

def change_json_system_object_into_system_id(system: Any) -> str:
    return system["id"]

def change_json_system_id_into_system_object(system_id: str) -> Optional[System]:
    system_base = StaticSystemBase.instance()
    system = system_base.get_by_id(system_id)
    return system if system else None

def get_active_deck_details(username: str) -> Optional[Dict[str, Union[str, List[str]]]]:
    try:
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
            decks: Dict[str, Dict] = json.load(f)
        current_player_deck = next((deck for deck in decks[username] if deck.get("active") == "true"), None)
        return current_player_deck
    except:
        return None

def server_start():
    """
    Called once at server startup.
    Loads all cards from localization files and registers them globally.
    Prints all loaded cards for verification.
    """
    init_files()
    # 1. Load raw data
    raw_cards_data = get_data_with_localization("en", localized_text.get_cards)
    cards_data = list(raw_cards_data.values())

    print(f"Found {len(cards_data)} card definitions in localization file.\n")
    
    raw_systems_data = get_data_with_localization("en", localized_text.get_systems)
    systems_data = list(raw_systems_data.values())

    print(f"Found {len(systems_data)} system definitions in localization file.\n")

    # 2. Convert to Card objects safely
    card_objects = []
    for card in cards_data:
        card_obj = Card(
            name=card['name'],
            id=card['id'],
            img=card['img'],
            desc=card.get('description', 'No description'),
            cost=int(card.get('cost') or 0),  # safe int conversion
            type=card.get('type', 'attack')
        )
        card_objects.append(card_obj)
        
    system_objects = []
    for system in systems_data:
        system_obj = System(
            name=system['name'],
            id=system['id'],
            img=system['img'],
            desc=system.get('description', 'No description')
        )
        system_objects.append(system_obj)

    # 3. Register all cards
    card_base = StaticCardBase.instance()
    card_base.register_many(card_objects)

    # 4. Register all systems
    system_base = StaticSystemBase.instance()
    system_base.register_many(system_objects)
    
    # 5. Register global event handler
    global_event_handler.on("select", handle_select_event)

# 在模組載入時自動執行 server_start()
server_start()

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

# App routes

@app.route('/chess')
def chess():
    return render_template("chess.html")

@app.route('/api/session')
def get_session():
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
    username = session.get("username", "Player")
    cards = get_data_with_localization(language, localized_text.get_cards, username=username)
    return jsonify(cards)

@app.route('/api/localization/<language>/systems', methods=['GET'])
def get_systems(language: str):
    username = session.get("username", "Player")
    systems = get_data_with_localization(language, localized_text.get_systems, username=username)
    return jsonify(systems)

@app.route('/api/get_deck')
def get_deck():
    username = session.get("username", "Player")
    try:
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
            decks = json.load(f)
        return jsonify(decks[username])
    except:
        return jsonify([])

@app.route('/api/save_deck', methods=['POST'])
def save_deck():
    data = request.get_json()
    username = session.get("username", "Player")
    
    deck_id = data["id"]
    deck_name = data["name"]
    deck_cards = change_json_card_object_into_card_id_list(data["cards"])
    deck_system = change_json_system_object_into_system_id(data["system"])
    deck_active = data["active"]
    
    with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
        try:
            decks = json.load(f)
        except:
            decks = {}
    
        if username in decks:
            player_original_decks = decks[username]
            if deck_id < player_original_decks.__len__():
                player_original_decks[deck_id] = {
                    "name": deck_name,
                    "system": deck_system,
                    "deck": deck_cards,
                    "active": deck_active
                }
            else:
                player_original_decks.append({
                    "name": deck_name,
                    "system": deck_system,
                    "deck": deck_cards,
                    "active": deck_active
                })
        else:
            decks[username] = [{
                "name": deck_name,
                "system": deck_system,
                "deck": deck_cards,
                "active": deck_active
            }]
        
    with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'w') as f:
        json.dump(decks, f)
    
    return jsonify({"success": True, "decks": decks[username]})

@app.route('/api/delete_deck', methods=['POST'])
def delete_deck():
    data = request.get_json()
    username = session.get("username", "Player")
    
    try:
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
            try:
                decks = json.load(f)
            except:
                decks = {}
                
            deck_id = int(data["id"])
                
        
            if username in decks:
                player_original_decks = decks[username]
                
                if deck_id < 0 or deck_id >= len(player_original_decks):
                    return jsonify({"success": False, "error": "Invalid deck ID"})
                
                del player_original_decks[deck_id]
        
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'w') as f:
            json.dump(decks, f)
    
        return jsonify({"success": True, "decks": decks[username]})
    except:
        return jsonify({"success": False, "error": "Invalid deck ID"})

@app.route('/api/set_active_deck', methods=['POST'])
def set_active_deck():
    data = request.get_json()
    username = session.get("username", "Player")
    
    try:
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'r') as f:
            try:
                decks = json.load(f)
            except:
                decks = {}
                
            deck_id = int(data["id"])
                
        
            if username in decks:
                player_original_decks = decks[username]
                
                if deck_id < 0 or deck_id >= len(player_original_decks):
                    return jsonify({"success": False, "error": "Invalid deck ID"})
                
                i = 0
                for deck in player_original_decks:
                    if i == deck_id:
                        deck["active"] = "true"
                    else:
                        deck["active"] = "false"
                    i += 1
        
        with open(get_full_file_path(DATABASE_DIR, PLAYER_DECK_FILE), 'w') as f:
            json.dump(decks, f)
    
        return jsonify({"success": True, "decks": decks[username]})
    except:
        return jsonify({"success": False, "error": "Invalid deck ID"})

@app.route('/chess')
def chess_room():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chess.html', username=session['username'])

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

# Socket.IO stuffs
@socketio.on('connect')
def on_connect():
    pass

@socketio.on('join')
def on_join(data):
    if 'username' not in session:
        disconnect()
        return

    username = session['username']
    sid = request.sid

    # Client sends room, but we validate against session (set in /chess/<room>)
    room = data.get('room')
    if not room:
        emit("error", {'msg': "Invalid or unauthorized room"}, to=sid)
        disconnect()
        return

    join_room(room)

    if room not in games:
        games[room] = {
            'controller': None,
            'board': None,
            'turn': 'white',
            'players': {}  # color → Player object
        }

    game = games[room]

    # Load and validate active deck
    current_player_deck = get_active_deck_details(username)
    if not current_player_deck:
        emit("error", {'msg': "No active deck selected. Please go to Deck Builder."}, to=sid)
        disconnect()
        return

    deck_cards = change_json_card_id_list_into_card_object(current_player_deck["deck"])
    if not deck_cards:
        emit("error", {'msg': "Your deck contains invalid cards."}, to=sid)
        disconnect()
        return

    deck = Deck(deck_cards)

    system = change_json_system_id_into_system_object(current_player_deck["system"])
    if not system:
        emit("error", {'msg': "Invalid system in active deck."}, to=sid)
        disconnect()
        return

    # Prevent more than 2 players
    if len(game['players']) >= 2:
        emit('message', {'msg': 'This room is full'}, to=sid)
        return

    # Assign color
    color = 'white' if len(game['players']) == 0 else 'black'

    # Store player
    game['players'][color] = Player(
        username=username,
        request_sid=sid,
        deck=deck,
        system=system
    )
    
    session['room'] = room

    emit('message', {'msg': f'You joined as {color.capitalize()}'}, to=sid)

    if len(game['players']) == 1:
        emit('waiting', to=sid)
    else:
        # Game starts!
        board = Board()
        game['board'] = board
        game['turn'] = 'white'

        white_player = game['players']['white']
        black_player = game['players']['black']
        
        game['controller'] = GameController(
            room=room,
            board=board, 
            players={"white": white_player, "black": black_player},
            event_handler=global_event_handler
        )
        
        game['controller'].game_start()

        # Notify both players
        emit('start', {
            'color': 'white',
            'opponent': black_player.username
        }, to=white_player.sid)

        emit('start', {
            'color': 'black',
            'opponent': white_player.username
        }, to=black_player.sid)

        emit('turn', {'turn': 'white'}, room=room)

@socketio.on('get_client_game_data')
def on_get_client_game_data(data):
    sid = request.sid
    
    if 'username' not in session or 'room' not in session:
        emit("error", {'msg': "Session expired. Please log in again."}, to=sid)
        disconnect()
        return

    username = session['username']
    room = session['room']

    if not room or room not in games:
        emit("error", {'msg': "Session expired. Please log in again."}, to=sid)
        disconnect()
        return
    
    game = games[room]

    white_player: Player = game['players']['white']
    black_player: Player = game['players']['black']
    
    players_by_username = {
        white_player.username: white_player,
        black_player.username: black_player
    }

    requesting_player = players_by_username.get(username)
    if not requesting_player:
        emit("error", {'msg': "Session expired. Please log in again."}, to=sid)
        disconnect()
        return

    # Determine enemy automatically
    requesting_enemy_player = white_player if requesting_player is black_player else black_player
    
    requesting_player_hand = change_card_objects_into_json_card_object(requesting_player.hand)
    requesting_player_prestige = requesting_player.prestige
    requesting_enemy_hand_count = len(requesting_enemy_player.hand)
    requesting_enemy_prestige = requesting_enemy_player.prestige

    emit("client_game_data_got", {
        "friendlyName": requesting_player.username,
        "friendlyHand": requesting_player_hand,
        "friendlyPrestige": requesting_player_prestige,
        "enemyName": requesting_enemy_player.username,
        "enemyHandCount": requesting_enemy_hand_count,
        "enemyPrestige": requesting_enemy_prestige
    }, to=sid)

@socketio.on('played_card')
def on_card_try_played(data):
    """
    Frontend tells server: "Player wants to play a card from hand[index]"
    """
    played_card_index = data.get('played_card_in_hand_index')
    if played_card_index is None:
        return

    sid = request.sid
    username = session.get('username')
    if not username:
        emit("error", {"msg": "Not logged in"}, to=sid)
        return

    room = session.get('room')
    if not room or room not in games:
        emit("error", {"msg": "Invalid room"}, to=sid)
        return

    game = games[room]
    controller = game.get('controller')
    if not controller:
        emit("error", {"msg": "Game not started yet"}, to=sid)
        return

    # Find which player is trying to play
    current_player_color = controller.current_player
    current_player_obj = game['players'].get(current_player_color)

    if current_player_obj.sid != sid:
        emit("message", {"msg": "It's not your turn!"}, to=sid)
        return

    # Ask controller to validate and play the card
    success = controller.try_play_card_with_index_in_hand(played_card_index)

    if not success:
        emit("reject_play_card", {"msg": "Cannot play this card"}, to=sid)

@socketio.on('chosen_by_selector')
def on_chosen_by_selector(data):
    room = session.get('room')
    sid = request.sid
    selected = data.get('selected')

    if not room or room not in games:
        emit("error", {"msg": "Invalid room"}, to=sid)
        return

    controller: GameController = games[room].get('controller')
    print(selected)
    if controller:
        # Forward to controller (resolves waiting select())
        controller.resolve_selection(selected)

@socketio.on('make_move')
def on_make_move(data):
    move_data = data['move']
    sid = request.sid

    room = session.get('room')

    if not room or room not in games:
        emit("error", {"msg": "Invalid room"}, to=sid)
        return
    
    game = games[room]
    controller: GameController = game.get("controller")
    
    # Find which player is trying to play
    current_player_color = controller.current_player
    current_player_obj = game['players'].get(current_player_color)

    if current_player_obj.sid != sid:
        emit("error", {"msg": "It's not your turn!"}, to=sid)
        return
    
    print("Received move request!", move_data)
    
    promotion = move_data["promotion"]
    move_result = controller.move_piece({
            'from': move_data['from'],
            'to': move_data['to'],
            'promotion': promotion,
    })
    success = move_result["success"]
    en_passant = move_result["en_passant"]
    win = move_result["win"]
    
    if win:
        emit('move_made', {
            'move': {
                'from': move_data['from'],
                'to': move_data['to'],
                'promotion': promotion,
                'en_passant': en_passant,
                'success': success
            }
        }, room=room)
        emit('game_over', {
            'winner': current_player_color,
            'msg': f'{current_player_obj.username} wins!'
        }, room=room)
        del games[room]
    elif success:
        emit('move_made', {
            'move': {
                'from': move_data['from'],
                'to': move_data['to'],
                'promotion': promotion,
                'en_passant': en_passant,
                'success': success
            }
        }, room=room)
    else :
        emit('move_fails', {
            'move': {
                'from': move_data['from'],
                'to': move_data['to'],
                'promotion': promotion,
                'en_passant': en_passant,
                'success': success
            }
        }, to=sid)

@socketio.on('request_turn_end')
def on_turn_end(data):
    sid = request.sid
    username = session.get('username')
    if not username:
        emit("error", {"msg": "Not logged in"}, to=sid)
        return

    room = session.get('room')
    if not room or room not in games:
        emit("error", {"msg": "Invalid room"}, to=sid)
        return

    game = games[room]
    controller = game.get('controller')
    if not controller:
        emit("error", {"msg": "Game not started yet"}, to=sid)
        return

    # Find which player is trying to play
    current_player_color = controller.current_player
    current_player_obj = game['players'].get(current_player_color)

    if current_player_obj.sid != sid:
        emit("message", {"msg": "It's not your turn!"}, to=sid)
        return
    
    controller.turn_end()
    
    emit("turn_end", {
        "current_color": controller.current_player
    }, room=room)
    
    controller.turn_start()

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

@socketio.on('disconnect')
def on_disconnect():
    """
    Automatically clean up the game room if a player disconnects.
    Called whenever a client loses connection.
    """
    sid = request.sid
    username = session.get('username')
    print(f"Player {username} is found disconnected.")

    if not username:
        return  # Not logged in, nothing to clean

    room = session.get('room')
    print(f"Checking if room {room} exists...")
    if not room or room not in games:
        return

    game = games[room]
    print(f"Checking if game exists...")

    # Find which player disconnected
    disconnected_color = None
    for color, player in game['players'].items():
        if player.sid == sid:
            disconnected_color = color
            break

    if not disconnected_color:
        return  # Wasn't a player in the game

    # Notify the remaining player (if any) that opponent left
    opponent_color = 'black' if disconnected_color == 'white' else 'white'
    opponent_player = game['players'].get(opponent_color)

    if opponent_player:
        emit('game_over', {
            'winner': opponent_color,
            'msg': f'{username} disconnected. You win by forfeit!'
        }, to=opponent_player.sid)

    # Optional: Update leaderboard (win by forfeit)
    leaderboard = load_leaderboard()
    if not leaderboard:
        leaderboard = {}
    if opponent_player:
        winner_name = opponent_player.username
        leaderboard[winner_name] = leaderboard.get(winner_name, 0) + 1
        save_leaderboard(leaderboard)
    
    controller: GameController = games[room].get('controller')
    if controller and hasattr(controller, '_pending_selection'):
        controller.cancel_selection()

    # Clean up the room
    print(f"Player {username} ({disconnected_color}) confirmed be disconnected. Destroying room {room}")
    del games[room]

    # Optional: clear session room
    session.pop('room', None)

# Event listening bridges

# Bridge: open selector UI
@set_event_handler("select")
def handle_select_event(data):
    room = data['room']
    
    if not room or room not in games:
        return None
    
    game = games[room]
    controller: GameController = game["controller"]
    player = controller.players.get(controller.current_player)
    
    if not player:
        return None
    
    sid = player.sid
    
    emit("open_selector", {
        "select_type": data["select_type"],
        "select_from_item": data["select_from_item"],
        "min": data["min"],
        "max": data["max"],
        "current_player": data["current_player"]
    }, to=sid)

# Bridge: send chess piece placement signal
@set_event_handler("place_piece")
def handle_piece_placement_event(data):
    room = data['room']
    
    if not room or room not in games:
        return None
    
    emit("place_piece", {
        "piece": data["piece"],
        "color": data["color"],
        "position": data["position"]
    }, room=room)

# Bridge: send chess piece removal signal
@set_event_handler("remove_piece")
def handle_piece_removal_event(data):
    room = data['room']
    
    if not room or room not in games:
        return None
    
    emit("remove_piece", {
        "position": data['position']
    }, room=room)


# Bridge: validate card playing
@set_event_handler("card_play_accepted")
def handle_card_play_accepted(data):
    room = data['room']
    
    if not room or room not in games:
        return None
    
    emit("accept_play_card", {
        "card_id": data['card_id'],
        "player_color": data['player_color'],
        "hand_index": data['hand_index']
    }, room=room)

# Bridge: update both side's hand
@set_event_handler("update_hand")
def handle_hand_updated(data):
    room = data.get('room')

    # 1. Early exit with clear conditions
    if not room or room not in games:
        return None
    
    game = games.get(room)

    controller: GameController = game["controller"]
    white = controller.players.get(controller.PLAYER_COLOR_WHITE)
    black = controller.players.get(controller.PLAYER_COLOR_BLACK)

    if not (white and black):
        return None

    # 2. Define the hands mapping
    hands = {
        "white": data.get("white_hand", []),
        "black": data.get("black_hand", [])
    }

    # 3. Create a configuration for targeted emits
    # Each entry: (Target Player SID, Friendly Hand, Enemy Hand Count)
    update_configs = [
        (white.sid, change_card_objects_into_json_card_object(hands["white"]), len(hands["black"])),
        (black.sid, change_card_objects_into_json_card_object(hands["black"]), len(hands["white"]))
    ]

    # 4. Execute emissions
    for sid, friendly_hand, enemy_count in update_configs:
        emit("update_hand", {
            "friendlyHand": friendly_hand,
            "enemyHandCount": enemy_count
        }, to=sid)

# Bridge: update both side's prestige
@set_event_handler("update_prestige")
def handle_prestige_updated_event(data):
    room = data['room']
    
    if not room or room not in games:
        return None
    
    emit("update_prestige", {
        "white": data["white"],
        "black": data["black"],
    }, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)