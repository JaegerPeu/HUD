# template_md.py
# Template do HUD (Markdown). Sem dependências.
TEMPLATE = """
# 🎮 HUD AI — {{DATA_EXTENSO}} • {{DIA_SEMANA_PT}} • {{HORA_LOCAL_BRT}}

**Player:** Pedro Duarte  
**Objetivo Supremo:** Turtle Capital + Melhor Físico

## Status Fisiológico
- ⚡ **Energia (Body Battery):** {{ENERGY_BAR_10}} {{ENERGY_PCT}}%
- 😴 **Sono (última noite):** {{SONO_HORAS}}h • **Score:** {{SONO_SCORE}}/100
- 🔥 **Calorias (ontem):** {{KCAL_DIA_ONTEM}} kcal • 🚶 **Passos (ontem):** {{PASSOS_ONTEM}}
- 🧠 **Stress:** {{STRESS_SCORE}}/100

---

## 📰 Mercado — Últimas 6 notícias (com data)
[{{NEWS1_SOURCE}}] {{NEWS1_TITULO}} — **{{NEWS1_DATAISO_BRT}}** — {{NEWS1_URL}}

[{{NEWS2_SOURCE}}] {{NEWS2_TITULO}} — **{{NEWS2_DATAISO_BRT}}** — {{NEWS2_URL}}

[{{NEWS3_SOURCE}}] {{NEWS3_TITULO}} — **{{NEWS3_DATAISO_BRT}}** — {{NEWS3_URL}}

[{{NEWS4_SOURCE}}] {{NEWS4_TITULO}} — **{{NEWS4_DATAISO_BRT}}** — {{NEWS4_URL}}

[{{NEWS5_SOURCE}}] {{NEWS5_TITULO}} — **{{NEWS5_DATAISO_BRT}}** — {{NEWS5_URL}}

[{{NEWS6_SOURCE}}] {{NEWS6_TITULO}} — **{{NEWS6_DATAISO_BRT}}** — {{NEWS6_URL}}

> **Fontes alvo:** Investing.com, Bloomberg Línea, InfoMoney (sempre exibir a **data/hora em BRT** da matéria).

### 📈 Tabela de Retornos (%)
_Períodos: D-1 | WTD | MTD | QTD | YTD | 12M_

| Ativo | D-1 | WTD | MTD | QTD | YTD | 12M |
|---|---:|---:|---:|---:|---:|---:|
| **S&P 500 (SPX)** | {{SPX_D1}} | {{SPX_WTD}} | {{SPX_MTD}} | {{SPX_QTD}} | {{SPX_YTD}} | {{SPX_12M}} |
| **Mini Índice (WIN)** | {{WIN_D1}} | {{WIN_WTD}} | {{WIN_MTD}} | {{WIN_QTD}} | {{WIN_YTD}} | {{WIN_12M}} |
| **Mini Dólar (WDO)** | {{WDO_D1}} | {{WDO_WTD}} | {{WDO_MTD}} | {{WDO_QTD}} | {{WDO_YTD}} | {{WDO_12M}} |
| **Ibovespa (IBOV)** | {{IBOV_D1}} | {{IBOV_WTD}} | {{IBOV_MTD}} | {{IBOV_QTD}} | {{IBOV_YTD}} | {{IBOV_12M}} |

### 🔗 Correlatos que influenciam o WIN
| Indicador | Nível | D-1 | WTD | MTD | Observação |
|---|---:|---:|---:|---:|---|
| **VIX** | {{VIX_NIVEL}} | {{VIX_D1}} | {{VIX_WTD}} | {{VIX_MTD}} | Risco global |
| **US10Y** | {{US10Y_NIVEL}} | {{US10Y_D1}} | {{US10Y_WTD}} | {{US10Y_MTD}} | Juros EUA |
| **DXY** | {{DXY_NIVEL}} | {{DXY_D1}} | {{DXY_WTD}} | {{DXY_MTD}} | Dólar global |
| **USD/BRL** | {{USDBRL_NIVEL}} | {{USDBRL_D1}} | {{USDBRL_WTD}} | {{USDBRL_MTD}} | FX local |
| **Brent** | {{BRENT_NIVEL}} | {{BRENT_D1}} | {{BRENT_WTD}} | {{BRENT_MTD}} | Petróleo |
| **Ouro** | {{GOLD_NIVEL}} | {{GOLD_D1}} | {{GOLD_WTD}} | {{GOLD_MTD}} | Hedge |

### 📅 Agenda Macro (BRT)
- **Brasil:** {{BR_EVENTOS_HOJE_LIST}}  
- **EUA:** {{US_EVENTOS_HOJE_LIST}}

> **Alertas automáticos (a definir):** {{ALERTAS_MERCADO_TXT}}

---

## 🧠 M — Mente
- **Meditação (Breathwork):** {{MEDIT_MIN}} min (média 7d) • **Streak:** {{MEDIT_STREAK}} dias
- **Sono — KPIs:**  
  **7d:** {{SONO_7D_H}}h • **Mês:** {{SONO_MTD_H}}h • **Trim.:** {{SONO_QTD_H}}h • **Ano:** {{SONO_YTD_H}}h

## 📚 E — Estudos *(Notion DB em breve)*
- **Meta ativa:** CGA ({{CGA_STATUS}}) • **Hoje:** {{ESTUDO_MIN_HOJE}} min  
- **Livro atual:** {{LIVRO_TITULO}} — pág. {{LIVRO_PAG_ATUAL}}/{{LIVRO_PAG_TOTAL}} ({{LIVRO_PROGRESSO}}%)

## 💼 T — Trabalho/Finanças
- **Trade – “Turtle” de hoje:** {{TURTLE_OBJETIVO_TEXTO}}
- **Risco diário (LOSS máx):** {{LOSS_MAX_R}}  •  **Pause Trigger:** {{PAUSE_TRIGGER_REGRA}}

## 🏃 A — Atividade Física/Saúde
**Corrida (somente dias com treino contam na média):**
- **Última corrida:** {{RUN_DATA}} — {{RUN_DIST}} km — Pace: {{RUN_PACE}} min/km — FCm: {{RUN_FC_MEDIA}}  
- **Médias de Pace**: 7d {{PACE_7D}} • Semana {{PACE_SEM}} • Mês {{PACE_MES}} • Trim. {{PACE_TRIM}} • Ano {{PACE_ANO}}
- **VO2max (Garmin):** {{VO2MAX}}

## 🎯 L — Lazer / Vida
- **Streak de Lazer:** {{LAZER_STREAK}} dias

---

## 📊 Insights — WTD / MTD / QTD / YTD / TOTAL
{{INSIGHTS_TABLE_MD}}

---

## 🔗 Links Rápidos
Garmin: {{LINK_GARMIN}} • Notion Life OS: {{LINK_NOTION}} • Fund Screener: {{LINK_FUNDSCREENER}} • Dashboard SWM/MFO: {{LINK_SWM}}
"""
