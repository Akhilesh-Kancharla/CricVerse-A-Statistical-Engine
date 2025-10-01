import sqlite3
import yaml

# --- Configuration ---
DB_FILE = "database.db"
YAML_FILE = "player.yaml"

def create_players_table():
    """
    Connects to the SQLite database and creates the 'players' table if it doesn't exist.
    This ensures the script can be run without manual database setup.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # SQL statement to create a table.
        # Using IF NOT EXISTS prevents an error if the table already exists.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            country_id INTEGER,
            firstname TEXT,
            lastname TEXT,
            fullname TEXT,
            image_path TEXT,
            dateofbirth TEXT,
            gender TEXT,
            battingstyle TEXT,
            bowlingstyle TEXT,
            position_name TEXT,
            updated_at TEXT
        )
        ''')

        conn.commit()
        print(f"Table 'players' is ready in '{DB_FILE}'.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def parse_and_insert_players():
    """
    Reads the player data from the YAML file and inserts it into the 'players' table.
    """
    try:
        with open(YAML_FILE, 'r') as file:
            players_data = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: The file '{YAML_FILE}' was not found.")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # The player information is nested under the 'data' key.
        players_list = players_data.get('data', [])
        if not players_list:
            print("No player data found under the 'data' key in the YAML file.")
            return

        insert_count = 0
        for player in players_list:
            # Use .get() for safe access to dictionary keys to avoid errors
            # if a key is missing. The second argument is a default value.
            player_info = (
                player.get('id'),
                player.get('country_id'),
                player.get('firstname'),
                player.get('lastname'),
                player.get('fullname'),
                player.get('image_path'),
                player.get('dateofbirth'),
                player.get('gender'),
                player.get('battingstyle'),
                player.get('bowlingstyle'),
                player.get('position', {}).get('name'), # Safely access nested dictionary
                player.get('updated_at')
            )

            # Using INSERT OR REPLACE will update a player's record if their
            # player_id already exists. This prevents duplicate entries.
            cursor.execute('''
            INSERT OR REPLACE INTO players (
                player_id, country_id, firstname, lastname, fullname, image_path,
                dateofbirth, gender, battingstyle, bowlingstyle, position_name, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', player_info)
            insert_count += 1

        conn.commit()
        print(f"Successfully inserted or updated {insert_count} players into the database.")

    except sqlite3.Error as e:
        print(f"Database error during insertion: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_players_table()
    parse_and_insert_players()
