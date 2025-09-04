# settings.py
# Carrega configs a partir de st.secrets (se existir) ou variáveis de ambiente.
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import json

try:
    import streamlit as st  # permite ler secrets do Streamlit
    SECRETS = st.secrets
except Exception:
    SECRETS = None

@dataclass
class Settings:
    gsheet_id: str
    gcp_sa_info: Optional[Dict[str, Any]]  # dict do service account (st.secrets["gcp_service_account"])
    gcp_sa_file: Optional[str]             # caminho do .json (fallback se não houver dict)

    # Notion (opcional)
    notion_token: Optional[str]
    notion_block_id: Optional[str]

    # Manuais / links (placeholders sem automação agora)
    loss_max_r: str
    pause_trigger_regra: str
    lazer_streak: str
    link_garmin: str
    link_notion: str
    link_fundscreener: str
    link_swm: str

    # Estudos (manter manual por enquanto; futuro: Notion DB)
    cga_status: str
    estudo_min_hoje: str
    livro_titulo: str
    livro_pag_atual: str
    livro_pag_total: str
    livro_progresso: str


def _get_secret(path: str, default=None):
    """Busca em st.secrets usando 'a.b.c' como caminho. Se não achar, retorna default."""
    if not SECRETS:
        return default
    cur = SECRETS
    try:
        for k in path.split("."):
            cur = cur[k]
        return cur
    except Exception:
        return default

def load_settings() -> Settings:
    # --- Google Sheets ---
    gsheet_id = _get_secret("gsheet_id") or os.getenv("HUD_GSHEET_ID") or ""
    if not gsheet_id:
        # >>> MANUAL INPUT: Se você não usa st.secrets nem env, coloque o ID da planilha abaixo:
        # gsheet_id = "1rwcDJA1yZ2hbsJx-HOW0dCduvWqV0z7f9Iio0HI1WwY"
        pass
    if not gsheet_id:
        raise ValueError("Defina o ID da planilha (st.secrets['gsheet_id'] ou env HUD_GSHEET_ID).")

    gcp_sa_info = _get_secret("gcp_service_account")
    gcp_sa_file = os.getenv("GCP_SERVICE_ACCOUNT_FILE")

    # --- Notion ---
    notion_token = _get_secret("notion.token") or os.getenv("NOTION_TOKEN")
    notion_block_id = _get_secret("notion.block_id") or os.getenv("NOTION_BLOCK_ID")

    # --- Manuais / Links ---
    loss_max_r = _get_secret("manual.loss_max_r", "-") or "-"
    pause_trigger_regra = _get_secret("manual.pause_trigger_regra", "-") or "-"
    lazer_streak = _get_secret("manual.lazer_streak", "0") or "0"

    link_garmin = _get_secret("links.garmin", "-") or os.getenv("LINK_GARMIN", "-")
    link_notion = _get_secret("links.notion", "-") or os.getenv("LINK_NOTION", "-")
    link_fundscreener = _get_secret("links.fundscreener", "-") or os.getenv("LINK_FUNDSCREENER", "-")
    link_swm = _get_secret("links.swm", "-") or os.getenv("LINK_SWM", "-")

    # >>> MANUAL INPUT: Se quiser fixar valores manuais direto aqui, pode sobrescrever:
    # loss_max_r = "R$ 600"
    # pause_trigger_regra = "2 losses seguidos ou -R$ 600"
    # lazer_streak = "3"

    # Estudos (manter manual enquanto não integremos Notion DB)
    cga_status = _get_secret("estudos.cga_status", "-")
    estudo_min_hoje = _get_secret("estudos.estudo_min_hoje", "-")
    livro_titulo = _get_secret("estudos.livro_titulo", "-")
    livro_pag_atual = _get_secret("estudos.livro_pag_atual", "-")
    livro_pag_total = _get_secret("estudos.livro_pag_total", "-")
    livro_progresso = _get_secret("estudos.livro_progresso", "-")

    return Settings(
        gsheet_id=gsheet_id,
        gcp_sa_info=gcp_sa_info,
        gcp_sa_file=gcp_sa_file,
        notion_token=notion_token,
        notion_block_id=notion_block_id,
        loss_max_r=loss_max_r,
        pause_trigger_regra=pause_trigger_regra,
        lazer_streak=lazer_streak,
        link_garmin=link_garmin,
        link_notion=link_notion,
        link_fundscreener=link_fundscreener,
        link_swm=link_swm,
        cga_status=cga_status,
        estudo_min_hoje=estudo_min_hoje,
        livro_titulo=livro_titulo,
        livro_pag_atual=livro_pag_atual,
        livro_pag_total=livro_pag_total,
        livro_progresso=livro_progresso,
    )
