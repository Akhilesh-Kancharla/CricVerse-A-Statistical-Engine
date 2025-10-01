# player_report.py

from flask import Flask, request, jsonify, render_template
import sqlite3
import threading
import atexit
import random

# --- Flask App Setup ---
app = Flask(__name__)

# --- Database Connection Pool ---
DB_CONNECTIONS = {}

def get_db_connection():
    thread_id = threading.get_ident()
    if thread_id not in DB_CONNECTIONS:
        conn = sqlite3.connect('database.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        DB_CONNECTIONS[thread_id] = conn
    return DB_CONNECTIONS[thread_id]

def close_all_connections():
    for conn in DB_CONNECTIONS.values():
        conn.close()

atexit.register(close_all_connections)

# --- Player Name Mapping ---
PLAYER_NAME_MAP = {}

def initialize_name_mapping():
    """
    Creates a mapping between players.fullname and players_master.name
    to link detailed profiles with statistical IDs. Optimized for speed.
    """
    global PLAYER_NAME_MAP
    if PLAYER_NAME_MAP: return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM players_master")
        master_names = {row['name'] for row in cursor.fetchall()}
        
        cursor.execute("SELECT fullname FROM players")
        full_names = {row['fullname'] for row in cursor.fetchall()}

        master_name_lookup = {}
        for name in master_names:
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1]
                if last_name not in master_name_lookup:
                    master_name_lookup[last_name] = []
                master_name_lookup[last_name].append(name)

        temp_map = {}
        for full_name in full_names:
            full_name_parts = full_name.split()
            if len(full_name_parts) < 2: continue
            
            last_name = full_name_parts[-1]
            if last_name in master_name_lookup:
                first_name = full_name_parts[0]
                for master_name in master_name_lookup[last_name]:
                    master_name_parts = master_name.split()
                    if len(master_name_parts) > 0 and first_name.startswith(master_name_parts[0][0]):
                        temp_map[full_name] = master_name
                        break
                
        PLAYER_NAME_MAP = temp_map
        print(f"Initialized name mapping with {len(PLAYER_NAME_MAP)} players.")
    except sqlite3.OperationalError as e:
        print("\n--- DATABASE ERROR ---")
        print(f"An error occurred during initialization: {e}")
        print("Please ensure the database 'database.db' exists and is correctly populated.")
        print("You may need to run the data parser scripts (e.g., player_parser.py, player_master.py) first.\n")

with app.app_context():
    initialize_name_mapping()

# --- HTML Page Routes ---
@app.route("/")
def search_page():
    """Serves the main player search page."""
    return render_template("playerreport_before.html")

@app.route("/player_dashboard")
def dashboard_page():
    """Serves the player dashboard page. The data is then loaded via the API."""
    return render_template("player_dashboard.html")

# --- Helper Functions ---
def calculate_performance_metrics(total_runs, total_balls_faced, total_outs, total_wickets, latest_season_stats):
    """
    Calculates derived metrics for the radar chart based on aggregated stats.
    """
    strike_rate = (total_runs / total_balls_faced * 100) if total_balls_faced > 0 else 0
    average = (total_runs / total_outs) if total_outs > 0 else total_runs

    power_hitting = min(100, (strike_rate / 180) * 100)
    consistency = min(100, (average / 60) * 100)
    
    form = 75 
    if latest_season_stats:
        ls_sr = latest_season_stats.get('strike_rate', 0)
        ls_avg = latest_season_stats.get('average', 0)
        sr_ratio = (ls_sr / strike_rate) if strike_rate > 0 else 1
        avg_ratio = (ls_avg / average) if average > 0 else 1
        form = min(100, ((sr_ratio + avg_ratio) / 2) * 70)

    bowler_impact = min(100, (total_wickets / 50) * 100) if total_wickets > 0 else 0
    
    finishing = (power_hitting * 0.6) + (consistency * 0.4)
    pressure_play = min(100, (average * 1.5) + (total_wickets * 0.5))

    return {
        'Consistency': round(consistency),
        'Power Hitting': round(power_hitting),
        'Finishing': round(finishing),
        'Pressure Play': round(pressure_play),
        'Form': round(form),
        'Bowler Impact': round(bowler_impact)
    }

# --- Main API Endpoint ---
@app.route("/api/player_data/<name>")
def get_player_data(name):
    """
    Fetches and processes player data from the database, optimized with SQL aggregations.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        master_name = PLAYER_NAME_MAP.get(name)
        if not master_name:
            return jsonify({"error": f"Player '{name}' not found or could not be mapped."}), 404

        cursor.execute("SELECT identifier FROM players_master WHERE name = ?", (master_name,))
        master_record = cursor.fetchone()
        if not master_record:
            return jsonify({"error": "Player identifier not found."}), 404
        player_identifier = master_record['identifier']

        player_details = cursor.execute("SELECT * FROM players WHERE fullname = ?", (name,)).fetchone()

        bat_summary = cursor.execute("""
            SELECT 
                SUM(runs) as total_runs,
                SUM(no_of_balls) as total_balls,
                SUM(CASE WHEN dismissal_kind IS NOT NULL AND dismissal_kind != 'not out' THEN 1 ELSE 0 END) as total_outs,
                COUNT(match_id) as total_innings, 
                MAX(runs) as high_score, 
                SUM(CASE WHEN runs >= 100 THEN 1 ELSE 0 END) as hundreds, 
                SUM(CASE WHEN runs >= 50 AND runs < 100 THEN 1 ELSE 0 END) as fifties 
            FROM batsman_stats WHERE player_id = ?
        """, (player_identifier,)).fetchone()

        if not bat_summary or bat_summary['total_runs'] is None:
            return jsonify({"error": f"No batting statistics found for player '{name}'."}), 404

        total_runs = bat_summary['total_runs'] or 0
        total_balls_faced = bat_summary['total_balls'] or 0
        total_outs = bat_summary['total_outs'] or 0
        
        strike_rate = (total_runs / total_balls_faced * 100) if total_balls_faced > 0 else 0
        average = (total_runs / total_outs) if total_outs > 0 else total_runs

        # --- Bowling Stats Aggregation Query ---
        bowl_summary = cursor.execute("""
            SELECT
                SUM(wickets) as total_wickets,
                SUM(runs_given) as total_runs_conceded,
                SUM(balls_played) as total_balls_bowled
            FROM bowling_stats WHERE player_id = ? 
        """, (player_identifier,)).fetchone()

        best_figures_row = cursor.execute("""
            SELECT wickets, runs_given FROM bowling_stats WHERE player_id = ?
            ORDER BY wickets DESC, runs_given ASC LIMIT 1
        """, (player_identifier,)).fetchone()

        total_wickets = bowl_summary['total_wickets'] if bowl_summary else 0
        total_runs_conceded = bowl_summary['total_runs_conceded'] if bowl_summary else 0
        total_balls_bowled = bowl_summary['total_balls_bowled'] if bowl_summary else 0
        
        bowling_avg = (total_runs_conceded / total_wickets) if total_wickets > 0 else 0
        economy = (total_runs_conceded / (total_balls_bowled / 6)) if total_balls_bowled > 0 else 0
        best_figures = f"{best_figures_row['wickets']}/{best_figures_row['runs_given']}" if best_figures_row and best_figures_row['wickets'] is not None else "N/A"
        
        batting_season_rows = cursor.execute("""
            SELECT 
                STRFTIME('%Y', m.date) as season,
                SUM(bs.runs) as total_runs, 
                SUM(bs.no_of_balls) as total_balls,
                SUM(CASE WHEN bs.dismissal_kind IS NOT NULL AND bs.dismissal_kind != 'not out' THEN 1 ELSE 0 END) as seasonal_outs
            FROM batsman_stats bs
            JOIN master_match m ON bs.match_id = m.match_id
            WHERE bs.player_id = ? 
            GROUP BY season 
            ORDER BY season
        """, (player_identifier,)).fetchall()
        
        runs_per_season = {row['season']: row['total_runs'] for row in batting_season_rows}
        strike_rate_per_season = {r['season']: (r['total_runs'] * 100 / r['total_balls']) if r['total_balls'] > 0 else 0 for r in batting_season_rows}
        
        # --- Per-Season Bowling Stats ---
        bowling_season_rows = cursor.execute("""
            SELECT 
                STRFTIME('%Y', m.date) as season,
                SUM(bo.wickets) as total_wickets,
                SUM(bo.runs_given) as total_runs_conceded,
                SUM(bo.balls_played) as total_balls_bowled
            FROM bowling_stats bo 
            JOIN master_match m ON bo.match_id = m.match_id
            WHERE bo.player_id = ? GROUP BY season ORDER BY season
        """, (player_identifier,)).fetchall()

        wickets_per_season = {row['season']: row['total_wickets'] for row in bowling_season_rows}
        economy_per_season = {
            row['season']: (row['total_runs_conceded'] / (row['total_balls_bowled'] / 6)) if row['total_balls_bowled'] > 0 else 0
            for row in bowling_season_rows
        }
        
        bowling_style = player_details['bowlingstyle'] if player_details and player_details['bowlingstyle'] else "N/A"
        if bowling_style in ('', 'N/A') and total_wickets > 0:
             bowling_style = "Right-arm fast-medium" 

        latest_season_stats = {}
        if batting_season_rows:
            lsr = batting_season_rows[-1]
            seasonal_outs = lsr['seasonal_outs']
            latest_season_stats = {
                'strike_rate': (lsr['total_runs'] / lsr['total_balls'] * 100) if lsr['total_balls'] > 0 else 0,
                'average': (lsr['total_runs'] / seasonal_outs) if seasonal_outs > 0 else lsr['total_runs']
            }
        
        performance_snapshot = calculate_performance_metrics(total_runs, total_balls_faced, total_outs, total_wickets, latest_season_stats)

        dismissal_rows = cursor.execute("""
            SELECT dismissal_kind, COUNT(*) as count
            FROM batsman_stats
            WHERE player_id = ? AND dismissal_kind IS NOT NULL AND dismissal_kind != 'not out'
            GROUP BY dismissal_kind
            ORDER BY count DESC
        """, (player_identifier,)).fetchall()
        dismissal_types = {row['dismissal_kind']: row['count'] for row in dismissal_rows}

        details_data = {
            "battingStyle": player_details['battingstyle'] if player_details else "N/A",
            "bowlingStyle": bowling_style,
            "imagePath": player_details['image_path'] if player_details else None
        }

        batting_data = {
            "totalRuns": total_runs, "highScore": bat_summary['high_score'] or 0, "average": round(average, 2),
            "strikeRate": round(strike_rate, 2), "hundreds": bat_summary['hundreds'] or 0, "fifties": bat_summary['fifties'] or 0,
            "dismissalTypes": dismissal_types
        }

        player_data = {
            "name": name,
            "details": details_data,
            "batting": batting_data,
            "bowling": {"totalWickets": total_wickets, "economy": round(economy, 2), "average": round(bowling_avg, 2), "bestFigures": best_figures},
            "runsPerSeason": runs_per_season,
            "strikeRatePerSeason": {k: round(v, 2) for k, v in strike_rate_per_season.items()},
            "wicketsPerSeason": wickets_per_season,
            "economyPerSeason": {k: round(v, 2) for k, v in economy_per_season.items()},
            "performance": performance_snapshot
        }

        return jsonify(player_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    print("Open http://127.0.0.1:5000 in your browser to access the search page.")
    app.run(debug=True, port=5000)