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


def process_bowler_stats(data_file):
    """
    Transforms raw JSON match data into a clean list of dictionaries
    containing bowling statistics for each player.
    """
    match_id = os.path.basename(data_file).split('.')[0]
    with open(data_file) as f:
        data = json.load(f)

    all_deliveries = []
    for inning in data['innings']:
        # Add inning number to each delivery
        inning_num = 1 if inning['team'] == data['info']['teams'][0] else 2
        for over in inning['overs']:
            for delivery in over['deliveries']:
                delivery_info = delivery.copy()
                delivery_info['over'] = over['over']
                delivery_info['inning'] = inning_num
                all_deliveries.append(delivery_info)
    
    if not all_deliveries:
        return [], {}

    df = pd.json_normalize(all_deliveries)

    # Ensure extra columns exist to prevent KeyErrors
    if 'extras.wides' not in df.columns:
        df['extras.wides'] = np.nan
    if 'extras.noballs' not in df.columns:
        df['extras.noballs'] = np.nan
    if 'extras.byes' not in df.columns:
        df['extras.byes'] = np.nan
    if 'extras.legbyes' not in df.columns:
        df['extras.legbyes'] = np.nan

    # Runs given (excluding byes and legbyes)
    df['runs_conceded'] = df['runs.total']
    # Wides and no-balls are extras, but the runs from them are still conceded by the bowler.
    # Byes and leg-byes are not.
    if 'extras.byes' in df.columns:
        df['runs_conceded'] -= df['extras.byes'].fillna(0)
    if 'extras.legbyes' in df.columns:
        df['runs_conceded'] -= df['extras.legbyes'].fillna(0)


    # Basic stats calculation
    bowler_stats = df.groupby('bowler').agg(
        runs_given=('runs_conceded', 'sum'),
        wides=('extras.wides', 'sum'),
        no_balls=('extras.noballs', 'sum')
    ).reset_index()

    # Calculate balls_bowled correctly (only legal deliveries)
    legal_deliveries = df[df['extras.wides'].isna() & df['extras.noballs'].isna()]
    balls_bowled_count = legal_deliveries.groupby('bowler').size().reset_index(name='balls_bowled')
    bowler_stats = pd.merge(bowler_stats, balls_bowled_count, on='bowler', how='left')
    
    # Wickets calculation (excluding run outs, etc.)
    wickets_df = df.dropna(subset=['wickets'])
    wickets_list = []
    for _, row in wickets_df.iterrows():
        bowler = row['bowler']
        for wicket in row['wickets']:
            if wicket['kind'] not in ['run out', 'retired hurt', 'obstructing the field', 'retired out']:
                wickets_list.append({'bowler': bowler})
    
    if wickets_list:
        wickets_count = pd.DataFrame(wickets_list).groupby('bowler').size().reset_index(name='wickets')
        bowler_stats = pd.merge(bowler_stats, wickets_count, on='bowler', how='left')
    else:
        bowler_stats['wickets'] = 0

    # Maiden overs calculation
    runs_per_over = df.groupby(['bowler', 'inning', 'over'])['runs_conceded'].sum().reset_index()
    maiden_overs = runs_per_over[runs_per_over['runs_conceded'] == 0].groupby('bowler').size().reset_index(name='maiden_overs')
    bowler_stats = pd.merge(bowler_stats, maiden_overs, on='bowler', how='left')

    # Hat-trick calculation
    df['is_wicket'] = df['wickets'].apply(lambda x: 1 if isinstance(x, list) and len(x) > 0 and x[0]['kind'] not in ['run out', 'retired hurt', 'obstructing the field', 'retired out'] else 0)
    df['delivery_index'] = df.index
    
    hat_trick_bowlers = []
    wickets_in_a_row = df[df['is_wicket'] == 1]
    if len(wickets_in_a_row) >= 3:
        for i in range(len(wickets_in_a_row) - 2):
            w1 = wickets_in_a_row.iloc[i]
            w2 = wickets_in_a_row.iloc[i+1]
            w3 = wickets_in_a_row.iloc[i+2]
            
            # Check for same bowler and consecutive deliveries
            if (w1['bowler'] == w2['bowler'] == w3['bowler']) and \
               (w2['delivery_index'] == w1['delivery_index'] + 1) and \
               (w3['delivery_index'] == w2['delivery_index'] + 1):
                hat_trick_bowlers.append(w1['bowler'])

    bowler_stats['hat_trick'] = bowler_stats['bowler'].apply(lambda x: 1 if x in hat_trick_bowlers else 0)

    # Get all players from the match
    all_players_list = []
    for team in data['info']['players']:
        all_players_list.extend(data['info']['players'][team])
    all_players_df = pd.DataFrame(all_players_list, columns=['bowler'])

    # Merge to include all players, even those who didn't bowl
    bowler_stats = pd.merge(all_players_df, bowler_stats, on='bowler', how='left')

    # Fill stats for non-bowlers with 0
    fill_cols = ['runs_given', 'wides', 'no_balls', 'wickets', 'maiden_overs', 'hat_trick', 'balls_bowled']
    for col in fill_cols:
        if col not in bowler_stats.columns:
            bowler_stats[col] = 0
    bowler_stats[fill_cols] = bowler_stats[fill_cols].fillna(0)
    
    for col in fill_cols:
        bowler_stats[col] = bowler_stats[col].astype(int)

    # Create player_id column
    people = data['info']['registry']['people']
    bowler_stats['player_id'] = bowler_stats['bowler'].map(people)

    id_to_name_map = pd.Series(bowler_stats.bowler.values, index=bowler_stats.player_id.astype(str)).to_dict()

    bowler_stats.insert(0, 'match_id', match_id)
    
    final_cols = ['match_id', 'player_id', 'balls_bowled', 'runs_given', 'wickets', 'hat_trick', 'wides', 'no_balls', 'maiden_overs']
    bowler_stats = bowler_stats[final_cols]
    
    bowler_stats = bowler_stats.dropna(subset=['player_id'])
    bowler_stats['player_id'] = bowler_stats['player_id'].astype(str)

    data_to_insert = bowler_stats.to_dict(orient='records')
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
                data, id_to_name = process_bowler_stats(file_path)
            except Exception as e:
                print(f"[ERROR] Failed to process JSON for file {file}. Error: {e}")
                continue

            success_count = 0
            fail_count = 0

            for row in data:
                try:
                    # Try to insert one row directly into the public table
                    supabase.table('bowler').upsert(row).execute()
                    success_count += 1
                
                except Exception as e:
                    error_str = str(e)
                    if 'violates foreign key constraint' in error_str and 'player_master' in error_str:
                        fail_count += 1
                        
                        match = re.search(r"Key \(player_id\)\=\((.*?)\) is not present", error_str)
                        
                        if match:
                            player_id = match.group(1)
                            player_name = id_to_name.get(player_id)
                            
                            if player_name:
                                print(f"  [QUEUE] Player '{player_name}' ({player_id}) missing. Adding to queue via RPC.")
                                
                                rpc_params = {'p_id': player_id, 'p_name': player_name}
                                supabase.rpc('queue_missing_player', rpc_params).execute()
                            else:
                                print(f"  [ERROR] Could not find name for missing player_id {player_id}")
                        else:
                            print(f"  [ERROR] Could not parse FK error: {error_str}")
                    else:
                        print(f"  [ERROR] Unexpected error for row {row.get('player_id')}: {e}")
                        fail_count += 1
            
            print(f"--- Finished file {file}. Success: {success_count} | Failed/Queued: {fail_count} ---")

except Exception as e:
    print(f"A critical error occurred: {e}")
