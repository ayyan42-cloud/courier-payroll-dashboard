import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os, json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_client():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(
            json.loads(creds_json), scopes=SCOPES
        )
    else:
        creds = Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
    return gspread.authorize(creds)

def load_data(sheet_name="CourierPayroll"):
    client = get_client()
    sh = client.open(sheet_name)
    ws = sh.sheet1
    data = ws.get_all_records()
    return pd.DataFrame(data)

def upsert_rows(df_new, sheet_name="CourierPayroll"):
    """Append new months, update existing Rider+Month in place."""
    client = get_client()
    sh = client.open(sheet_name)
    ws = sh.sheet1

    existing = pd.DataFrame(ws.get_all_records())
    headers = ws.row_values(1)

    # Composite key = Courier ID + Pay Month
    df_new["_key"] = df_new["courier ID"].astype(str) + "|" + df_new["pay month"].astype(str)
    if not existing.empty:
        existing["_key"] = existing["courier ID"].astype(str) + "|" + existing["pay month"].astype(str)
        existing_keys = set(existing["_key"])
    else:
        existing_keys = set()

    new_rows = []
    for _, row in df_new.iterrows():
        if row["_key"] not in existing_keys:
            new_rows.append([row.get(h, "") for h in headers])
        else:
            # Update existing row in place
            idx = existing[existing["_key"] == row["_key"]].index[0]
            row_num = idx + 2  # +2 because of header + 0-index
            for col_idx, h in enumerate(headers, start=1):
                ws.update_cell(row_num, col_idx, row.get(h, ""))

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    return len(new_rows)