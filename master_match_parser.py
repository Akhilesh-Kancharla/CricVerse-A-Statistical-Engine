from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from postgrest.exceptions import APIError
import pandas as pd
import os
import json

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url,key)

def match_record(file_path,file_name): 
    data = json.load(open(file_path))

    # Extract Match Info
    date = data['info']['dates'][0]
    season = data['info']['season']
    if isinstance(season, str):
        season = int(season[0:4])

    
    # Fetch Venue ID from Supabase
    venue = data['info']['venue']
    response = supabase.rpc('find_venue_id', {'file_name': venue}).execute()
    venue=response.data
    
    city = data.get('info', {}).get('city')

    # Extract Team Names
    team1 = data['info']['teams'][0]
    team2 = data['info']['teams'][1]

    # Fetch Team IDs from Supabase
    response = supabase.table('teams').select("id").eq('name',team1).execute()
    team1id=response.data[0]['id']
    response = supabase.table('teams').select("id").eq('name',team2).execute()
    team2id=response.data[0]['id']

    # Extract Toss Winner
    toss_winner = data['info']['toss']['winner']
    if toss_winner == team1:
        toss_winner = team1id
    else:
        toss_winner = team2id
    
    # Extract Toss Decision
    toss_decision = data['info']['toss']['decision']

    # Extract Match Winner
    winner = data.get('info', {}).get('outcome', {}).get('winner')
    if winner is None:
        winner = data.get('info', {}).get('outcome', {}).get('eliminator')
    if winner == team1:
        winner = team1id
    else:
        winner = team2id

    # Extract Player of the Match
    player_of_match = data.get('info', {}).get('player_of_match', [None])[0]
    if player_of_match is not None:
        player_of_match = data['info']['registry']['people'][player_of_match]

    # Calculate Team Runs
    try:
        df1 = pd.json_normalize(data["innings"][0],record_path=['overs', 'deliveries'])
        t1runs = int(df1['runs.total'].sum())
    except IndexError:
        t1runs = 0
    try:
        df2 = pd.json_normalize(data["innings"][1],record_path=['overs', 'deliveries'])
        t2runs = int(df2['runs.total'].sum())
    except IndexError:
        t2runs = 0

    record = {'match_id':int(file_name.strip('.json')),'date_of_match':date,'venue':venue,'city':city,'team1':team1id,'team2':team2id,'toss_winner':toss_winner,'toss_desicion':toss_decision,'team1score':t1runs,'team2score':t2runs,'winner':winner,'player_of_match':player_of_match,'season':season}
    return record

target_directory = 'Data/Matches'
faulty_files = []  # A list to store the files that failed
successful_count = 0
total_files = 0

try:
    all_files_in_dir = os.listdir(target_directory)
    total_files = len([f for f in all_files_in_dir if f.endswith('.json')])

    for file1 in all_files_in_dir:
        if file1.endswith('.json'):
            file_path = os.path.join(target_directory, file1)
            
            try:
                # 1. Parse the file
                record = match_record(file_path, file1)
                
                # 2. Try to insert just this one record
                response = supabase.table('master_match').insert(record).execute()
                
                successful_count += 1
                print(f"SUCCESS: {file1} (Processed {successful_count}/{total_files})")

            except APIError as e:
                # 3. Catch the database error (like your Foreign Key error)
                print(f"DB ERROR in {file1}: {e.message}")
                faulty_files.append({'file': file1, 'error': e.message})
            except Exception as e:
                # 4. Catch any other error (like a parsing error in match_record)
                print(f"PARSE ERROR in {file1}: {e}")
                faulty_files.append({'file': file1, 'error': str(e)})

    print(f'\n--- Summary ---')
    print(f'Successfully inserted: {successful_count}')
    print(f'Total files skipped with errors: {len(faulty_files)}')
    
    # 5. Print the final log of faulty files
    if faulty_files:
        print("\n--- Faulty File Log ---")
        for item in faulty_files:
            print(f"File: {item['file']}\n  Error: {item['error']}\n")

except FileNotFoundError:
    print(f"Error: Directory not found at {target_directory}")
except Exception as e:
    print(f"A critical error stopped the process: {e}")