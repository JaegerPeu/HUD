# gsheets_io.py
from __future__ import annotations
from typing import Optional, Dict, Any
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials

def _authorize_gspread(sa_info: Optional[Dict[str, Any]], sa_file: Optional[str]) -> gspread.Client:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    if sa_info:
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        return gspread.authorize(creds)
    if sa_file:
        creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
        return gspread.authorize(creds)
    raise ValueError("Forneça credenciais do Google (st.secrets['gcp_service_account'] OU env GCP_SERVICE_ACCOUNT_FILE).")

def load_sheet(client: gspread.Client, gsheet_id: str, sheet_name: str) -> pd.DataFrame:
    ws = client.open_by_key(gsheet_id).worksheet(sheet_name)
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0)
    df = df.dropna(how="all")
    return df

def get_client(sa_info: Optional[Dict[str, Any]], sa_file: Optional[str]) -> gspread.Client:
    return _authorize_gspread(sa_info, sa_file)
