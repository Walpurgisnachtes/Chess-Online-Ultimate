# Chess-Online-Ultimate

![Chess-Online-Ultimate Banner](static/img/banner.png) <!-- Placeholder; replace with actual image if available -->

## Overview

Chess-Online-Ultimate is an innovative web-based multiplayer game that combines the strategic depth of traditional chess with collectible card game (CCG) mechanics. Players build decks of 20 cards, select a "system" (institution) that influences resource generation (prestige), and use cards during matches to alter the board—such as attacking pieces, applying buffs, setting traps, or creating ongoing effects. The game supports real-time online play, user accounts, lobbies for matchmaking, deck building, and a full chess engine with CCG integrations.

This project was developed as a solo final assignment for COMP3421: Web Application Design and Development (Year 4 course). It demonstrates full-stack web development, including frontend UI, backend logic, real-time communication, database management, and cloud deployment.

### Key Features
- **Multiplayer Chess with CCG Twist**: Standard chess rules enhanced by card plays (e.g., attack cards remove pieces, traps activate on enemy turns).
- **Deck Building**: Customize decks from a card pool; systems modify prestige gain (e.g., via captures or board control).
- **Real-Time Gameplay**: Socket.IO ensures synchronized moves and card effects.
- **User Management**: Accounts with login, leaderboards, and persistent decks.
- **Localization**: Multi-language support via XML files.
- **Responsive Design**: Mobile-friendly UI using Bootstrap and custom CSS with @media queries.

## Technologies Used
- **Backend**: Python 3.12, Flask (web framework), Flask-SocketIO (real-time), Eventlet (async).
- **Frontend**: HTML/Jinja2 (templates), JavaScript (interactivity), CSS/Bootstrap (styling).
- **Deployment**: Docker, Google Cloud Build, Google Cloud Run.
- **Other**: JSON for data prototyping, dynamic module loading for card effects.

## Architecture
The project follows the MVC (Model-View-Controller) pattern:
- **Model**: Chess pieces, cards, players, and board logic (e.g., `backend/chess_related/`, `backend/cards/`).
- **View**: Jinja2 templates for pages like login, lobby, deck builder, and chess board.
- **Controller**: Routes and event handlers in `backend/app.py` and `backend/controller.py`.

Frontend-backend communication uses Socket.IO for events like piece moves and card plays, ensuring low-latency multiplayer.

## Installation and Setup (Local Development)
1. Clone the repository:
   ```
   git clone https://github.com/Walpurgisnachtes/Chess-Online-Ultimate.git
   cd Chess-Online-Ultimate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Initialize the database (create MySQL schema for users/games if needed).
4. Run the app:
   ```
   python backend/app.py
   ```
   Access at `http://localhost:5000`.

## Deployment
The app is live-deployed on Google Cloud Run: [Play Now](https://chess-online-ultimate.run.app) <!-- Replace with actual URL -->

To deploy yourself:
1. Build Docker image: `docker build -t chess-online-ultimate .`
2. Use `cloudbuild.yaml` for Google Cloud Build to push and deploy to Cloud Run.

## Game Rules
Detailed in [game_information.md](game_information.md) and [card_example.md](card_example.md) (in Chinese; English translation forthcoming).

- **Setup**: Build a 20-card deck, choose a system.
- **Turns**: Play cards (unlimited, prestige-costed), then mandatory chess move.
- **Win Conditions**: Checkmate (with card delays), opponent resignation, or draws.
- **Card Types**: Attack, Special, Trap, Battlefield, Negative.

## Contributing
Contributions welcome! Fork the repo, create a branch, and submit a pull request. Add tests, fix bugs, or suggest new cards/systems.

## License
MIT License (see [LICENSE](LICENSE) for details).

## Acknowledgments
- Inspired by chess and CCGs like Magic: The Gathering.
- Built with open-source tools; thanks to Flask and Socket.IO communities.

For issues or feedback, open a GitHub issue. Happy gaming! ♟️🃏