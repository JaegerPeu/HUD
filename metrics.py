# metrics.py
from __future__ import annotations
from typing import Optional, Tuple, Dict
import pandas as pd
import datetime as dt
import math

# ---------- Helpers de formato ----------
def minutes_to_mmss(value: Optional[float]) -> str:
    if value is None or (isinstance(value,float) and (math.isnan(value) or value <= 0)):
        return "-"
    total_seconds = int(round(value * 60))
    m, s = divmod(total_seconds, 60)
    return f"{m}:{s:02d}"

def hours_to_hhmm(value: Optional[float]) -> str:
    if value is None or (isinstance(value,float) and math.isnan(value)):
        return "-"
    # aceita decimais (ex.: 7.25 -> 07:15)
    total_minutes = int(round(float(value) * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h:02d}:{m:02d}"

def int_fmt(x: Optional[float]) -> str:
    try:
        return f"{int(round(float(x))):,}".replace(",", ".")
    except Exception:
        return "-"

def num_fmt(x: Optional[float], nd=2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "-"

# ---------- Datas de período ----------
def today_brt() -> dt.date:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:
        return dt.date.today()

def start_of_week(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())

def start_of_month(d: dt.date) -> dt.date:
    return d.replace(day=1)

def start_of_quarter(d: dt.date) -> dt.date:
    q = (d.month - 1)//3 + 1
    return dt.date(d.year, 3*(q-1)+1, 1)

def start_of_year(d: dt.date) -> dt.date:
    return dt.date(d.year, 1, 1)

# ---------- Energia / Sono / Stress ----------
def energy_pct_from_row(row: pd.Series) -> Optional[int]:
    for col in ["Body Battery (máx)", "Body Battery (end)"]:
        if col in row and pd.notna(row[col]):
            try:
                return int(row[col])
            except Exception:
                continue
    return None

def energy_bar_10(pct: Optional[int]) -> str:
    if pct is None:
        return "[..........]"
    filled = max(0, min(10, round(pct/10)))
    return "[" + "█"*filled + "·"*(10-filled) + "]"

def stress_wtd_mean(daily_df: pd.DataFrame) -> Optional[float]:
    if "Data" not in daily_df.columns or "Stress (média)" not in daily_df.columns:
        return None
    d = daily_df.copy()
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    d = d.dropna(subset=["Data"])
    today = today_brt()
    start = start_of_week(today)
    d = d[d["Data"].dt.date.between(start, today)]
    vals = pd.to_numeric(d["Stress (média)"], errors="coerce").dropna()
    return float(vals.mean()) if not vals.empty else None

def breathwork_today_and_7d(daily_df: pd.DataFrame) -> Tuple[int, int]:
    """Retorna (hoje_em_minutos, media_7d) — usa coluna 'Breathwork (min)'."""
    if "Breathwork (min)" not in daily_df.columns or "Data" not in daily_df.columns:
        return (0, 0)
    d = daily_df.copy()
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    d = d.dropna(subset=["Data"]).sort_values("Data")
    today = today_brt()
    today_row = d[d["Data"].dt.date == today]
    today_min = int(round(float(today_row["Breathwork (min)"].iloc[-1]))) if not today_row.empty and pd.notna(today_row["Breathwork (min)"].iloc[-1]) else 0
    d7 = d[d["Data"].dt.date.between(today - dt.timedelta(days=6), today)]
    avg7 = int(round(pd.to_numeric(d7["Breathwork (min)"], errors="coerce").fillna(0).mean())) if not d7.empty else 0
    return today_min, avg7

def breathwork_streak_days(daily_df: pd.DataFrame) -> int:
    """Conta dias consecutivos com 'Breathwork (min)' > 0 a partir do dia mais recente."""
    if "Breathwork (min)" not in daily_df.columns or "Data" not in daily_df.columns:
        return 0
    d = daily_df.copy()
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    d = d.dropna(subset=["Data"]).sort_values("Data")
    streak, last_date = 0, None
    for _, row in d[::-1].iterrows():  # começa do mais recente
        val = row.get("Breathwork (min)")
        if pd.isna(val) or float(val) <= 0:
            if last_date is None:
                continue
            else:
                break
        current_date = row["Data"].date()
        if last_date is None:
            streak = 1
        else:
            if (last_date - current_date).days == 1:
                streak += 1
            else:
                break
        last_date = current_date
    return streak

def sleep_period_avg(daily_df: pd.DataFrame, col: str, period: str) -> Optional[float]:
    """Média de sono (h) para períodos WTD/MTD/QTD/YTD/7D/TOTAL."""
    if "Data" not in daily_df.columns or col not in daily_df.columns:
        return None
    d = daily_df.copy()
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=["Data"])
    today = today_brt()
    if period == "7D":
        start = today - dt.timedelta(days=6)
    elif period == "WTD":
        start = start_of_week(today)
    elif period == "MTD":
        start = start_of_month(today)
    elif period == "QTD":
        start = start_of_quarter(today)
    elif period == "YTD":
        start = start_of_year(today)
    else:  # TOTAL
        start = d["Data"].min().date()
    vals = d.loc[d["Data"].dt.date.between(start, today), col].dropna()
    return float(vals.mean()) if not vals.empty else None

# ---------- Corrida (somente dias com corrida contam) ----------
def running_daily_agg(acts_df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por dia apenas atividades 'running' e calcula pace diário."""
    if acts_df.empty:
        return pd.DataFrame(columns=["Data","km","dur_min","pace_num","fc_mean","vo2_mean"])
    df = acts_df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df = df[df["Tipo"].str.lower() == "running"]
    if df.empty:
        return pd.DataFrame(columns=["Data","km","dur_min","pace_num","fc_mean","vo2_mean"])
    df["km"] = pd.to_numeric(df["Distância (km)"], errors="coerce")
    df["dur_min"] = pd.to_numeric(df["Duração (min)"], errors="coerce")
    grp = df.groupby(df["Data"].dt.normalize(), as_index=False).agg(
        km=("km","sum"),
        dur_min=("dur_min","sum"),
        fc_mean=("FC Média","mean"),
        vo2_mean=("VO2 Máx","mean")
    )
    grp["pace_num"] = grp.apply(lambda r: (r["dur_min"]/r["km"]) if (r["km"] and r["km"]>0) else float("nan"), axis=1)
    grp.rename(columns={"Data":"DataDay"}, inplace=True)
    return grp

def running_last_session(acts_df: pd.DataFrame) -> Dict:
    if acts_df.empty:
        return {"date":"-","km":"-","pace":"-","fc":"-","vo2":"-"}
    run = acts_df.copy()
    run["Data"] = pd.to_datetime(run["Data"], errors="coerce")
    run = run.dropna(subset=["Data"])
    run = run[run["Tipo"].str.lower() == "running"]
    if run.empty:
        return {"date":"-","km":"-","pace":"-","fc":"-","vo2":"-"}
    last = run.sort_values("Data").iloc[-1]
    km = last.get("Distância (km)")
    pace = last.get("Pace (min/km)")
    fc = last.get("FC Média")
    vo2 = last.get("VO2 Máx")
    # pace pode vir como float (minutos) ou string "m:ss"
    try:
        if isinstance(pace, (int,float)):
            pace_s = minutes_to_mmss(float(pace))
        else:
            s = str(pace).strip()
            if s and s != "nan":
                pace_s = s
            else:
                pace_s = "-"
    except Exception:
        pace_s = "-"
    return {
        "date": last["Data"].date().isoformat(),
        "km": num_fmt(km, 2) if pd.notna(km) else "-",
        "pace": pace_s,
        "fc": num_fmt(fc, 0) if pd.notna(fc) else "-",
        "vo2": num_fmt(vo2, 0) if pd.notna(vo2) else "-"
    }

def running_period_avg_pace(agg_run: pd.DataFrame, period: str) -> Optional[float]:
    if agg_run.empty:
        return None
    today = today_brt()
    if period == "7D":
        start = today - dt.timedelta(days=6)
    elif period == "SEM":  # semana atual
        start = start_of_week(today)
    elif period == "MES":
        start = start_of_month(today)
    elif period == "TRIM":
        start = start_of_quarter(today)
    elif period == "ANO":
        start = start_of_year(today)
    else:
        return None
    df = agg_run.copy()
    df["DataDay"] = pd.to_datetime(df["DataDay"])
    mask = df["DataDay"].dt.date.between(start, today)
    vals = pd.to_numeric(df.loc[mask, "pace_num"], errors="coerce").dropna()
    return float(vals.mean()) if not vals.empty else None

def running_last_vo2(agg_run: pd.DataFrame) -> Optional[float]:
    if agg_run.empty:
        return None
    df = agg_run.dropna(subset=["vo2_mean"]).sort_values("DataDay")
    if df.empty:
        return None
    return float(df.iloc[-1]["vo2_mean"])

# ---------- Insights Table ----------
def build_insights_table_md(daily_df: pd.DataFrame) -> str:
    """Gera a tabela Markdown (WTD/MTD/QTD/YTD/TOTAL) com as métricas do exemplo."""
    d = daily_df.copy()
    if "Data" not in d.columns:
        return "_Sem dados_"
    d["Data"] = pd.to_datetime(d["Data"], errors="coerce")
    d = d.dropna(subset=["Data"])
    # Tranformações auxiliares
    if "Pace (min/km)" in d.columns and "PaceNum" not in d.columns:
        d["PaceNum"] = pd.to_numeric(d["Pace (min/km)"], errors="coerce")
    if "Sono (h)" in d.columns and "SonoHorasNum" not in d.columns:
        d["SonoHorasNum"] = pd.to_numeric(d["Sono (h)"], errors="coerce")

    items = [
        ("Sono (h) — Média",          "SonoHorasNum", "mean", "time"),
        ("Sono Deep (h) — Média",     "Sono Deep (h)","mean", "time"),
        ("Sono REM (h) — Média",      "Sono REM (h)", "mean", "time"),
        ("Sono Light (h) — Média",    "Sono Light (h)","mean","time"),
        ("Qualidade do sono (score)", "Sono (score)", "mean", "num"),
        ("Distância corrida (km) — Soma","Corrida (km)","sum","num"),
        ("Distância corrida (km) — Média","Corrida (km)","mean","num"),
        ("Pace médio (min/km)",       "PaceNum",      "mean","pace"),
        ("Passos — Média",            "Passos",       "mean","int"),
        ("Calorias (total dia) — Média","Calorias (total dia)","mean","num"),
        ("Body Battery (máx)",        "Body Battery (máx)","mean","num"),
        ("Stress médio",              "Stress (média)","mean","num"),
        ("Breathwork (min) — Média",  "Breathwork (min)","mean","int"),
    ]
    periods = [("WTD","WTD"), ("MTD","MTD"), ("QTD","QTD"), ("YTD","YTD"), ("TOTAL","TOTAL")]

    def _period_mask(df, pcode):
        t = today_brt()
        if pcode == "WTD":
            start = start_of_week(t)
        elif pcode == "MTD":
            start = start_of_month(t)
        elif pcode == "QTD":
            start = start_of_quarter(t)
        elif pcode == "YTD":
            start = start_of_year(t)
        else:
            start = df["Data"].min().date()
        return df["Data"].dt.date.between(start, t)

    # Computa valores e formata
    rows = []
    for name, col, mode, fmt in items:
        if col not in d.columns:
            rows.append([name] + ["-"]*len(periods))
            continue
        line = [name]
        for _, p in periods:
            sub = d.loc[_period_mask(d, p), col]
            vals = pd.to_numeric(sub, errors="coerce").dropna()
            if vals.empty:
                line.append("-")
                continue
            val = float(vals.sum() if mode=="sum" else vals.mean())
            if fmt == "time":
                line.append(hours_to_hhmm(val))
            elif fmt == "pace":
                line.append(minutes_to_mmss(val))
            elif fmt == "int":
                line.append(int_fmt(val))
            else:
                line.append(num_fmt(val, 2))
        rows.append(line)

    # Monta markdown
    header = "| Métrica | WTD | MTD | QTD | YTD | TOTAL |\n|---|---:|---:|---:|---:|---:|"
    body = "\n".join([f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows])
    return header + "\n" + body
