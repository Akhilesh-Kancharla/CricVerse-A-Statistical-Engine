import sqlite3
import yaml
import os

# Specify the target directory (replace with the full path of your directory)
target_directory = 'Matches'

#reads the files safely
def read(address):
    with open(address,'r') as file:
        data=yaml.safe_load(file)
    return data

#function to add data into the Matches tables in the db
def add_data(data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    
    try:
        cursor.execute('''
            INSERT INTO master_match (
                date,match_id,venue,city,team_1,team_2,toss_winner,toss_desicion,team_1_score,team_2_score,winner,man_of_the_match
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,? )
        ''', (
            data[0], data[1], data[2], data[3], data[4],
            data[5], data[6], data[7], data[8], data[9],data[10],data[11]
        ))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("Table not found, creating one...")
            cursor.execute('''
                CREATE TABLE master_match (
                    date DATE,
                    match_id TEXT,
                    venue TEXT,
                    city TEXT,
                    team_1 TEXT,
                    team_2 TEXT,
                    toss_winner TEXT,
                    toss_desicion TEXT,
                    team_1_score INTEGER,
                    team_2_score INTEGER,
                    winner TEXT,
                    man_of_the_match TEXT,
                    PRIMARY KEY (date, match_id)
                )
            ''')
            conn.commit()

            # retry the insert
    finally:
        conn.close()
        print(data)

#the main iterator which iterates through the innings and caluclates the runs and the wickets
def counter(innings):
    count=0 #runs counter

    #for dynamically switching from 1st innings to 2nd innings
    if innings==0:
        a='1st innings'
    else:
        a='2nd innings'
    
    #actuall counter
    balcount=len(dump['innings'][innings][a]['deliveries'])
    for ball in range(balcount):
        #getting the names of required properties from dump
        ball_list=dump['innings'][innings][a]['deliveries'][ball]
        ballname=list(ball_list.keys())[0]
        batsman=dump['innings'][innings][a]['deliveries'][ball][ballname]['batsman']
        bowler=dump['innings'][innings][a]['deliveries'][ball][ballname]['bowler']

        count+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['total']

    return count


matchcount=0
# Handle exceptions
try:
    # Iterate through all files in the target directory
    for file in os.listdir(target_directory):
        # Construct the full file path
        file_path = os.path.join(target_directory, file)
        
        # Check if it's a file (skip directories)
        if os.path.isfile(file_path):
            matchcount+=1
            #for skipping files that are not in yaml format
            if '.yaml' not in file:
                matchcount-=1
                continue
            
            data=[]#temporay list to fold all the parameters to add into the db
            
            print(matchcount,file) #prints file name
            address=file_path
            dump = read(address)
        
            #for skipping incomplete matches
            try:
                if dump['info']['outcome']['result']=='no result':
                    matchcount-=1
                    continue
                    print('match is incomplete')
            except(KeyError):
                 ...#skip if result parameter not found

            #the variables have the team names participating in the match
            team1=dump['info']['teams'][0]
            team2=dump['info']['teams'][1]

            #toss
            tosswin=dump['info']['toss']['winner']
            desicion=dump['info']['toss']['decision']
            if desicion=='bat':
                if team1 is not tosswin:
                    team1,team2=team2,team1
            else:
                if team2 is not tosswin:
                    team1,team2=team2,team1

            count1=counter(0)
            count2=counter(1)

            #data part to append to list
            data.append(dump['info']['dates'][0])
            data.append(file.strip('.yaml'))
            data.append(dump['info']['venue'])
            try:
                data.append(dump['info']['city'])
            except(KeyError):
                data.append('not found')
            data.append(team1)
            data.append(team2)
            data.append(tosswin)
            data.append(desicion)
            data.append(count1)
            data.append(count2)
            try:
                data.append(dump['info']['outcome']['winner'])
            except(Exception):
                data.append(dump['info']['outcome']['eliminator']+' - '+dump['info']['outcome']['result'])
            data.append(dump['info']['player_of_match'][0])

            add_data(data)
except FileNotFoundError:
    print(f"The directory '{target_directory}' does not exist. Please check the path.")
except PermissionError:
    print(f"Permission denied for accessing the directory '{target_directory}'.")
except Exception as e:
    print(f"An error occurred: {e}")
#the total matches executed
print(f'Total number of matches played: {matchcount}')