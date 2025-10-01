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
            {'wickets':''},
            {'hatrick':''},
            {'balls_played':''},
            {'maidens':''},
            {'runs_given':''},
            {'no_balls':''},
            {'wides':''}
        ]
    return dic

#function to add data into the Matches tables in the db
def add_data(data):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    
    try:
        cursor.execute('''
            INSERT INTO bowling_stats (
                match_id,player_id,bowling_type,wickets,hatrick,balls_played,maidens,runs_given,no_balls,wides
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
        ''', (
            data[0], data[1],'', data[2], data[3], data[4],
            data[5], data[6], data[7], data[8]
        ))
        conn.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("Table not found, creating one...")
            cursor.execute('''
                CREATE TABLE bowling_stats (
                    match_id TEXT,
                    player_id TEXT,
                    bowling_type TEXT,
                    wickets INTEGER,
                    hatrick INTEGER,
                    balls_played INTEGER,
                    maidens INTEGER,
                    runs_given INTEGER,
                    no_balls INTEGER,
                    wides INTEGER,
                    PRIMARY KEY (match_id, player_id)
                )
            ''')
            conn.commit()

            # retry the insert
            cursor.execute('''
                INSERT INTO bowling_stats (
                    match_id,player_id,bowling_type,wickets,hatrick,balls_played,maidens,runs_given,no_balls,wides
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
                ''', (
                    data[0], data[1],'', data[2], data[3], data[4],
                    data[5], data[6], data[7], data[8]
                ))
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
    current_over = -1
    runs_in_over = 0
    bowler_of_over = None

    for ball in range(balcount):
        #getting the names of required properties from dump
        ball_list=dump['innings'][innings][a]['deliveries'][ball]
        ballname=list(ball_list.keys())[0]
        batsman=dump['innings'][innings][a]['deliveries'][ball][ballname]['batsman']
        bowler=dump['innings'][innings][a]['deliveries'][ball][ballname]['bowler']

        over_num = int(float(ballname))

        # Maiden over logic: check if a new over has started
        if over_num != current_over:
            # If it's a new over, check if the *previous* one was a maiden
            if current_over != -1 and runs_in_over == 0 and bowler_of_over:
                if bowler_of_over in team1dic:
                    team1dic[bowler_of_over][5]['maidens'] += 1
                elif bowler_of_over in team2dic:
                    team2dic[bowler_of_over][5]['maidens'] += 1
            
            # Reset for the new over
            current_over = over_num
            runs_in_over = 0
            bowler_of_over = bowler

        count+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['total']
        
        #wicket counter for bowlers
        try:
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['wicket']['player_out']==batsman:
                if batsman in team1dic:
                    team2dic[bowler][2]['wickets']+=1
                else:
                    team1dic[bowler][2]['wickets']+=1
        except(KeyError):
            pass

        #runs_given and balls_played
        if bowler in team1dic:
            team1dic[bowler][6]['runs_given']+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            runs_in_over += dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            team1dic[bowler][4]['balls_played']+=1
        else:
            team2dic[bowler][6]['runs_given']+=dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            runs_in_over += dump['innings'][innings][a]['deliveries'][ball][ballname]['runs']['batsman']
            team2dic[bowler][4]['balls_played']+=1
        
        #wides
        try:
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['extras']['wides']==1:
                
                if bowler in team1dic:
                    team1dic[bowler][8]['wides']+=1
                else:
                    team2dic[bowler][8]['wides']+=1
        except(KeyError):
            pass
        
        #noballs
        try:
            if dump['innings'][innings][a]['deliveries'][ball][ballname]['extras']['noballs']==1:
                if bowler in team1dic:
                    team1dic[bowler][7]['no_balls']+=1
                else:
                    team2dic[bowler][7]['no_balls']+=1
        except(KeyError):
            pass

    # After the loop, check if the very last over of the innings was a maiden
    if current_over != -1 and runs_in_over == 0 and bowler_of_over:
        if bowler_of_over in team1dic:
            team1dic[bowler_of_over][5]['maidens'] += 1
        elif bowler_of_over in team2dic:
            team2dic[bowler_of_over][5]['maidens'] += 1

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
                team1dic[key][1]=dump['info']['registry']['people'][key]
                team1dic[key][2]['wickets']=0
                team1dic[key][3]['hatrick']=0
                team1dic[key][4]['balls_played']=0
                team1dic[key][5]['maidens']=0
                team1dic[key][6]['runs_given']=0
                team1dic[key][7]['no_balls']=0
                team1dic[key][8]['wides']=0
            
            #initialisation for team2
            for key in keys2:

                team2dic[key][0]=file.strip('.yaml')
                team2dic[key][1]=dump['info']['registry']['people'][key]
                team2dic[key][2]['wickets']=0
                team2dic[key][3]['hatrick']=0
                team2dic[key][4]['balls_played']=0
                team2dic[key][5]['maidens']=0
                team2dic[key][6]['runs_given']=0
                team2dic[key][7]['no_balls']=0
                team2dic[key][8]['wides']=0

            counter(0)
            counter(1)

            data=[]
            for key in keys1:
                data.append(team1dic[key][0])
                data.append(team1dic[key][1])
                data.append(team1dic[key][2]['wickets'])
                data.append(team1dic[key][3]['hatrick'])
                data.append(team1dic[key][4]['balls_played'])
                data.append(team1dic[key][5]['maidens'])
                data.append(team1dic[key][6]['runs_given'])
                data.append(team1dic[key][7]['no_balls'])
                data.append(team1dic[key][8]['wides'])

                print(data)
                add_data(data)
                data=[]

            print('next innings')

            for key in keys2:
                data.append(team2dic[key][0])
                data.append(team2dic[key][1])
                data.append(team2dic[key][2]['wickets'])
                data.append(team2dic[key][3]['hatrick'])
                data.append(team2dic[key][4]['balls_played'])
                data.append(team2dic[key][5]['maidens'])
                data.append(team2dic[key][6]['runs_given'])
                data.append(team2dic[key][7]['no_balls'])
                data.append(team2dic[key][8]['wides'])

                print(data)
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