import sqlite3
import threading
import atexit
from flask import Flask, request, jsonify, render_template

# --- Flask App Setup ---
app = Flask(__name__)

# --- Database Connection Pool ---
DB_CONNECTIONS = {}

def get_db_connection():
    """Creates and manages a pool of database connections per thread."""
    thread_id = threading.get_ident()
    if thread_id not in DB_CONNECTIONS:
        conn = sqlite3.connect('database.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        DB_CONNECTIONS[thread_id] = conn
    return DB_CONNECTIONS[thread_id]

def close_all_connections():
    """Closes all active database connections on application exit."""
    for conn in DB_CONNECTIONS.values():
        conn.close()

atexit.register(close_all_connections)

# --- Page & API Routes ---

@app.route("/")
def prm_page():
    """Serves the main Pressure Resistance Model (PRM) explorer page."""
    return render_template("prm.html")

@app.route("/api/prm_data")
def get_prm_data():
    """
    API endpoint to fetch Pressure Resistance Model (PRM) data from the database.
    Supports searching by player name and dynamically assigns a role.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        search_query = request.args.get('search', '')

        if search_query:
            query = "SELECT rowid as id, player_name, batting_prs, bowling_prs, bat_balls, bowl_balls FROM prm WHERE player_name LIKE ? ORDER BY player_name"
            params = (f'%{search_query}%',)
        else:
            query = "SELECT rowid as id, player_name, batting_prs, bowling_prs, bat_balls, bowl_balls FROM prm ORDER BY player_name"
            params = ()

        players = cursor.execute(query, params).fetchall()

        prm_data = []
        for player in players:
            bat_balls = player['bat_balls'] or 0
            bowl_balls = player['bowl_balls'] or 0
            # Determine player role based on volume of play
            role = "Batsman" # Default role
            if bat_balls > 50 and bowl_balls > 50:
                role = "All-Rounder"
            elif bowl_balls > bat_balls:
                role = "Bowler"

            prm_data.append(dict(player, role=role))

        return jsonify(prm_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    # Note: Running on port 5001 to avoid conflict with player_report.py
    print("Starting PRM Flask server...")
    print("Open http://127.0.0.1:5001 in your browser to access the PRM Explorer.")
    app.run(debug=True, port=5001)