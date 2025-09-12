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

#creates the dictonary with players and their property
def playerdic(team):
    dic = {}
    for player in range(len(dump['info']['players'][team])):
        dic[dump['info']['players'][team][player]] = [
            {'match_id':''},
            {'player_id':''},
            {'runs':''},
            {'fours':''},
            {'sixes':''},
            {'no_of_balls':''}
        ]
    return dic

#function to add data into the Matches tables in the db
def add_data(data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    
    try:
        cursor.execute('''
            INSERT INTO batsman_stats (
                match_id,player_id,runs,fours,sixes,no_of_balls
            ) VALUES (?, ?, ?, ?, ? ,? )
        ''', (
            data[0], data[1], data[2], data[3], data[4], data[5]
        ))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("Table not found, creating one...")
            cursor.execute('''
                CREATE TABLE batsman_stats (
                    match_id TEXT,
                    player_id TEXT,
                    runs INTEGER,
                    fours INTEGER,
                    sixes INTEGER,
                    no_of_balls INTEGER,
                    PRIMARY KEY (match_id, player_id)
                )
            ''')
            conn.commit()

            # retry the insert
            cursor.execute('''
                INSERT INTO batsman_stats (
                    match_id, player_id, runs, fours, sixes, no_of_balls
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
        else:
            print("Error inserting:", e)
            conn.rollback()
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
        
        
        if batsman in team1dic:
            team1dic[batsman][5]['balls']+=1
        else:
            team2dic[batsman][5]['balls']+=1

        #batsman runs
        if batsman in team1dic:
            team1dic[batsman][2]['runs']+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            #fours
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman'] == 4:
                team1dic[batsman][3]['fours']+=1
            #sixes
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman'] == 6:
                team1dic[batsman][4]['sixes']+=1
        else:
            team2dic[batsman][2]['runs']+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            #fours
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman'] == 4:
                team2dic[batsman][3]['fours']+=1
            #sixes
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman'] == 6:
                team2dic[batsman][4]['sixes']+=1
    
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

            try:
                if dump['info']['outcome']['result']=='no result':
                    matchcount-=1
                    continue
                    print('match is incomplete')
            except(KeyError):
                pass#skip if result parameter not found

            team1dic=playerdic(dump['info']['teams'][0])
            team2dic=playerdic(dump['info']['teams'][1])

            team1=dump['info']['teams'][0]
            team2=dump['info']['teams'][1]

            keys1=list(team1dic)
            keys2=list(team2dic)

            #initialisation for team1
            for key in keys1:

                team1dic[key][0]=file.strip('.yaml')
                team1dic[key][1]= dump['info']['registry']['people'][key]
                team1dic[key][2]['runs']=0
                team1dic[key][3]['fours']=0
                team1dic[key][4]['sixes']=0
                team1dic[key][5]['balls']=0

            #initialisation for team2
            for key in keys2:

                team2dic[key][0]=file.strip('.yaml')
                team2dic[key][1]= dump['info']['registry']['people'][key]
                team2dic[key][2]['runs']=0
                team2dic[key][3]['fours']=0
                team2dic[key][4]['sixes']=0
                team2dic[key][5]['balls']=0
            
            counter(0)
            counter(1)

            data=[]
            for key in keys1:
                data.append(team1dic[key][0])
                data.append(team1dic[key][1])
                data.append(team1dic[key][2]['runs'])
                data.append(team1dic[key][3]['fours'])
                data.append(team1dic[key][4]['sixes'])
                data.append(team1dic[key][5]['balls'])

                
                add_data(data)
                data=[]

            print('next innings')

            for key in keys2:
                data.append(team2dic[key][0])
                data.append(team2dic[key][1])
                data.append(team2dic[key][2]['runs'])
                data.append(team2dic[key][3]['fours'])
                data.append(team2dic[key][4]['sixes'])
                data.append(team2dic[key][5]['balls'])

                
                add_data(data)
                data=[]

except FileNotFoundError:
    print(f"The directory '{target_directory}' does not exist. Please check the path.")
except PermissionError:
    print(f"Permission denied for accessing the directory '{target_directory}'.")
except Exception as e:
    print(f"An error occurred: {e}")
#the total matches executed
print(f'Total number of matches played: {matchcount}')