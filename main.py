# main.py
from __future__ import annotations
import pandas as pd
from zoneinfo import ZoneInfo
import datetime as dt
from settings import load_settings
from gsheets_io import get_client, load_sheet
from turtle import get_today_turtle_objective
from metrics import (
    energy_pct_from_row, energy_bar_10,
    stress_wtd_mean, breathwork_today_and_7d, breathwork_streak_days,
    sleep_period_avg, running_daily_agg, running_last_session,
    running_period_avg_pace, running_last_vo2, build_insights_table_md,
    minutes_to_mmss, hours_to_hhmm, int_fmt, num_fmt, today_brt
)
from notion_client import push_code_block
from renderer import render_template
from template_md import TEMPLATE

# >>> MANUAL INPUT (opcional): se quiser desativar/envio ao Notion independente dos secrets:
PUSH_TO_NOTION_OVERRIDE = None  # use True/False para forçar; ou deixe None para decidir por secrets

def main():
    cfg = load_settings()
    client = get_client(cfg.gcp_sa_info, cfg.gcp_sa_file)

    # Carrega abas
    daily = load_sheet(client, cfg.gsheet_id, "DailyHUD")
    acts  = load_sheet(client, cfg.gsheet_id, "Activities")

    # Conversões
    if not daily.empty:
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

    # ========= Datas / Horário BRT =========
    tz = ZoneInfo("America/Sao_Paulo")
    now = dt.datetime.now(tz)
    DIA_SEMANA_PT = now.strftime("%A").capitalize()
    meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
    DATA_EXTENSO = f"{now.day} de {meses[now.month-1]} de {now.year}"
    HORA_LOCAL_BRT = now.strftime("%H:%M") + " BRT"

    # ========= Status fisiológico =========
    last_row = daily.dropna(subset=["Data"]).sort_values("Data").iloc[-1] if not daily.empty else pd.Series()
    ENERGY_PCT = energy_pct_from_row(last_row) if not daily.empty else None
    ENERGY_BAR_10 = energy_bar_10(ENERGY_PCT)
    SONO_HORAS = num_fmt(last_row.get("Sono (h)"), 1) if not daily.empty else "-"
    SONO_SCORE = num_fmt(last_row.get("Sono (score)"), 0) if not daily.empty else "-"
    # Ontem (tenta achar a data de ontem; se não houver, usa última disponível)
    yesterday_date = (today_brt() - dt.timedelta(days=1))
    d_ontem = daily.loc[daily["Data"].dt.date == yesterday_date] if not daily.empty else pd.DataFrame()
    if not d_ontem.empty:
        row_y = d_ontem.iloc[-1]
    else:
        row_y = last_row
    KCAL_DIA_ONTEM = int_fmt(row_y.get("Calorias (total dia)")) if not daily.empty else "-"
    PASSOS_ONTEM = int_fmt(row_y.get("Passos")) if not daily.empty else "-"
    STRESS_SCORE = num_fmt(stress_wtd_mean(daily), 2) if not daily.empty else "-"

    # ========= Mente (Breathwork/Sono) =========
    bw_today, bw_7d = breathwork_today_and_7d(daily) if not daily.empty else (0, 0)
    MEDIT_MIN = str(bw_7d)  # conforme pedido: exibimos a MÉDIA 7D
    MEDIT_STREAK = str(breathwork_streak_days(daily)) if not daily.empty else "0"

    SONO_7D_H  = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","7D"))  if not daily.empty else "-"
    SONO_MTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","MTD")) if not daily.empty else "-"
    SONO_QTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","QTD")) if not daily.empty else "-"
    SONO_YTD_H = hours_to_hhmm(sleep_period_avg(daily,"Sono (h)","YTD")) if not daily.empty else "-"

    # ========= Trabalho / Turtle =========
    TURTLE_OBJETIVO_TEXTO = get_today_turtle_objective(load_sheet, client, cfg.gsheet_id)

    # ========= Atividade Física (somente dias com corrida) =========
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

    # ========= Insights Table =========
    INSIGHTS_TABLE_MD = build_insights_table_md(daily) if not daily.empty else "_Sem dados_"

    # ========= Estudos (manual por enquanto) =========
    CGA_STATUS = cfg.cga_status
    ESTUDO_MIN_HOJE = cfg.estudo_min_hoje
    LIVRO_TITULO = cfg.livro_titulo
    LIVRO_PAG_ATUAL = cfg.livro_pag_atual
    LIVRO_PAG_TOTAL = cfg.livro_pag_total
    LIVRO_PROGRESSO = cfg.livro_progresso

    # ========= Links / manuais =========
    LOSS_MAX_R = cfg.loss_max_r
    PAUSE_TRIGGER_REGRA = cfg.pause_trigger_regra
    LAZER_STREAK = cfg.lazer_streak
    LINK_GARMIN = cfg.link_garmin
    LINK_NOTION = cfg.link_notion
    LINK_FUNDSCREENER = cfg.link_fundscreener
    LINK_SWM = cfg.link_swm

    # ========= News / Mercado placeholders (vão ficar vazios por agora) =========
    news_defaults = {
        "NEWS1_SOURCE":"", "NEWS1_TITULO":"", "NEWS1_DATAISO_BRT":"", "NEWS1_URL":"",
        "NEWS2_SOURCE":"", "NEWS2_TITULO":"", "NEWS2_DATAISO_BRT":"", "NEWS2_URL":"",
        "NEWS3_SOURCE":"", "NEWS3_TITULO":"", "NEWS3_DATAISO_BRT":"", "NEWS3_URL":"",
        "NEWS4_SOURCE":"", "NEWS4_TITULO":"", "NEWS4_DATAISO_BRT":"", "NEWS4_URL":"",
        "NEWS5_SOURCE":"", "NEWS5_TITULO":"", "NEWS5_DATAISO_BRT":"", "NEWS5_URL":"",
        "NEWS6_SOURCE":"", "NEWS6_TITULO":"", "NEWS6_DATAISO_BRT":"", "NEWS6_URL":"",
        "SPX_D1":"", "SPX_WTD":"", "SPX_MTD":"", "SPX_QTD":"", "SPX_YTD":"", "SPX_12M":"",
        "WIN_D1":"", "WIN_WTD":"", "WIN_MTD":"", "WIN_QTD":"", "WIN_YTD":"", "WIN_12M":"",
        "WDO_D1":"", "WDO_WTD":"", "WDO_MTD":"", "WDO_QTD":"", "WDO_YTD":"", "WDO_12M":"",
        "IBOV_D1":"", "IBOV_WTD":"", "IBOV_MTD":"", "IBOV_QTD":"", "IBOV_YTD":"", "IBOV_12M":"",
        "VIX_NIVEL":"", "VIX_D1":"", "VIX_WTD":"", "VIX_MTD":"",
        "US10Y_NIVEL":"", "US10Y_D1":"", "US10Y_WTD":"", "US10Y_MTD":"",
        "DXY_NIVEL":"", "DXY_D1":"", "DXY_WTD":"", "DXY_MTD":"",
        "USDBRL_NIVEL":"", "USDBRL_D1":"", "USDBRL_WTD":"", "USDBRL_MTD":"",
        "BRENT_NIVEL":"", "BRENT_D1":"", "BRENT_WTD":"", "BRENT_MTD":"",
        "GOLD_NIVEL":"", "GOLD_D1":"", "GOLD_WTD":"", "GOLD_MTD":"",
        "BR_EVENTOS_HOJE_LIST":"", "US_EVENTOS_HOJE_LIST":"", "ALERTAS_MERCADO_TXT":""
    }

    # ========= Monta mapping =========
    mapping = {
        "DATA_EXTENSO": DATA_EXTENSO,
        "DIA_SEMANA_PT": DIA_SEMANA_PT,
        "HORA_LOCAL_BRT": HORA_LOCAL_BRT,
        "ENERGY_BAR_10": ENERGY_BAR_10,
        "ENERGY_PCT": (str(ENERGY_PCT) if ENERGY_PCT is not None else "-"),
        "SONO_HORAS": SONO_HORAS,
        "SONO_SCORE": SONO_SCORE,
        "KCAL_DIA_ONTEM": KCAL_DIA_ONTEM,
        "PASSOS_ONTEM": PASSOS_ONTEM,
        "STRESS_SCORE": STRESS_SCORE,
        "MEDIT_MIN": MEDIT_MIN,
        "MEDIT_STREAK": MEDIT_STREAK,
        "SONO_7D_H": SONO_7D_H,
        "SONO_MTD_H": SONO_MTD_H,
        "SONO_QTD_H": SONO_QTD_H,
        "SONO_YTD_H": SONO_YTD_H,
        "CGA_STATUS": CGA_STATUS,
        "ESTUDO_MIN_HOJE": ESTUDO_MIN_HOJE,
        "LIVRO_TITULO": LIVRO_TITULO,
        "LIVRO_PAG_ATUAL": LIVRO_PAG_ATUAL,
        "LIVRO_PAG_TOTAL": LIVRO_PAG_TOTAL,
        "LIVRO_PROGRESSO": LIVRO_PROGRESSO,
        "TURTLE_OBJETIVO_TEXTO": TURTLE_OBJETIVO_TEXTO,
        "LOSS_MAX_R": LOSS_MAX_R,
        "PAUSE_TRIGGER_REGRA": PAUSE_TRIGGER_REGRA,
        "RUN_DATA": RUN_DATA,
        "RUN_DIST": RUN_DIST,
        "RUN_PACE": RUN_PACE,
        "RUN_FC_MEDIA": RUN_FC_MEDIA,
        "PACE_7D": PACE_7D,
        "PACE_SEM": PACE_SEM,
        "PACE_MES": PACE_MES,
        "PACE_TRIM": PACE_TRIM,
        "PACE_ANO": PACE_ANO,
        "VO2MAX": VO2MAX,
        "LAZER_STREAK": LAZER_STREAK,
        "INSIGHTS_TABLE_MD": INSIGHTS_TABLE_MD,
        "LINK_GARMIN": LINK_GARMIN,
        "LINK_NOTION": LINK_NOTION,
        "LINK_FUNDSCREENER": LINK_FUNDSCREENER,
        "LINK_SWM": LINK_SWM,
    }
    mapping.update(news_defaults)

    # ========= Renderiza =========
    hud_md = render_template(TEMPLATE, mapping)

    # Salva local
    with open("hud_output.md", "w", encoding="utf-8") as f:
        f.write(hud_md)

    # Opcional: envia ao Notion
    do_push = (PUSH_TO_NOTION_OVERRIDE
               if PUSH_TO_NOTION_OVERRIDE is not None
               else bool(cfg.notion_token and cfg.notion_block_id))
    if do_push:
        ok, msg = push_code_block(cfg.notion_block_id, hud_md, cfg.notion_token)
        print("Notion:", "OK" if ok else f"FAIL - {msg}")
    else:
        print("HUD gerado em hud_output.md (envio ao Notion desativado).")

if __name__ == "__main__":
    main()
