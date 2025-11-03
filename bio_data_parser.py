from dotenv import load_dotenv
load_dotenv()
import pandas as pd
import os
import json
from supabase import create_client


url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url,key)

try:
    data = json.load(open("Data/player.json"))
    df = pd.json_normalize(data,record_path='data')#normalizing nested json data
    df = df.drop(columns=['resource','updated_at','position.resource','position.id'])#dropping unnecessary columns
    df = df.rename(columns={'position.name':'role'})#renaming column to match with db
    
    df = df.replace('0000-00-00', None)#cleaning invalid date values
    df = df.replace({pd.NA: None, pd.NaT: None, 'NaN': None})#cleaning NaN values
    records = df.to_dict('records')
    response = supabase.table('bio_data').insert(records).execute()
    if response.data:
        print(f"Successfully inserted data for {len(response.data)} records.")
    else:
        print(f"Data upserted (or skipped), but no data was returned.")
except FileNotFoundError:
    print("File not Found")
except Exception as e:
    print(f"Unexpected Erorr {e}")