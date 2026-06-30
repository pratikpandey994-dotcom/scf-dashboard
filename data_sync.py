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
DRIVE_FOLDER_ID = '1ZjiUf4xdjrdiRqoXYxUEYjhR0eJ2mPj6'

SHEET_FILES = {
    'reactlist.csv': '1SIwm7hUghfG4Mz0pTPhH0CaWkOd-P2XZ2vL6uQYslDQ',
    'industry.csv': '1zm2AxkCotTqk4jAggGNGChTppWqajTR4puULC0leU2U'
}

def get_service():
    # Attempt to load credentials from Streamlit Secrets or fallback to local path
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
        elif "type" in st.secrets and st.secrets["type"] == "service_account":
            creds_info = dict(st.secrets)
        else:
            keys = list(st.secrets.keys())
            raise ValueError(f"WARNING: No Google credentials found. st.secrets keys are: {keys}")
            
        if "private_key" in creds_info:
            pk = creds_info["private_key"]
            pk = pk.replace('\\n', '\n')
            if '\n' not in pk and ' ' in pk:
                pk = pk.replace('-----BEGIN PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----\n')
                pk = pk.replace('-----END PRIVATE KEY-----', '\n-----END PRIVATE KEY-----')
                pk = pk.replace(' ', '\n')
                pk = pk.replace('-----BEGIN\nPRIVATE\nKEY-----', '-----BEGIN PRIVATE KEY-----')
                pk = pk.replace('-----END\nPRIVATE\nKEY-----', '-----END PRIVATE KEY-----')
            creds_info["private_key"] = pk
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    except Exception as e:
        # Fallback for local development
        key_path = r"C:\Users\PratikPandey\Downloads\robotic-haven-499821-d2-35b004d34efd.json"
        if os.path.exists(key_path):
            creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        else:
            # If we reach here on cloud, append the secrets keys for debugging
            keys = list(st.secrets.keys()) if hasattr(st, "secrets") else []
            pk_repr = repr(creds_info.get("private_key", ""))[:100] + "..." if 'creds_info' in locals() else ""
            raise ValueError(f"No Google credentials found. st.secrets keys are: {keys}. Exception: {e}. PK repr: {pk_repr}")
    return build('drive', 'v3', credentials=creds)

@st.cache_data(ttl=86400) # Daily refresh for Drive files
def sync_drive_data_v2():
    service = get_service()
    
    out_dir = os.path.join("static", "data")
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Fetching files from Drive folder {DRIVE_FOLDER_ID}...")
    results = service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
        pageSize=50, fields="nextPageToken, files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    if not items:
        print("No files found in the Drive folder.")
        return time.time()
        
    for item in items:
        file_id = item['id']
        raw_name = item['name'].lower()
        
        # Determine the target filename based on keywords in the Google Drive filename
        filename = None
        if 'master' in raw_name:
            filename = 'master.xlsx'
        elif 'invoice' in raw_name:
            filename = 'v2.xlsx'
        elif 'historic' in raw_name:
            filename = 'obhist.xlsx'
        elif 'refresh' in raw_name:
            filename = 'refresh.xlsx'
        elif 'daily' in raw_name:
            filename = 'obcurr.xlsx'
            
        if not filename:
            print(f"Skipping unrecognized file: {item['name']}")
            continue
            
        print(f"Downloading {item['name']} as {filename}...")
        request = service.files().get_media(fileId=file_id)
        content = request.execute()
        file_path = os.path.join(out_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Convert Excel to JSON for lightning fast frontend loading
        try:
            print(f"Converting {filename} to JSON...")
            df = pd.read_excel(file_path)
            # Fill NaN with None so it translates to JSON null
            df = df.where(pd.notnull(df), None)
            json_path = os.path.join(out_dir, filename.replace('.xlsx', '.json'))
            df.to_json(json_path, orient='records', date_format='iso')
            print(f"Converted {filename} to JSON")
        except Exception as e:
            print(f"Failed to convert {filename} to JSON: {e}")
            
        print(f"Synced {filename}")
    return time.time()

@st.cache_data(ttl=43200) # Twice a day refresh for Google Sheets
def sync_sheets_data_v2():
    service = get_service()
    
    out_dir = os.path.join("static", "data")
    os.makedirs(out_dir, exist_ok=True)
    
    for filename, file_id in SHEET_FILES.items():
        print(f"Downloading {filename}...")
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        content = request.execute()
        file_path = os.path.join(out_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Convert CSV to JSON for lightning fast frontend loading
        if filename == 'reactlist.csv':
            try:
                print(f"Converting {filename} to JSON...")
                df = pd.read_csv(file_path)
                df = df.where(pd.notnull(df), None)
                json_path = os.path.join(out_dir, filename.replace('.csv', '.json'))
                df.to_json(json_path, orient='records', date_format='iso')
                print(f"Converted {filename} to JSON")
            except Exception as e:
                print(f"Failed to convert {filename} to JSON: {e}")
        
        # Post-process industry.csv into a JSON map that dashboard.html can directly consume
        if filename == 'industry.csv':
            process_industry_csv(file_path, out_dir)
        print(f"Synced {filename}")
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
    sync_drive_data_v2()
    sync_sheets_data_v2()
