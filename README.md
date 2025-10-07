# CricVerse — Beyond the Scorecard
A focused cricket analytics engine that converts raw match YAML files into a Pressure Resistance Model (PRM) and a small Flask UI to explore player, PRS and venue summaries.

Overview
- Purpose: Process ball-by-ball match YAML files, compute pressure-aware scores (PRS), and expose results via CLI reports and a Flask web UI.
- Data: Raw YAML match files are expected in Data/Matches (the data directory is not included here).
- Database: SQLite (database.db) used by multiple modules and by the Flask app.

Table of contents
- Project structure
- Quickstart (install & run)
- CLI (PRS analyzer)
- Web app (Flask) & API
- Key modules and what they do
- Troubleshooting & notes for developers
- Contributing & license

## 📂 Project Structure
- Replaced with a more complete and accurate layout that reflects files present in the repository
```
CricVerse/
├── main.py                          # Flask application + API endpoints (web UI & APIs)
├── prm.py                           # CLI entry for PRS batch processing (calls Package.cricket_analyzer)
├── player_master.py                 # Helper: create players_master table and import CSV name mapping
├── database.db                      # (generated) SQLite DB used by the app / scripts (created at runtime)
├── Data/                            # Raw YAML match files (not committed here)
│   └── Matches/
├── Package/                         # Core Python package (PRS pipeline)
│   ├── __init__.py                  # (optional / may be missing)
│   ├── cricket_analyzer.py          # Orchestrates parsing, classification, scoring, aggregation
│   ├── match_parser.py              # Expected: YAML -> normalized match structure (may be required)
│   ├── delivery_scorer.py           # Expected: delivery -> numeric scores (may be required)
│   ├── pressure_classifier.py       # Classifies pressure level per delivery
│   ├── prs_calculator.py            # Aggregates deliveries and computes final PRS per player
│   └── results_formater.py          # Formats and optionally writes PRS results to DB
├── static/                          # Static frontend assets
│   ├── js/
│   │   ├── prm_react_dom.js         # Bundled runtime already in repo
│   │   ├── prm.js                   # (expected) PRM page interactivity
│   │   ├── player.js                # (expected) player dashboard scripts
│   │   └── venue.js                 # (expected) venue dashboard scripts
│   ├── css/
│   │   ├── base.css                 # (recommended) global styles
│   │   ├── dashboard.css            # (recommended) dashboard specific styles
│   │   └── prm.css                  # (recommended) PRM page styles
│   └── img/
│       └── players/                 # player images (referenced by player records)
├── templates/                       # Jinja2 templates used by Flask (explicit list below)
├── requirements.txt                 # (optional) pin your Python dependencies here
└── README.md
```

## Notes:
- The tree above lists files that exist and those the code references. If match_parser.py or delivery_scorer.py are missing, the pipeline will raise ImportError; create stubs or implement them.
- database.db is generated at runtime; include a migration or data processing script (process_data.py) in the pipeline to populate DB if needed.

Quickstart — install & run (minimal)
1. Create & activate Python venv (recommended)
   - python3 -m venv venv
   - source venv/bin/activate

2. Install requirements
   - If requirements.txt exists: pip install -r requirements.txt
   - Otherwise install minimal packages:
     pip install flask pyyaml sqlite3

3. Prepare data & DB
- Place YAML match files under Data/Matches (the analyzer expects this path).
- The project expects a SQLite DB 'database.db'. If missing, scripts like player_master.py will create/populate some tables; implement or run the data ingestion pipeline to populate full schema.

4. Run the Flask web app (local)
   - python main.py
   - The app opens at http://127.0.0.1:5000 (main.py tries to open a browser automatically).

5. Run PRS CLI (process YAML -> compute PRS)
   - python prm.py
   - prm.py processes files under Data/Matches and invokes Package.cricket_analyzer.CricketAnalyzer which:
     - Parses matches (MatchParser)
     - Classifies pressure per delivery (PressureClassifier)
     - Scores deliveries (DeliveryScorer)
     - Aggregates scores (PRSCalculator)
     - Formats/outputs results (ResultsFormatter)

**Notes on installation**
- Use Python 3.9+.
- If you use the repo inside containers/CI, ensure the process has read access to Data/Matches and write access to create database.db.
- If a requirements.txt is missing, add the packages you actually used in your environment.

**Web app & API** (endpoints present in main.py)
- GET /                 -> index page (templates expected under templates/)
- GET /player-report    -> player search page
- GET /player_dashboard -> player dashboard page
- GET /api/player_data/<name>
  - Returns aggregated player data (batting, bowling, per-season stats, performance snapshot)
  - Expects DB tables: players_master, players, batsman_stats, bowling_stats, master_match
- GET /prm-report       -> PRM explorer page
- GET /api/prm_data
  - Returns PRM rows from the prm table (player_name, batting_prs, bowling_prs, bat_balls, bowl_balls)
  - Supports search query parameter ?search=xxx
- GET /venue-report and GET /report?venue=XXX
  - Venue dashboard using master_match and related stats

### Key modules — short descriptions & usage
- Package/pressure_classifier.py
  - Classifies a delivery into pressure levels (VERY_LOW..EXTREME) and returns a numeric weight used when aggregating PRS.
- Package/prs_calculator.py
  - Maintains per-player lists of delivery-level scores and pressure weights and produces final PRS (normalized).
- Package/results_formater.py
  - Prints results (table, detailed, json) and writes a prm table into database.db. It ensures prm table exists and performs inserts. Be aware of types (integers/floats) when viewing DB.
- Package/cricket_analyzer.py
  - High-level orchestrator: loads YAML match, iterates innings and deliveries, calls classifier and scorer, pushes deliveries to calculator, then finalizes and formats results.
- prm.py
  - Simple CLI wrapper that finds YAML files under Data/Matches and calls CricketAnalyzer to process them.
- player_master.py
  - Creates players_master table and imports Data/names.csv — useful to create a canonical name mapping used by the web app.

### Database & schema notes
- The Flask app and scripts expect SQLite tables:
  - players (fullname, firstname, lastname, bowlingstyle, image_path, ...)
  - players_master (identifier, name) — mapping from canonical id -> available names
  - batsman_stats (player_id, match_id, runs, no_of_balls, dismissal_kind, ...)
  - bowling_stats (player_id, match_id, wickets, runs_given, balls_played, ...)
  - master_match (match_id, date, venue, team_1_score, team_2_score, toss_winner, toss_desicion, winner, ...)
  - prm (player_name, batting_prs, bowling_prs, bat_balls, bowl_balls) — created by ResultsFormatter if missing
- If any of these tables are missing, you will get OperationalError. Use the provided data-processing scripts (if available) to populate DB.

### Troubleshooting — common issues & fixes
- "No YAML files found": ensure Data/Matches exists and contains .yaml/.yml files; prm.py currently defaults path to "Data/Matches".
- "no such table: prm": ResultsFormatter auto-creates the prm table when inserting results; if insert fails, inspect database permissions.
- Player not found from API: run player_master.py to populate players_master (needs Data/names.csv), or verify players table fullnames match players_master.name.
- Database concurrency: main.py uses Flask app context and per-request DB connections via flask.g. Avoid long-lived global connections.

**Developer notes**
- Add tests under Package/tests/ and run with pytest.
- To extend scoring rules, modify Package/delivery_scorer.py (scorer is used by cricket_analyzer).
- To change normalization or weighting, update Package/prs_calculator.py.
- The static/js/prm_react_dom.js file is a bundled script; modify source React code (if available) rather than editing the bundle.

### Suggested maintenance tasks
- Add a requirements.txt with exact pinned versions (Flask, PyYAML, pandas/numpy if used).
- Add a small process_data.py or document the pipeline to build the SQLite DB from YAML.
- Add a templates/ directory and list the pages expected by the Flask app.
- Add tests that validate PRS outputs on a small subset of YAML files.

### Contributing
- Fork, create a feature branch, add tests, open a PR with details.
- For large changes, open an issue first to discuss approach.

### Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Running the Application
  ```bash
  python3 main.py
  ```

The application will be available at `http://localhost:3000`.

---

## 🚀 Usage Guide
- **Player Hub**: Search for any IPL player to view their detailed profile and unique Pressure Resistance Score.
- **Tactical XI Engine**: Select an upcoming fixture to receive a data-driven recommendation for the optimal playing XI.
- **Venue Insights**: Choose a stadium to analyze its historical trends and pitch behavior before a match.

---

## ❗ Troubleshooting

### Common Issues
1. **Database Connection Errors**
   ```
   Solution: Check database path and permissions
   ```

2. **API Connection Failures**
   ```
   Solution: Verify network connectivity and API endpoints
   ```

3. **Data Processing Errors**
   ```
   Solution: Ensure YAML files are properly formatted
   ```

---

## 🗺️ Roadmap
 - Interactive Data Visualizations: Integrate Chart.js or D3.js for dynamic graphs.
 - Live Match Integration: Pull live scores via an API and overlay predictive analytics in real-time.
 - AI-Powered Projections: Use machine learning to predict player form and match winners.
 - Advanced Interactive Filters: Add client-side, JS-based sorting and filtering for all data tables.
 - PDF/Report Exports: Allow users to download strategic match previews and player reports.

---

## 🤝 Contributing
Contributions are what make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

**Steps**:
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📞 Support

- **Technical Issues**: Open an issue on GitHub
- **Feature Requests**: Use the discussions tab
- **Business Inquiries**: akhileshkancharla5@gmail.com

---

<div align="center">
<p>Built by Akhilesh Kancharla</p>
</div>
