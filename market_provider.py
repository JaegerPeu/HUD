# market_provider.py
# Coleta cotações (Yahoo Finance), calcula retornos por período, correlatos e busca notícias (RSS).
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import datetime as dt
import pandas as pd
import yfinance as yf
import feedparser
from dateutil import parser as dtparser
from zoneinfo import ZoneInfo

# ------------------------
# Helpers de data/tempo
# ------------------------
BRT = ZoneInfo("America/Sao_Paulo")

def today_brt() -> dt.date:
    return dt.datetime.now(BRT).date()

def start_of_week(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())

def start_of_month(d: dt.date) -> dt.date:
    return d.replace(day=1)

def start_of_quarter(d: dt.date) -> dt.date:
    q = (d.month - 1)//3 + 1
    return dt.date(d.year, 3*(q-1)+1, 1)

def start_of_year(d: dt.date) -> dt.date:
    return dt.date(d.year, 1, 1)

def fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "-"
    try:
        return f"{x*100:+.2f}%"
    except Exception:
        return "-"

def fmt_num(x: Optional[float], nd=2) -> str:
    if x is None:
        return "-"
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return "-"

# ------------------------
# Yahoo Finance
# ------------------------
def _download_prices(tickers: List[str], lookback_days: int = 550) -> pd.DataFrame:
    """Baixa dados diários (Close) dos tickers; retorna df com MultiIndex columns (ticker -> field)."""
    start = today_brt() - dt.timedelta(days=lookback_days)
    df = yf.download(
        tickers=tickers, start=start.isoformat(),
        interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True
    )
    # normaliza para DataFrame com linhas=dates e colunas simples por ticker (Close)
    if isinstance(df.columns, pd.MultiIndex):
        close_cols = []
        out = pd.DataFrame(index=df.index)
        for t in tickers:
            if (t, "Close") in df.columns:
                out[t] = pd.to_numeric(df[(t, "Close")], errors="coerce")
                close_cols.append(t)
        return out
    else:
        # quando só um ticker
        s = pd.to_numeric(df["Close"], errors="coerce")
        return pd.DataFrame({tickers[0]: s})
        
def _first_value_on_or_after(series: pd.Series, d: dt.date) -> Optional[float]:
    try:
        s = series.dropna()
        s = s[s.index.date >= d]
        if s.empty:
            return None
        return float(s.iloc[0])
    except Exception:
        return None

def _last_two(series: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    s = series.dropna()
    if len(s) < 2:
        if len(s) == 1:
            return float(s.iloc[-1]), None
        return None, None
    return float(s.iloc[-1]), float(s.iloc[-2])

def _return_from_start_to_last(series: pd.Series, start_date: dt.date) -> Optional[float]:
    v0 = _first_value_on_or_after(series, start_date)
    v1 = series.dropna().iloc[-1] if not series.dropna().empty else None
    if v0 is None or v1 is None or v0 == 0:
        return None
    return float(v1 / v0 - 1.0)

def _d1_return(series: pd.Series) -> Optional[float]:
    last_, prev_ = _last_two(series)
    if last_ is None or prev_ is None or prev_ == 0:
        return None
    return float(last_ / prev_ - 1.0)

# ------------------------
# Retornos por período
# ------------------------
def compute_period_returns(series: pd.Series) -> Dict[str, Optional[float]]:
    """Retorna dict {D1,WTD,MTD,QTD,YTD,12M} como frações (0.0123=1.23%)."""
    t = today_brt()
    out = {
        "D1": _d1_return(series),
        "WTD": _return_from_start_to_last(series, start_of_week(t)),
        "MTD": _return_from_start_to_last(series, start_of_month(t)),
        "QTD": _return_from_start_to_last(series, start_of_quarter(t)),
        "YTD": _return_from_start_to_last(series, start_of_year(t)),
        "12M": _return_from_start_to_last(series, t - dt.timedelta(days=365)),
    }
    return out

# ------------------------
# Mercado – interface pública
# ------------------------
class MarketData:
    def __init__(self, win_ticker: Optional[str] = None, wdo_ticker: Optional[str] = None):
        # Tickers padrão (Yahoo)
        self.tickers = {
            "SPX": "^GSPC",
            "IBOV": "^BVSP",
            "VIX": "^VIX",
            "US10Y": "^TNX",      # dividir por 10 para % real
            "DXY": "DX-Y.NYB",    # fallback ^DXY
            "USDBRL": "BRL=X",
            "BRENT": "BZ=F",
            "GOLD": "GC=F",
        }
        # Tickers opcionais (WIN/WDO) – se você tiver um mapeamento
        if win_ticker:
            self.tickers["WIN"] = win_ticker  # >>> MANUAL INPUT se usar provider alternativo
        if wdo_ticker:
            self.tickers["WDO"] = wdo_ticker

        # Carrega preços
        self._prices = _download_prices(list(self.tickers.values()))

        # Se DXY não veio, tenta fallback
        if "DX-Y.NYB" in self._prices.columns and self._prices["DX-Y.NYB"].dropna().empty:
            alt = _download_prices(["^DXY"])
            if not alt.empty:
                self._prices["DX-Y.NYB"] = alt["^DXY"]

    def last_level(self, key: str) -> Optional[float]:
        """Último preço/nível."""
        t = self.tickers.get(key)
        if not t or t not in self._prices.columns:
            return None
        s = self._prices[t].dropna()
        if s.empty:
            return None
        v = float(s.iloc[-1])
        # Ajustes
        if key == "US10Y":
            return v / 10.0  # ^TNX é em deci-pontos
        return v

    def returns(self, key: str) -> Dict[str, Optional[float]]:
        t = self.tickers.get(key)
        if not t or t not in self._prices.columns:
            return {"D1": None, "WTD": None, "MTD": None, "QTD": None, "YTD": None, "12M": None}
        return compute_period_returns(self._prices[t])

# ------------------------
# Notícias (RSS)
# ------------------------
RSS_SOURCES = [
    ("InfoMoney", "https://www.infomoney.com.br/feed/"),
    ("Investing Brasil", "https://br.investing.com/rss/news.rss"),
    # Bloomberg Línea - feed global; pode vir em ES/EN:
    ("Bloomberg Línea", "https://www.bloomberglinea.com/feeds/latest/"),
]

def fetch_latest_news(max_items: int = 6) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for source_name, url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()
                # published_parsed ou updated_parsed
                pub = (
                    e.get("published") or e.get("updated") or
                    e.get("published_parsed") or e.get("updated_parsed")
                )
                try:
                    if isinstance(pub, str):
                        dt_obj = dtparser.parse(pub)
                    else:
                        dt_obj = dt.datetime(*pub[:6])  # time.struct_time
                    dt_brt = dt_obj.astimezone(BRT)
                    iso_brt = dt_brt.strftime("%Y-%m-%d %H:%M BRT")
                except Exception:
                    iso_brt = ""
                if title and link:
                    items.append({
                        "source": source_name,
                        "title": title,
                        "url": link,
                        "date_brt": iso_brt,
                    })
        except Exception:
            continue
    # Ordena por data decrescente (quando possível)
    def _key(x):
        try:
            return dt.datetime.strptime(x["date_brt"].replace(" BRT",""), "%Y-%m-%d %H:%M")
        except Exception:
            return dt.datetime(1970,1,1)
    items.sort(key=_key, reverse=True)
    return items[:max_items]

# ------------------------
# Agenda Macro (opcional)
# ------------------------
def fetch_macro_agenda_tradingeconomics(api_key: Optional[str]) -> Tuple[str, str]:
    """
    Busca eventos para hoje no TradingEconomics (Brasil/EUA) se houver api_key.
    Retorna (lista_brasil_md, lista_usa_md) como string pronta.
    Obs.: você pode usar 'guest:guest' mas é limitado.
    """
    if not api_key:
        return "", ""

    import requests
    base = "https://api.tradingeconomics.com/calendar"
    d = today_brt().isoformat()
    params = {
        "d1": d, "d2": d,
        "c": "brazil,united states",
        "format": "json",
        "client": api_key
    }
    try:
        r = requests.get(base, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return "", ""

    br_items, us_items = [], []
    for ev in data:
        country = (ev.get("Country") or "").lower()
        time_utc = ev.get("DateUtc") or ev.get("Date")
        title = ev.get("Event") or ev.get("Category") or "Evento"
        actual = ev.get("Actual")
        forecast = ev.get("Forecast")
        previous = ev.get("Previous")
        # horário para BRT
        try:
            dt_utc = dtparser.parse(time_utc)
            dt_local = dt_utc.astimezone(BRT)
            hhmm = dt_local.strftime("%H:%M")
        except Exception:
            hhmm = "--:--"
        txt = f"- {hhmm} — {title}"
        det = []
        if actual: det.append(f"Real: {actual}")
        if forecast: det.append(f"Cons.: {forecast}")
        if previous: det.append(f"Ant.: {previous}")
        if det:
            txt += " (" + " • ".join(det) + ")"
        if "brazil" in country:
            br_items.append(txt)
        elif "united states" in country:
            us_items.append(txt)

    return ("\n".join(br_items), "\n".join(us_items))
