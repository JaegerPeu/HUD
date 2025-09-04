# app.py — HUD AI v2 (Streamlit UI)
from __future__ import annotations
import streamlit as st
import pandas as pd
import datetime as dt
from zoneinfo import ZoneInfo

from settings import load_settings
from gsheets_io import get_client, load_sheet
from turtle import get_today_turtle_objective
from template_md import TEMPLATE
from renderer import render_template
from notion_client import push_code_block
from market_provider import MarketData, fetch_latest_news, fetch_macro_agenda_tradingeconomics
from metrics import (
    energy_pct_from_row, energy_bar_10, stress_wtd_mean,
    breathwork_today_and_7d, breathwork_streak_days,
    sleep_period_avg, running_daily_agg, running_last_session,
    running_period_avg_pace, running_last_vo2, build_insights_table_md,
    minutes_to_mmss, hours_to_hhmm, int_fmt, num_fmt, today_brt
)

# >>> MANUAL INPUT (opcional): habilitar blocos extras de debug/tabelas
SHOW_DATAFRAMES = False

st.set_page_config(page_title="HUD AI v2", layout="wide")
st.title("🎮 HUD AI v2 — Streamlit")

# ---------- Carrega configs/clients ----------
try:
    cfg = load_settings()
    client = get_client(cfg.gcp_sa_info, cfg.gcp_sa_file)
except Exception as e:
    st.error(f"Config/credenciais ausentes: {e}")
    st.stop()

# ---------- Sidebar ----------
st.sidebar.header("Configurações")
push_to_notion = st.sidebar.checkbox(
    "Enviar ao Notion ao gerar",
    value=bool(cfg.notion_token and cfg.notion_block_id),
    help="Precisa de notion.token e notion.block_id em st.secrets."
)
st.sidebar.write("**Planilha**:", cfg.gsheet_id or "—")
if cfg.notion_block_id:
    st.sidebar.write("**Notion Block ID**:", cfg.notion_block_id)

# ---------- Carrega Sheets ----------
@st.cache_data(ttl=60)
def load_dataframes(_client, _gsheet_id):
    daily = load_sheet(_client, _gsheet_id, "DailyHUD")
    acts = load_sheet(_client, _gsheet_id, "Activities")
    return daily, acts

daily, acts = load_dataframes(client, cfg.gsheet_id)

if daily.empty:
    st.warning("Aba `DailyHUD` vazia. Gere/atualize a planilha primeiro.")
    st.stop()

# Conversões
daily["Data"] = pd.to_datetime(daily["Data"], errors="coerce")
for c in [
    "Sono (h)","Sono Deep (h)","Sono REM (h)","Sono Light (h)","Sono (score)",
    "Body Battery (start)","Body Battery (end)","Body Battery (mín)","Body Battery (máx)",
    "Stress (média)","Passos","Calorias (total dia)","Corrida (km)","Pace (min/km)","Breathwork (min)"
]:
    if c in daily.columns:
        daily[c] = pd.to_numeric(daily[c], errors="coerce")

if not acts.empty:
    acts["Data"] = pd.to_datetime(acts["Data"], errors="coerce")

# ---------- Datas ----------
tz = ZoneInfo("America/Sao_Paulo")
now = dt.datetime.now(tz)
DIA_SEMANA_PT = now.strftime("%A").capitalize()
meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
DATA_EXTENSO = f"{now.day} de {meses[now.month-1]} de {now.year}"
HORA_LOCAL_BRT = now.strftime("%H:%M") + " BRT"

# ---------- Status fisiológico ----------
last_row = daily.dropna(subset=["Data"]).sort_values("Data").iloc[-1]
ENERGY_PCT = energy_pct_from_row(last_row)
ENERGY_BAR_10 = energy_bar_10(ENERGY_PCT)
SONO_HORAS = num_fmt(last_row.get("Sono (h)"), 1)
SONO_SCORE = num_fmt(last_row.get("Sono (score)"), 0)

yesterday_date = (today_brt() - dt.timedelta(days=1))
d_ontem = daily.loc[daily["Data"].dt.date == yesterday_date]
row_y = d_ontem.iloc[-1] if not d_ontem.empty else last_row
KCAL_DIA_ONTEM = int_fmt(row_y.get("Calorias (total dia)"))
PASSOS_ONTEM = int_fmt(row_y.get("Passos"))
STRESS_SCORE = num_fmt(stress_wtd_mean(daily), 2)

# ---------- Mente ----------
bw_today, bw_7d = breathwork_today_and_7d(daily)
MEDIT_MIN = str(bw_7d)     # média 7d
MEDIT_STREAK = str(breathwork_streak_days(daily))
SONO_7D_H  = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","7D"))
SONO_MTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","MTD"))
SONO_QTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","QTD"))
SONO_YTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","YTD"))

# ---------- Turtle / Trabalho ----------
TURTLE_OBJETIVO_TEXTO = get_today_turtle_objective(load_sheet, client, cfg.gsheet_id)

# ---------- Corrida ----------
agg_run = running_daily_agg(acts) if not acts.empty else pd.DataFrame()
last_run = running_last_session(acts) if not acts.empty else {"date":"-","km":"-","pace":"-","fc":"-","vo2":"-"}
RUN_DATA = last_run["date"]
RUN_DIST = last_run["km"]
RUN_PACE = last_run["pace"]
RUN_FC_MEDIA = last_run["fc"]
VO2MAX = num_fmt(running_last_vo2(agg_run), 0) if not agg_run.empty else "-"

PACE_7D  = minutes_to_mmss(running_period_avg_pace(agg_run, "7D"))   if not agg_run.empty else "-"
PACE_SEM = minutes_to_mmss(running_period_avg_pace(agg_run, "SEM"))  if not agg_run.empty else "-"
PACE_MES = minutes_to_mmss(running_period_avg_pace(agg_run, "MES"))  if not agg_run.empty else "-"
PACE_TRIM= minutes_to_mmss(running_period_avg_pace(agg_run, "TRIM")) if not agg_run.empty else "-"
PACE_ANO = minutes_to_mmss(running_period_avg_pace(agg_run, "ANO"))  if not agg_run.empty else "-"

# ---------- Mercado / Notícias / Agenda ----------
md = MarketData(win_ticker=cfg.win_ticker, wdo_ticker=cfg.wdo_ticker)

def fmt_pct(x):
    return f"{x*100:+.2f}%" if x is not None else "-"

def fmt_lvl(x, nd=2, suffix=""):
    return f"{x:.{nd}f}{suffix}" if x is not None else "-"

def rets(key):
    r = md.returns(key)
    return {k: fmt_pct(v) for k, v in r.items()}

SPX = rets("SPX")
IBOV = rets("IBOV")
WIN = rets("WIN") if cfg.win_ticker else {k:"-" for k in ("D1","WTD","MTD","QTD","YTD","12M")}
WDO = rets("WDO") if cfg.wdo_ticker else {k:"-" for k in ("D1","WTD","MTD","QTD","YTD","12M")}

VIX_lvl   = fmt_lvl(md.last_level("VIX"))
US10Y_lvl = fmt_lvl(md.last_level("US10Y"), 2, "%")
DXY_lvl   = fmt_lvl(md.last_level("DXY"))
USDBRL_lvl= fmt_lvl(md.last_level("USDBRL"), 4)
BRENT_lvl = fmt_lvl(md.last_level("BRENT"))
GOLD_lvl  = fmt_lvl(md.last_level("GOLD"))

VIX = rets("VIX"); US10Y = rets("US10Y"); DXY = rets("DXY")
USDBRL = rets("USDBRL"); BRENT = rets("BRENT"); GOLD = rets("GOLD")

news = fetch_latest_news(max_items=6)
BR_EVENTOS, US_EVENTOS = fetch_macro_agenda_tradingeconomics(cfg.te_api_key)

# ---------- Insights ----------
INSIGHTS_TABLE_MD = build_insights_table_md(daily)

# ---------- Estudos / Links (manuais por enquanto) ----------
CGA_STATUS = cfg.cga_status
ESTUDO_MIN_HOJE = cfg.estudo_min_hoje
LIVRO_TITULO = cfg.livro_titulo
LIVRO_PAG_ATUAL = cfg.livro_pag_atual
LIVRO_PAG_TOTAL = cfg.livro_pag_total
LIVRO_PROGRESSO = cfg.livro_progresso

LOSS_MAX_R = cfg.loss_max_r
PAUSE_TRIGGER_REGRA = cfg.pause_trigger_regra
LAZER_STREAK = cfg.lazer_streak
LINK_GARMIN = cfg.link_garmin
LINK_NOTION = cfg.link_notion
LINK_FUNDSCREENER = cfg.link_fundscreener
LINK_SWM = cfg.link_swm

# ---------- Mapping ----------
mapping = {
    "DATA_EXTENSO": DATA_EXTENSO, "DIA_SEMANA_PT": DIA_SEMANA_PT, "HORA_LOCAL_BRT": HORA_LOCAL_BRT,
    "ENERGY_BAR_10": ENERGY_BAR_10, "ENERGY_PCT": (str(ENERGY_PCT) if ENERGY_PCT is not None else "-"),
    "SONO_HORAS": SONO_HORAS, "SONO_SCORE": SONO_SCORE,
    "KCAL_DIA_ONTEM": KCAL_DIA_ONTEM, "PASSOS_ONTEM": PASSOS_ONTEM, "STRESS_SCORE": STRESS_SCORE,
    "MEDIT_MIN": MEDIT_MIN, "MEDIT_STREAK": MEDIT_STREAK,
    "SONO_7D_H": SONO_7D_H, "SONO_MTD_H": SONO_MTD_H, "SONO_QTD_H": SONO_QTD_H, "SONO_YTD_H": SONO_YTD_H,
    "CGA_STATUS": CGA_STATUS, "ESTUDO_MIN_HOJE": ESTUDO_MIN_HOJE,
    "LIVRO_TITULO": LIVRO_TITULO, "LIVRO_PAG_ATUAL": LIVRO_PAG_ATUAL, "LIVRO_PAG_TOTAL": LIVRO_PAG_TOTAL, "LIVRO_PROGRESSO": LIVRO_PROGRESSO,
    "TURTLE_OBJETIVO_TEXTO": TURTLE_OBJETIVO_TEXTO,
    "LOSS_MAX_R": LOSS_MAX_R, "PAUSE_TRIGGER_REGRA": PAUSE_TRIGGER_REGRA,
    "RUN_DATA": RUN_DATA, "RUN_DIST": RUN_DIST, "RUN_PACE": RUN_PACE, "RUN_FC_MEDIA": RUN_FC_MEDIA,
    "PACE_7D": PACE_7D, "PACE_SEM": PACE_SEM, "PACE_MES": PACE_MES, "PACE_TRIM": PACE_TRIM, "PACE_ANO": PACE_ANO,
    "VO2MAX": VO2MAX, "LAZER_STREAK": LAZER_STREAK,
    "INSIGHTS_TABLE_MD": INSIGHTS_TABLE_MD,
    "LINK_GARMIN": LINK_GARMIN, "LINK_NOTION": LINK_NOTION, "LINK_FUNDSCREENER": LINK_FUNDSCREENER, "LINK_SWM": LINK_SWM,
    # Mercado – retornos
    "SPX_D1": SPX["D1"], "SPX_WTD": SPX["WTD"], "SPX_MTD": SPX["MTD"], "SPX_QTD": SPX["QTD"], "SPX_YTD": SPX["YTD"], "SPX_12M": SPX["12M"],
    "IBOV_D1": IBOV["D1"], "IBOV_WTD": IBOV["WTD"], "IBOV_MTD": IBOV["MTD"], "IBOV_QTD": IBOV["QTD"], "IBOV_YTD": IBOV["YTD"], "IBOV_12M": IBOV["12M"],
    "WIN_D1": WIN["D1"], "WIN_WTD": WIN["WTD"], "WIN_MTD": WIN["MTD"], "WIN_QTD": WIN["QTD"], "WIN_YTD": WIN["YTD"], "WIN_12M": WIN["12M"],
    "WDO_D1": WDO["D1"], "WDO_WTD": WDO["WTD"], "WDO_MTD": WDO["MTD"], "WDO_QTD": WDO["QTD"], "WDO_YTD": WDO["YTD"], "WDO_12M": WDO["12M"],
    # Correlatos – níveis e retornos
    "VIX_NIVEL": VIX_lvl, "VIX_D1": VIX["D1"], "VIX_WTD": VIX["WTD"], "VIX_MTD": VIX["MTD"],
    "US10Y_NIVEL": US10Y_lvl, "US10Y_D1": US10Y["D1"], "US10Y_WTD": US10Y["WTD"], "US10Y_MTD": US10Y["MTD"],
    "DXY_NIVEL": DXY_lvl, "DXY_D1": DXY["D1"], "DXY_WTD": DXY["WTD"], "DXY_MTD": DXY["MTD"],
    "USDBRL_NIVEL": USDBRL_lvl, "USDBRL_D1": USDBRL["D1"], "USDBRL_WTD": USDBRL["WTD"], "USDBRL_MTD": USDBRL["MTD"],
    "BRENT_NIVEL": BRENT_lvl, "BRENT_D1": BRENT["D1"], "BRENT_WTD": BRENT["WTD"], "BRENT_MTD": BRENT["MTD"],
    "GOLD_NIVEL": GOLD_lvl, "GOLD_D1": GOLD["D1"], "GOLD_WTD": GOLD["WTD"], "GOLD_MTD": GOLD["MTD"],
    # Agenda Macro
    "BR_EVENTOS_HOJE_LIST": BR_EVENTOS or "",
    "US_EVENTOS_HOJE_LIST": US_EVENTOS or "",
    "ALERTAS_MERCADO_TXT": "",
}

# Notícias → NEWS1..6
for i in range(6):
    src = news[i] if i < len(news) else {"source":"","title":"","date_brt":"","url":""}
    mapping[f"NEWS{i+1}_SOURCE"] = src.get("source","")
    mapping[f"NEWS{i+1}_TITULO"] = src.get("title","")
    mapping[f"NEWS{i+1}_DATAISO_BRT"] = src.get("date_brt","")
    mapping[f"NEWS{i+1}_URL"] = src.get("url","")

# ---------- Render HUD ----------
hud_md = render_template(TEMPLATE, mapping)

# UI: coluna grande HUD + coluna lateral com ações
col_main, col_side = st.columns([4, 1])
with col_main:
    st.markdown(hud_md)

with col_side:
    st.download_button("⬇️ Baixar Markdown", data=hud_md, file_name="hud_output.md")
    if push_to_notion:
        if cfg.notion_token and cfg.notion_block_id:
            if st.button("🚀 Enviar ao Notion"):
                ok, msg = push_code_block(cfg.notion_block_id, hud_md, cfg.notion_token)
                st.success("Enviado ao Notion!") if ok else st.error(f"Falhou: {msg}")
        else:
            st.info("Configure `notion.token` e `notion.block_id` em st.secrets.")

# ---------- Extras (opcionais) ----------
with st.expander("📰 Notícias (lista)"):
    for i, n in enumerate(news, start=1):
        st.markdown(f"**{i}. [{n['source']}]** {n['title']}  —  _{n['date_brt']}_  \n{n['url']}")

with st.expander("📅 Agenda Macro (hoje)"):
    if mapping["BR_EVENTOS_HOJE_LIST"]:
        st.markdown("**Brasil**")
        st.markdown(mapping["BR_EVENTOS_HOJE_LIST"])
    if mapping["US_EVENTOS_HOJE_LIST"]:
        st.markdown("**EUA**")
        st.markdown(mapping["US_EVENTOS_HOJE_LIST"])

if SHOW_DATAFRAMES:
    with st.expander("📊 Retornos — Tabela (SPX/WIN/WDO/IBOV)"):
        df = pd.DataFrame({
            "Ativo": ["SPX","WIN","WDO","IBOV"],
            "D-1":[SPX["D1"],WIN["D1"],WDO["D1"],IBOV["D1"]],
            "WTD":[SPX["WTD"],WIN["WTD"],WDO["WTD"],IBOV["WTD"]],
            "MTD":[SPX["MTD"],WIN["MTD"],WDO["MTD"],IBOV["MTD"]],
            "QTD":[SPX["QTD"],WIN["QTD"],WDO["QTD"],IBOV["QTD"]],
            "YTD":[SPX["YTD"],WIN["YTD"],WDO["YTD"],IBOV["YTD"]],
            "12M":[SPX["12M"],WIN["12M"],WDO["12M"],IBOV["12M"]],
        })
        st.dataframe(df, use_container_width=True)

    with st.expander("🔗 Correlatos — Níveis/Retornos"):
        df2 = pd.DataFrame([
            ["VIX", VIX_lvl, VIX["D1"], VIX["WTD"], VIX["MTD"]],
            ["US10Y", US10Y_lvl, US10Y["D1"], US10Y["WTD"], US10Y["MTD"]],
            ["DXY", DXY_lvl, DXY["D1"], DXY["WTD"], DXY["MTD"]],
            ["USD/BRL", USDBRL_lvl, USDBRL["D1"], USDBRL["WTD"], USDBRL["MTD"]],
            ["Brent", BRENT_lvl, BRENT["D1"], BRENT["WTD"], BRENT["MTD"]],
            ["Ouro", GOLD_lvl, GOLD["D1"], GOLD["WTD"], GOLD["MTD"]],
        ], columns=["Indicador","Nível","D-1","WTD","MTD"])
        st.dataframe(df2, use_container_width=True)

st.caption(f"Atualizado em {now.strftime('%Y-%m-%d %H:%M BRT')}")
