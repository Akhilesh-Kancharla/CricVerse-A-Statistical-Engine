import json
import pandas as pd
import numpy as np
from supabase import create_client, Client
import os
import re
from dotenv import load_dotenv


load_dotenv()
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY') 

if not url or not key:
    raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(url, key)
print("Supabase client initialized (using anon key).")


def process_batsman_stats(data_file):
    """
    This function is copied from your script. It is well-written and correct.
    It transforms the raw JSON into a clean list of dictionaries.
    """
    match_id = os.path.basename(data_file).split('.')[0]
    data = json.load(open(data_file))

    all_deliveries = []
    for inning in data['innings']:
        all_deliveries.append(pd.json_normalize(inning, record_path=['overs', 'deliveries']))
    df = pd.concat(all_deliveries)

    # Get batsman stats from batter runs
    batsman_stats = df.groupby('batter').agg(
        runs=('runs.batter', 'sum'),
        fours=('runs.batter', lambda x: (x == 4).sum()),
        sixs=('runs.batter', lambda x: (x == 6).sum())
    ).reset_index()

    # Get all players from the match
    all_players_list = []
    for team in data['info']['players']:
        all_players_list.extend(data['info']['players'][team])

    all_players_df = pd.DataFrame(all_players_list, columns=['batter'])

    # Merge to include all players, even those who didn't bat
    batsman_stats = pd.merge(all_players_df, batsman_stats, on='batter', how='left')

    # Fill stats for non-batters with 0
    batsman_stats[['runs', 'fours', 'sixs']] = batsman_stats[['runs', 'fours', 'sixs']].fillna(0)
    
    for col in ['runs', 'fours', 'sixs']:
        batsman_stats[col] = batsman_stats[col].astype(int)

    # Extract dismissal data
    dismissals = []
    if 'innings' in data:
        for inning in data['innings']:
            if 'overs' in inning:
                for over in inning['overs']:
                    if 'deliveries' in over:
                        for delivery in over['deliveries']:
                            if 'wickets' in delivery:
                                for wicket in delivery['wickets']:
                                    dismissals.append({
                                        'batter': wicket['player_out'],
                                        'dismissal': wicket['kind']
                                    })
    dismissals_df = pd.DataFrame(dismissals)
    
    if not dismissals_df.empty:
        batsman_stats = pd.merge(batsman_stats, dismissals_df, on='batter', how='left')
    else:
        batsman_stats['dismissal'] = np.nan

    batsman_stats['dismissal'] = batsman_stats['dismissal'].fillna('not out')

    dismissal_mapping = {
        'caught': 1, 'run out': 2, 'stumped': 3, 'bowled': 4,
        'not out': 5, 'lbw': 6, 'caught and bowled': 7,
        'retired hurt': 8, 'hit wicket': 9,
        'obstructing the field': 10, 'retired out': 11
    }
    batsman_stats['dismissal'] = batsman_stats['dismissal'].map(dismissal_mapping)

    people = data['info']['registry']['people']
    # Create player_id column
    batsman_stats['player_id'] = batsman_stats['batter'].map(people)

    # This reverse map is the key to your error handling.
    id_to_name_map = pd.Series(batsman_stats.batter.values, index=batsman_stats.player_id).to_dict()

    batsman_stats.insert(0, 'match_id', match_id)
    # Reorder and select columns
    batsman_stats = batsman_stats[['match_id', 'player_id', 'runs', 'fours', 'sixs', 'dismissal']]
    
    # Handle players who are in the registry but not in the 'players' list (e.g., umpires)
    # This will prevent rows with a NaN player_id from breaking the script
    batsman_stats = batsman_stats.dropna(subset=['player_id'])

    data_to_insert = batsman_stats.to_dict(orient='records')
    return data_to_insert, id_to_name_map


# --- SELF HEALING PIPELINE ---
try:
    target_directory = 'Data/Matches'
    all_files_in_dir = os.listdir(target_directory)
    print(f"Found {len(all_files_in_dir)} files...")

    for file in all_files_in_dir:
        if file.endswith('.json'):
            file_path = os.path.join(target_directory, file)
            print(f"\n--- Processing file: {file} ---")
            
            try:
                # The data for this one file
                data, id_to_name = process_batsman_stats(file_path)
            except Exception as e:
                print(f"[ERROR] Failed to process JSON for file {file}. Error: {e}")
                continue # Skip to the next file

            success_count = 0
            fail_count = 0

            for row in data:
                try:
                    # Try to insert one row directly into the public table
                    supabase.table('batsman').upsert(row).execute()
                    success_count += 1
                
                except Exception as e:
                    # The insert failed, let's analyze the error
                    error_str = str(e)
                    if 'violates foreign key constraint' in error_str and 'player_master' in error_str:
                        fail_count += 1
                        
                        match = re.search(r"Key \(player_id\)=\((.*?)\) is not present", error_str)
                        
                        if match:
                            player_id = match.group(1) # This is now a string
                            player_name = id_to_name.get(player_id)
                            
                            if player_name:
                                print(f"  [QUEUE] Player '{player_name}' ({player_id}) missing. Adding to queue via RPC.")
                                
                                # This calls the 'queue_missing_player' function in PostgreSQL to safely insert the player into the ETL queue table.
                                rpc_params = {'p_id': player_id, 'p_name': player_name}
                                supabase.rpc('queue_missing_player', rpc_params).execute()
                            else:
                                print(f"  [ERROR] Could not find name for missing player_id {player_id}")
                        else:
                            print(f"  [ERROR] Could not parse FK error: {error_str}")
                    else:
                        # A different, unexpected error (e.g., bad match_id)
                        print(f"  [ERROR] Unexpected error for row {row.get('player_id')}: {e}")
                        fail_count += 1
            
            print(f"--- Finished file {file}. Success: {success_count} | Failed/Queued: {fail_count} ---")

except Exception as e:
    print(f"A critical error occurred: {e}")