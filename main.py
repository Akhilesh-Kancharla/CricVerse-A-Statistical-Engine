import sqlite3
import threading
import webbrowser
from flask import Flask, request, jsonify, render_template, redirect, url_for, g

# --- Flask App Setup ---
app = Flask(__name__)

# --- Database Connection Management (Idiomatic Flask Pattern) ---
# This is the new, recommended way to handle connections.
# It ensures one connection is opened per request and closed automatically.

def get_db_connection():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        g.db = sqlite3.connect('database.db', check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Player Name Mapping ---
PLAYER_NAME_MAP = {}

def initialize_name_mapping():
    """
    Creates a mapping between players.fullname and players_master.name
    by performing an optimized join in the database.
    """
    global PLAYER_NAME_MAP
    if PLAYER_NAME_MAP: return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optimized query to map names directly in the database
        cursor.execute("""
            SELECT p.fullname, pm.name as master_name
            FROM players p
            JOIN players_master pm ON (p.firstname || ' ' || p.lastname) = pm.name OR p.fullname = pm.name
        """)
        
        PLAYER_NAME_MAP = {row['fullname']: row['master_name'] for row in cursor.fetchall()}
        
        print(f"Initialized name mapping with {len(PLAYER_NAME_MAP)} players.")

    except sqlite3.OperationalError as e:
        print("\n--- DATABASE ERROR ---")
        print(f"An error occurred during initialization: {e}")
        print("Please ensure the database 'database.db' exists and is correctly populated.")
        print("You may need to run the data parser scripts first.\n")

# Run initialization within the application context
with app.app_context():
    initialize_name_mapping()

# --- Main Page ---
@app.route("/")
def index():
    """Serves the main index page."""
    return render_template("index.html")

# --- Player Report Feature ---
@app.route("/player-report")
def player_search_page():
    """Serves the main player search page."""
    return render_template("playerreport_before.html")

@app.route("/player_dashboard")
def player_dashboard_page():
    """Serves the player dashboard page. The data is then loaded via the API."""
    return render_template("player_dashboard.html")

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

# --- PRM Report Feature ---
@app.route("/prm-report")
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

# --- Venue Report Feature ---
@app.route("/venue-report")
def venue_search_page():
    """Renders the main search page."""
    return render_template("venue_before.html")

@app.route("/report")
def venue_report():
    """
    Renders the dashboard with data for the requested venue.
    """
    venue_query = request.args.get("venue")
    if not venue_query:
        return redirect(url_for("venue_search_page"))

    venue_data = get_venue_dashboard_data(venue_query)
    
    return render_template("venue_dashboard.html", venue_data=venue_data)

def get_venue_dashboard_data(venue_query):
    """
    Fetches and processes all data for a given venue to populate the dashboard.
    """
    conn = get_db_connection()
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT venue FROM master_match WHERE venue LIKE ?", (f"%{venue_query}%",))
    result = cursor.fetchone()
    
    if not result:
        # No need to close the connection here; Flask's teardown will handle it.
        return None

    venue_name = result['venue']

    master_match = conn.execute("SELECT * FROM master_match WHERE venue = ?", (venue_name,)).fetchall()

    if not master_match:
        return None

    total_master_match = len(master_match)
    
    avg_first_innings = round(sum(m['team_1_score'] for m in master_match) / total_master_match)
    avg_second_innings = round(sum(m['team_2_score'] for m in master_match) / total_master_match)
    highest_score = max(max(m['team_1_score'], m['team_2_score']) for m in master_match)

    team_wins = {}
    for match in master_match:
        winner = match['winner']
        if winner and 'tie' not in winner:
            team_wins[winner] = team_wins.get(winner, 0) + 1

    bat_first_wins = 0
    field_first_wins = 0
    for match in master_match:
        if match['winner'] and 'tie' not in match['winner']:
            won_batting_first = (match['toss_winner'] == match['winner'] and match['toss_desicion'] == 'bat') or \
                                (match['toss_winner'] != match['winner'] and match['toss_desicion'] == 'field')
            if won_batting_first:
                bat_first_wins += 1
            else:
                field_first_wins += 1

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.bowlingstyle
        FROM master_match mm
        JOIN bowling_stats bs ON mm.match_id = bs.match_id
        JOIN players_master pm ON bs.player_id = pm.identifier
        JOIN players p ON pm.name = p.fullname OR pm.name = (p.firstname || ' ' || p.lastname)
        WHERE mm.venue = ? AND bs.wickets > 0 AND p.bowlingstyle IS NOT NULL
    """, (venue_name,))
    
    bowling_styles = cursor.fetchall()
    # <<-- THE PROBLEMATIC conn.close() LINE WAS REMOVED FROM HERE -->>

    pace_wickets = 0
    spin_wickets = 0
    for style_row in bowling_styles:
        style = (style_row['bowlingstyle'] or '').lower()
        if 'fast' in style or 'pace' in style or 'seam' in style:
            pace_wickets += 1
        elif 'spin' in style or 'orthodox' in style or 'legbreak' in style or 'offbreak' in style or 'chinaman' in style:
            spin_wickets += 1

    scores_by_season = {}
    for m in master_match:
        try:
            year = m['date'].split('-')[-1]
            if year not in scores_by_season:
                scores_by_season[year] = {'first_innings': [], 'second_innings': []}
            scores_by_season[year]['first_innings'].append(m['team_1_score'])
            scores_by_season[year]['second_innings'].append(m['team_2_score'])
        except:
            continue

    avg_1st_innings_season = {
        year: round(sum(data['first_innings']) / len(data['first_innings']))
        for year, data in sorted(scores_by_season.items()) if data['first_innings']
    }
    avg_2nd_innings_season = {
        year: round(sum(data['second_innings']) / len(data['second_innings']))
        for year, data in sorted(scores_by_season.items()) if data['second_innings']
    }

    dashboard_data = {
        "name": venue_name,
        "kpis": {
            "avgFirstInnings": avg_first_innings,
            "avgSecondInnings": avg_second_innings,
            "highestScore": highest_score,
            "matchesPlayed": total_master_match
        },
        "teamWins": dict(sorted(team_wins.items(), key=lambda item: item[1], reverse=True)),
        "tossDecision": {
            "Bat First Wins": bat_first_wins,
            "Field First Wins": field_first_wins
        },
        "bowlingAnalysis": {
            "Pace Wickets": pace_wickets,
            "Spin Wickets": spin_wickets
        },
        "avgScoreBySeason": avg_1st_innings_season,
        "avgSecondInningsScoreBySeason": avg_2nd_innings_season
    }
    
    return dashboard_data

# --- Under Construction and 404 ---
@app.route("/under-construction")
def under_construction():
    """Serves the page under construction."""
    return render_template("page_under_construction.html")

@app.errorhandler(404)
def page_not_found(e):
    """Serves the 404 page."""
    return render_template('page404.html'), 404

if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    threading.Timer(1.25, lambda: webbrowser.open(url)).start()
    app.run(debug=True, use_reloader=True, port=5000)