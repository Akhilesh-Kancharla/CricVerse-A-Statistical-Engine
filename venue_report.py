import sqlite3
import webbrowser
import threading
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_venue_dashboard_data(venue_query):
    """
    Fetches and processes all data for a given venue to populate the dashboard.
    """
    conn = get_db_connection()
    
    # Find the exact venue name from a partial query
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT venue FROM master_match WHERE venue LIKE ?", (f"%{venue_query}%",))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None # Return None if no venue is found

    venue_name = result['venue']

    # Fetch all master_match for the identified venue
    master_match = conn.execute("SELECT * FROM master_match WHERE venue = ?", (venue_name,)).fetchall()
    conn.close()

    if not master_match:
        return None

    total_master_match = len(master_match)
    
    # 1. Calculate KPIs
    avg_first_innings = round(sum(m['team_1_score'] for m in master_match) / total_master_match)
    avg_second_innings = round(sum(m['team_2_score'] for m in master_match) / total_master_match)
    highest_score = max(max(m['team_1_score'], m['team_2_score']) for m in master_match)

    # 2. Calculate Team Wins
    team_wins = {}
    for match in master_match:
        winner = match['winner']
        if winner and 'tie' not in winner:
            team_wins[winner] = team_wins.get(winner, 0) + 1

    # 3. Calculate Toss Decision Outcomes
    bat_first_wins = 0
    field_first_wins = 0
    for match in master_match:
        if match['winner'] and 'tie' not in match['winner']:
            # Team batting first wins if they are the winner and chose to bat, OR the other team chose to field and lost.
            won_batting_first = (match['toss_winner'] == match['winner'] and match['toss_desicion'] == 'bat') or \
                                (match['toss_winner'] != match['winner'] and match['toss_desicion'] == 'field')
            if won_batting_first:
                bat_first_wins += 1
            else:
                field_first_wins += 1

    # 4. Calculate Pace vs. Spin Wickets
    # This requires a more complex query joining multiple tables.
    # We need to link bowling_stats -> players_master -> players to get bowling style.
    # For simplicity, we'll do this in steps.
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # This query gets the bowling style for every wicket taken at the venue.
    # It joins through master_match, bowling_stats, players_master, and finally players.
    cursor.execute("""
        SELECT p.bowlingstyle
        FROM master_match mm
        JOIN bowling_stats bs ON mm.match_id = bs.match_id
        JOIN players_master pm ON bs.player_id = pm.identifier
        JOIN players p ON pm.name = p.fullname OR pm.name = (p.firstname || ' ' || p.lastname)
        WHERE mm.venue = ? AND bs.wickets > 0 AND p.bowlingstyle IS NOT NULL
    """, (venue_name,))
    
    bowling_styles = cursor.fetchall()
    conn.close()

    pace_wickets = 0
    spin_wickets = 0
    for style_row in bowling_styles:
        style = (style_row['bowlingstyle'] or '').lower()
        if 'fast' in style or 'pace' in style or 'seam' in style:
            pace_wickets += 1
        elif 'spin' in style or 'orthodox' in style or 'legbreak' in style or 'offbreak' in style or 'chinaman' in style:
            spin_wickets += 1

    # 4. Calculate Average Scores by Season
    scores_by_season = {}
    for m in master_match:
        # Assuming date format is like '1-May-2023'
        try:
            year = m['date'].split('-')[-1]
            if year not in scores_by_season:
                scores_by_season[year] = {'first_innings': [], 'second_innings': []}
            scores_by_season[year]['first_innings'].append(m['team_1_score'])
            scores_by_season[year]['second_innings'].append(m['team_2_score'])
        except:
            continue # Skip if date format is unexpected

    avg_1st_innings_season = {
        year: round(sum(data['first_innings']) / len(data['first_innings']))
        for year, data in sorted(scores_by_season.items()) if data['first_innings']
    }
    avg_2nd_innings_season = {
        year: round(sum(data['second_innings']) / len(data['second_innings']))
        for year, data in sorted(scores_by_season.items()) if data['second_innings']
    }

    # Assemble final data structure for the frontend
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


@app.route("/")
def index():
    """Renders the main search page."""
    return render_template("venue_before.html")


@app.route("/report")
def venue_report():
    """
    Renders the dashboard with data for the requested venue.
    """
    venue_query = request.args.get("venue")
    if not venue_query:
        return redirect(url_for("index")) # If no venue, go back to search

    # Fetch all data needed for the dashboard
    venue_data = get_venue_dashboard_data(venue_query)
    
    # The template will handle the case where venue_data is None (not found)
    return render_template("venue_dashboard.html", venue_data=venue_data)


if __name__ == "__main__":
    # Open the browser automatically to the web app's URL
    url = "http://127.0.0.1:5000"
    threading.Timer(1.25, lambda: webbrowser.open(url)).start()
    
    # Run the Flask app
    app.run(debug=True, use_reloader=True)