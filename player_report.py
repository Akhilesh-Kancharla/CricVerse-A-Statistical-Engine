# player_report.py

from flask import Flask, request, render_template, jsonify
import sqlite3
import webbrowser
import threading
import random

app = Flask(__name__, template_folder='.')

def generate_mock_data(player_name):
    """Generates realistic mock data for charts where DB data is not available."""
    # Mock data for Dismissal Types
    dismissals = {
        'Caught': random.randint(40, 70),
        'Bowled': random.randint(10, 25),
        'LBW': random.randint(5, 15),
        'Run Out': random.randint(3, 8),
        'Stumped': random.randint(1, 5)
    }

    # Mock data for Performance Snapshot (Radar Chart)
    # Create different archetypes for more interesting results
    if 'V' in player_name or 'CH' in player_name: # Aggressive player archetype
        performance = {
            'Consistency': random.randint(75, 88),
            'Power Hitting': random.randint(85, 98),
            'Finishing': random.randint(80, 92),
            'Pressure Play': random.randint(82, 95),
            'Form': random.randint(78, 90)
        }
    else: # Default stable player archetype
        performance = {
            'Consistency': random.randint(80, 95),
            'Power Hitting': random.randint(70, 85),
            'Finishing': random.randint(75, 88),
            'Pressure Play': random.randint(80, 92),
            'Form': random.randint(75, 88)
        }
    return dismissals, performance


@app.route("/")
def index():
    return render_template("playerreport_before.html")

@app.route("/player_dashboard")
def player_dashboard():
    return render_template("player_dashboard.html")

@app.route("/api/player_data/<string:name>")
def get_player_data(name):
    if not name:
        return jsonify({"error": "No player name specified."}), 400
    
    conn = None
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT player_id, runs, fours, sixes, no_of_balls, match_id "
            "FROM batsman_stats WHERE player_id = ?", (name,)
        )
        batting_rows = cursor.fetchall()

        if not batting_rows:
            return jsonify({"error": f"Player '{name}' not found."}), 404

        total_runs, total_balls, hundreds, fifties = 0, 0, 0, 0
        for row in batting_rows:
            total_runs += row['runs']
            total_balls += row['no_of_balls']
            if row['runs'] >= 100:
                hundreds += 1
            elif 50 <= row['runs'] < 100:
                fifties += 1
        
        strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0
        
        cursor.execute("""
            SELECT 
                SUBSTR(m.date, -4) as season,
                SUM(bs.runs) as total_runs,
                SUM(bs.no_of_balls) as total_balls
            FROM batsman_stats bs
            JOIN master_match m ON bs.match_id = m.match_id
            WHERE bs.player_id = ?
            GROUP BY season
            ORDER BY season;
        """, (name,))
        season_rows = cursor.fetchall()
        
        runs_per_season = {row['season']: row['total_runs'] for row in season_rows}
        strike_rate_per_season = {
            row['season']: round((row['total_runs'] / row['total_balls'] * 100), 2) if row['total_balls'] > 0 else 0
            for row in season_rows
        }

        # Generate and add the mock data for the new charts
        dismissal_types, performance_snapshot = generate_mock_data(name)

        player_data = {
            "name": name,
            "batting": {
                "totalRuns": total_runs,
                "highScore": max(row['runs'] for row in batting_rows) if batting_rows else 0,
                "average": "N/A",
                "strikeRate": round(strike_rate, 2),
                "hundreds": hundreds,
                "fifties": fifties,
                "dismissalTypes": dismissal_types # Added mock data
            },
            "runsPerSeason": runs_per_season,
            "strikeRatePerSeason": strike_rate_per_season,
            "performance": performance_snapshot # Added mock data
        }

        return jsonify(player_data)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    url = "http://1227.0.0.1:5000/"
    threading.Timer(1, lambda: webbrowser.open(url)).start()
    app.run(debug=True)