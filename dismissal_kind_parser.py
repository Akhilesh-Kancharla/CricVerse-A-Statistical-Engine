from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
import pandas as pd
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url,key)

try:
    df = pd.read_csv("Data/dismissal_kinds.csv")
    records = df.to_dict('records')
    response = supabase.table('dismissal_kind').upsert(records).execute()

    if response.data:
        print(f"Successfully upserted data. {len(response.data)} records processed.")
    else:
        print("Upsert successful.")
except FileNotFoundError:
    print("File not found")
except Exception as e:
    print(f"Unexpected error occured: {e} ")