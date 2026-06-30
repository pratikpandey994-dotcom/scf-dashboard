import os
import io
import json
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import streamlit as st
import time

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# File IDs determined from the user's provided sheets and drive files
DRIVE_FILES = {
    'master.xlsx': '1tedCS9rJZhEw4Bl9Nk_3xNsvppGkTfCZ',
    'v2.xlsx': '1XlrwlBwJS3lhMvyI_2VGSdjKEf4PukTy',
    'obhist.xlsx': '1SQnvRmL7lmhWXEttRW9XUW-DcApVGh7I'
}

SHEET_FILES = {
    'reactlist.csv': '1SIwm7hUghfG4Mz0pTPhH0CaWkOd-P2XZ2vL6uQYslDQ',
    'industry.csv': '1zm2AxkCotTqk4jAggGNGChTppWqajTR4puULC0leU2U'
}

def get_service():
    # Attempt to load credentials from Streamlit Secrets or fallback to local path
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            raise KeyError("No secrets")
    except Exception:
        # Fallback for local development
        key_path = r"C:\Users\PratikPandey\Downloads\robotic-haven-499821-d2-35b004d34efd.json"
        if os.path.exists(key_path):
            creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        else:
            print("WARNING: No Google credentials found. Sync will fail.")
            return None
    return build('drive', 'v3', credentials=creds)

@st.cache_data(ttl=86400) # Daily refresh for Drive files
def sync_drive_data():
    service = get_service()
    if not service: return False
    
    out_dir = os.path.join("static", "data")
    os.makedirs(out_dir, exist_ok=True)
    
    for filename, file_id in DRIVE_FILES.items():
        try:
            print(f"Downloading {filename}...")
            request = service.files().get_media(fileId=file_id)
            content = request.execute()
            with open(os.path.join(out_dir, filename), 'wb') as f:
                f.write(content)
            print(f"Synced {filename}")
        except Exception as e:
            print(f"Error syncing {filename}: {e}")
    return time.time()

@st.cache_data(ttl=43200) # Twice a day refresh for Google Sheets
def sync_sheets_data():
    service = get_service()
    if not service: return False
    
    out_dir = os.path.join("static", "data")
    os.makedirs(out_dir, exist_ok=True)
    
    for filename, file_id in SHEET_FILES.items():
        try:
            print(f"Downloading {filename}...")
            request = service.files().export_media(fileId=file_id, mimeType='text/csv')
            content = request.execute()
            with open(os.path.join(out_dir, filename), 'wb') as f:
                f.write(content)
            print(f"Synced {filename}")
            
            # Post-process industry.csv into a JSON map that dashboard.html can directly consume
            if filename == 'industry.csv':
                process_industry_csv(os.path.join(out_dir, filename), out_dir)
                
        except Exception as e:
            print(f"Error syncing {filename}: {e}")
    return time.time()

def process_industry_csv(csv_path, out_dir):
    import re
    try:
        df = pd.read_csv(csv_path)
        industry_map = {}
        INDUSTRY_SUFFIX = ['llc','inc','incorporated','corporation','corp','company','co','ltd','limited','llp','lp','plc','the','usa','us']
        
        for _, row in df.iterrows():
            buyer = str(row.get('Buyer Name', '')).strip().lower()
            ind = str(row.get('Primary Industry', '')).strip()
            if not buyer or not ind or ind == 'nan': continue
            
            # Emulate dashboard.html normIndName logic to guarantee matching keys
            parts = [p for p in buyer.split(' ') if p and p not in INDUSTRY_SUFFIX]
            core = "".join(parts)
            
            changed = True
            while changed:
                changed = False
                for suf in INDUSTRY_SUFFIX:
                    if len(core) > len(suf) and core.endswith(suf):
                        core = core[:-len(suf)]
                        changed = True
            
            norm_key = re.sub(r'[^a-z0-9]', '', core)
            if norm_key:
                industry_map[norm_key] = ind
                
        with open(os.path.join(out_dir, 'industry.json'), 'w') as f:
            json.dump(industry_map, f)
            
    except Exception as e:
        print(f"Error processing industry.csv: {e}")

def run_syncs():
    sync_drive_data()
    sync_sheets_data()
