from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client
import pandas as pd

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url,key)

try:
    df = pd.read_csv("Data/names.csv")
    df = df.replace({pd.NA: None, pd.NaT: None, 'NaN': None})#cleaning NaN values
    df = df.drop_duplicates(subset='player_id', keep='first')

    records = df.to_dict('records')
    response = supabase.table('player_master').insert(records).execute()
    if response.data:
        print(f"Successfully inserted data for {len(response.data)} records.")
    else:
        print(f"Data upserted (or skipped), but no data was returned.")
except FileNotFoundError:
    print(f"File nout found")
except Exception as e:
    print(f"An Error Occured {e}")