import sqlite3
import csv

# --- Configuration ---
DB_FILE = "database.db"
CSV_FILE = "names.csv"

def create_players_master_table():
    """
    Connects to the SQLite database and creates the 'players_master' table if it doesn't exist.
    This table will store player identifiers and their various names.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # SQL statement to create the new table.
        # We can add a UNIQUE constraint to prevent duplicate identifier/name pairs.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players_master (
            identifier TEXT,
            name TEXT,
            UNIQUE(identifier, name)
        )
        ''')

        conn.commit()
        print(f"Table 'players_master' is ready in '{DB_FILE}'.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def parse_and_insert_names():
    """
    Reads player name data from the CSV file and inserts it into the 'players_master' table.
    """
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            # Use DictReader to easily access columns by header name
            csv_reader = csv.DictReader(file)
            # Convert to a list of tuples for insertion
            data_to_insert = [(row['identifier'], row['name']) for row in csv_reader]
            
    except FileNotFoundError:
        print(f"Error: The file '{CSV_FILE}' was not found.")
        return
    except Exception as e:
        print(f"Error reading or processing CSV file: {e}")
        return

    if not data_to_insert:
        print("No data found in the CSV file to insert.")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Using INSERT OR IGNORE will skip any rows that would violate the UNIQUE constraint,
        # preventing errors from duplicate data.
        cursor.executemany('''
        INSERT OR IGNORE INTO players_master (identifier, name) VALUES (?, ?)
        ''', data_to_insert)

        conn.commit()
        # The number of newly inserted rows
        inserted_rows = cursor.rowcount
        print(f"Successfully inserted {inserted_rows} new records into the 'players_master' table.")
        
        total_rows = len(data_to_insert)
        if inserted_rows < total_rows:
            print(f"Skipped {total_rows - inserted_rows} duplicate records.")

    except sqlite3.Error as e:
        print(f"Database error during insertion: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_players_master_table()
    parse_and_insert_names()
