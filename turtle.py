# turtle.py
from __future__ import annotations
import pandas as pd
import datetime as dt
import unicodedata

def _norm(s: str) -> str:
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.strip().lower()

def get_today_turtle_objective(load_sheet_fn, client, gsheet_id: str) -> str:
    """Lê aba 'Turtle' e retorna objetivo do dia (ou último <= hoje)."""
    try:
        turtle = load_sheet_fn(client, gsheet_id, "Turtle")
        if turtle is None or turtle.empty:
            return "-"
        name_map = {_norm(c): c for c in turtle.columns}
        date_col = next((name_map[k] for k in ("data","date","dia") if k in name_map), None)
        obj_col  = next((name_map[k] for k in ("objetivo","objective","goal","meta") if k in name_map), None)
        if not date_col or not obj_col:
            return "-"
        s = turtle[date_col]
        if pd.api.types.is_numeric_dtype(s):
            dates = pd.to_datetime(s, unit="D", origin="1899-12-30", errors="coerce")
        else:
            dates = pd.to_datetime(s, errors="coerce", dayfirst=True)
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("America/Sao_Paulo")
            today = dt.datetime.now(tz).date()
        except Exception:
            today = dt.date.today()
        turtle["_date"] = dates.dt.date
        valid = turtle.dropna(subset=["_date"])
        row = valid.loc[valid["_date"] == today]
        if row.empty:
            row = valid.loc[valid["_date"] <= today].sort_values("_date")
            if row.empty:
                return "-"
        objetivo_val = str(row.iloc[-1][obj_col]).strip()
        return objetivo_val if objetivo_val and objetivo_val.lower() not in {"nan","none"} else "-"
    except Exception:
        return "-"
