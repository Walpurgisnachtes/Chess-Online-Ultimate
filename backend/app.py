from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, join_room, emit
import os
import json
import secrets
from typing import Dict

import read_localized_text as localized_text

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CSS_DIR = os.path.join("static", "css")
IMG_DIR = os.path.join("static", "img")
JS_DIR = os.path.join("static", "js")
TEMP_DIR = "templates"
DATABASE_DIR = "database"


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

games = {}

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

def replace_placeholders_in_localized_text(texts_dict: Dict[str, Dict[str, str]]):
    username = session.get("username", "Player")

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


@app.route('/')
def no_path():
    return redirect(url_for("home"))

@app.route('/home')
def home():
    return render_template("chess.html")
    # return redirect(url_for('login'))

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
    
@app.route('/api/localization/<language>/skills', methods=['GET'])
def get_skills(language):
    skills = localized_text.get_all_data(localized_text.get_skills, language)
    skills = replace_placeholders_in_localized_text(skills)
    return jsonify(skills)

@app.route('/api/localization/<language>/cards', methods=['GET'])
def get_cards(language):
    cards = localized_text.get_all_data(localized_text.get_cards, language)
    cards = replace_placeholders_in_localized_text(cards)
    return jsonify(cards)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)