"""
game_dashboard.py
Página principal mejorada con Game Overview, últimos 5 partidos, H2H y estadísticas.
Integrado con el backend de NBA Betting Analyzer.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from dateutil import parser, tz
import time
import html
import re
from typing import Dict, List, Optional

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
BACKEND_URL = "http://localhost:8000"
PAGE_ICON_URL = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/1f3c0.png?v=1"
st.set_page_config(
    page_title="NBA Game Dashboard",
    page_icon=PAGE_ICON_URL,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados — Diseño NBA Premium (idéntico a interface.py)
DASHBOARD_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');

    /* ─── Variables de color NBA ─── */
    :root {
        --nba-red:      #C8102E;
        --nba-blue:     #1D428A;
        --nba-gold:     #F0B429;
        --nba-dark:     #0A0A0F;
        --nba-surface:  #12121A;
        --nba-card:     #1A1A26;
        --nba-border:   #2A2A3E;
        --nba-glow-red: rgba(200,16,46,0.35);
        --nba-glow-gold:rgba(240,180,41,0.3);
        --text-primary: #F5F5F0;
        --text-muted:   #8888AA;
    }

    /* ─── Reset global ─── */
    html, body, .stApp {
        background-color: var(--nba-dark) !important;
        color: var(--text-primary) !important;
        font-family: 'Barlow', sans-serif !important;
    }

    /* ─── Fondo con textura de cancha sutil ─── */
    .stApp {
        background-image:
            repeating-linear-gradient(
                0deg,
                transparent,
                transparent 59px,
                rgba(255,255,255,0.018) 59px,
                rgba(255,255,255,0.018) 60px
            ),
            repeating-linear-gradient(
                90deg,
                transparent,
                transparent 59px,
                rgba(255,255,255,0.018) 59px,
                rgba(255,255,255,0.018) 60px
            ),
            radial-gradient(ellipse 100% 60% at 50% -10%,
                rgba(29,66,138,0.18) 0%,
                transparent 70%),
            radial-gradient(ellipse 60% 40% at 90% 90%,
                rgba(200,16,46,0.12) 0%,
                transparent 60%),
            linear-gradient(180deg, #0A0A0F 0%, #0D0D18 100%) !important;
        background-attachment: fixed !important;
    }

    /* ─── Header principal del partido ─── */
    .game-header {
        background:
            linear-gradient(135deg, rgba(29,66,138,0.6) 0%, rgba(200,16,46,0.4) 100%),
            linear-gradient(180deg, var(--nba-card) 0%, var(--nba-surface) 100%);
        border: 1px solid var(--nba-border);
        border-top: 3px solid var(--nba-gold);
        padding: 2.5rem 2rem;
        border-radius: 14px;
        color: var(--text-primary);
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 12px 48px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06);
    }
    .game-header::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 85% 60% at 50% -10%, rgba(255,255,255,0.05), transparent 70%);
        pointer-events: none;
    }
    .game-header::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(240,180,41,0.07), transparent);
        pointer-events: none;
    }
    .game-header-content {
        position: relative;
        z-index: 1;
    }
    .game-header-side-logo {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        width: 220px;
        height: 220px;
        object-fit: contain;
        opacity: 0.12;
        filter: drop-shadow(0 8px 16px rgba(0,0,0,0.55));
        pointer-events: none;
        z-index: 0;
    }
    .game-header-side-logo.left {
        left: 8px;
    }
    .game-header-side-logo.right {
        right: 8px;
    }
    .game-header h1 {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: clamp(2rem, 4vw, 3.2rem) !important;
        letter-spacing: 0.08em !important;
        color: #FFFFFF !important;
        margin: 0 !important;
        line-height: 1 !important;
    }
    .game-header h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        color: var(--nba-gold) !important;
        margin: 0.6rem 0 0.3rem !important;
        text-transform: uppercase !important;
    }
    .game-header p {
        font-family: 'Barlow', sans-serif !important;
        font-size: 0.82rem !important;
        color: var(--text-muted) !important;
        margin: 0 !important;
        letter-spacing: 0.06em !important;
    }
    .game-header-matchup {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.1rem;
        margin-bottom: 0.8rem;
        flex-wrap: wrap;
    }
    .game-header-team {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        min-width: 200px;
        justify-content: center;
    }
    .team-logo-header {
        width: 58px;
        height: 58px;
        object-fit: contain;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.45));
    }
    .team-name-header {
        font-family: 'Bebas Neue', sans-serif;
        font-size: clamp(1.8rem, 3.5vw, 2.8rem);
        letter-spacing: 0.08em;
        line-height: 1;
        color: #FFFFFF;
    }
    .at-separator {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: var(--nba-gold);
    }

    /* ─── Tarjeta de equipo ─── */
    .team-card {
        background: linear-gradient(135deg, var(--nba-card) 0%, rgba(29,66,138,0.15) 100%);
        border: 1px solid var(--nba-border);
        border-left: 4px solid var(--nba-blue);
        padding: 1.6rem;
        border-radius: 12px;
        text-align: center;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
        animation: fadeSlideUp 0.38s ease both;
    }
    .team-card::before {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--nba-blue), var(--nba-gold));
    }

    /* ─── Stat box ─── */
    .stat-box {
        background: linear-gradient(135deg, var(--nba-card), rgba(29,66,138,0.12));
        border: 1px solid var(--nba-border);
        padding: 1.2rem 0.8rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.3rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s, transform 0.2s;
        animation: fadeSlideUp 0.38s ease both;
    }
    .stat-box:hover {
        border-color: var(--nba-gold);
        transform: translateY(-2px);
    }
    .stat-box::before {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--nba-red), var(--nba-gold));
    }
    .stat-label {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }
    .stat-value {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
        letter-spacing: 0.04em;
        line-height: 1;
        color: var(--nba-gold);
        margin: 0;
    }

    /* ─── Tabla de partidos recientes ─── */
    .recent-games-table {
        background: var(--nba-card);
        border: 1px solid var(--nba-border);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }

    /* ─── Win / Loss ─── */
    .win  { color: #2ECC71 !important; font-weight: 700; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 0.06em; }
    .loss { color: #FF5567 !important; font-weight: 700; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 0.06em; }

    /* ─── Tarjeta H2H ─── */
    .h2h-card {
        background: linear-gradient(135deg, rgba(29,66,138,0.35) 0%, rgba(200,16,46,0.25) 100%);
        border: 1px solid var(--nba-border);
        border-top: 3px solid var(--nba-blue);
        color: var(--text-primary);
        padding: 1.6rem;
        border-radius: 12px;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
        animation: fadeSlideUp 0.38s ease both;
    }
    .h2h-card::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 60% 40% at 80% 20%, rgba(200,16,46,0.07), transparent);
        pointer-events: none;
    }

    /* ─── Tarjetas de predicción de apuestas ─── */
    .bet-card {
        background: linear-gradient(135deg, rgba(26,26,38,0.98), rgba(18,18,26,0.98));
        border: 1px solid var(--nba-border);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 0.8rem 0;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .bet-card h4 {
        margin: 0 0 0.45rem 0;
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 0.06em;
        font-size: 1.03rem;
    }
    .bet-card .bet-main {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2rem;
        line-height: 1;
        letter-spacing: 0.05em;
        margin: 0.2rem 0 0.35rem;
    }
    .bet-over { color: #2ECC71; }
    .bet-under { color: #FF5567; }
    .bet-pass { color: #F0B429; }
    .bet-meta {
        color: var(--text-muted);
        font-size: 0.85rem;
        letter-spacing: 0.04em;
    }
    .bet-reason {
        margin: 0.2rem 0;
        color: #D6D6E8;
        font-size: 0.9rem;
    }

    /* ─── Tablas estilo Bootstrap ─── */
    .nba-table-shell {
        background: linear-gradient(180deg, rgba(26,26,38,0.98), rgba(18,18,26,0.98));
        border: 1px solid var(--nba-border);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 10px 34px rgba(0,0,0,0.45);
        margin: 0.8rem 0 1.2rem;
    }
    .nba-table-shell table {
        margin-bottom: 0 !important;
        width: 100%;
        color: var(--text-primary);
        border-collapse: separate;
        border-spacing: 0;
    }
    .nba-table-shell thead th {
        background: linear-gradient(135deg, var(--nba-blue), #132b5e) !important;
        color: #fff !important;
        font-family: 'Barlow Condensed', sans-serif;
        text-align: center !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.8rem 0.9rem;
        border-bottom: 1px solid rgba(255,255,255,0.08) !important;
        white-space: nowrap;
    }
    .nba-table-shell tbody td {
        background: rgba(26,26,38,0.98) !important;
        color: var(--text-primary) !important;
        border-top: 1px solid rgba(255,255,255,0.04) !important;
        border-bottom: 1px solid rgba(42,42,62,0.9) !important;
        padding: 0.72rem 0.9rem;
        font-size: 0.92rem;
        vertical-align: middle;
        text-align: center;
    }
    .nba-table-shell tbody tr:nth-of-type(odd) td {
        background: rgba(18,18,26,0.98) !important;
    }
    .nba-table-shell tbody tr:hover td {
        background: rgba(200,16,46,0.12) !important;
    }
    .nba-result-win {
        color: #2ECC71;
        font-weight: 700;
    }
    .nba-result-loss {
        color: #FF5567;
        font-weight: 700;
    }
    .nba-table-shell tbody tr:last-child td:first-child {
        border-bottom-left-radius: 14px;
    }
    .nba-table-shell tbody tr:last-child td:last-child {
        border-bottom-right-radius: 14px;
    }
    .nba-table-empty {
        padding: 1rem 1.2rem;
        border: 1px dashed var(--nba-border);
        border-radius: 12px;
        color: var(--text-muted);
        background: rgba(26,26,38,0.5);
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 0.05em;
    }

    /* ─── Alerta de lesiones ─── */
    .injury-alert {
        background: rgba(240,180,41,0.08);
        border: 1px solid rgba(240,180,41,0.35);
        border-left: 4px solid var(--nba-gold);
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1rem;
        letter-spacing: 0.04em;
        color: var(--nba-gold);
    }

    /* ─── Divider ─── */
    hr, .stMarkdown hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, var(--nba-border), transparent) !important;
        margin: 1.5rem 0 !important;
    }

    /* ─── Sidebar ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E0E18 0%, #0A0A14 100%) !important;
        border-right: 1px solid var(--nba-border) !important;
    }
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] header {
        font-family: 'Bebas Neue', sans-serif !important;
        color: var(--nba-gold) !important;
        letter-spacing: 0.08em;
    }
    [data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, var(--nba-red), #A00C24) !important;
        color: #fff !important;
        border: none !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.07em !important;
        border-radius: 8px !important;
        transition: opacity 0.2s, transform 0.15s !important;
        box-shadow: 0 4px 16px var(--nba-glow-red) !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
    }

    /* ─── Botón primario ─── */
    .stButton button[kind="primary"],
    .stButton button {
        background: linear-gradient(135deg, var(--nba-red) 0%, #A00C24 100%) !important;
        color: #fff !important;
        border: none !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.15rem !important;
        letter-spacing: 0.1em !important;
        border-radius: 8px !important;
        padding: 0.65rem 1.5rem !important;
        box-shadow: 0 4px 20px var(--nba-glow-red) !important;
        transition: transform 0.15s ease, box-shadow 0.2s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(200,16,46,0.55) !important;
    }

    /* ─── Selectbox ─── */
    .stSelectbox [data-baseweb="select"] > div {
        background-color: var(--nba-card) !important;
        border: 1px solid var(--nba-border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Barlow', sans-serif !important;
    }
    .stSelectbox [data-baseweb="select"] > div:focus-within {
        border-color: var(--nba-red) !important;
        box-shadow: 0 0 0 2px var(--nba-glow-red) !important;
    }

    /* ─── Expander ─── */
    .streamlit-expanderHeader {
        background: var(--nba-card) !important;
        border: 1px solid var(--nba-border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        transition: border-color 0.2s !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: var(--nba-gold) !important;
    }
    .streamlit-expanderContent {
        background: var(--nba-surface) !important;
        border: 1px solid var(--nba-border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* ─── Métricas ─── */
    [data-testid="stMetric"] {
        background: var(--nba-card) !important;
        border: 1px solid var(--nba-border) !important;
        border-radius: 10px !important;
        padding: 0.9rem 1rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.9rem !important;
        letter-spacing: 0.04em !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 600 !important;
    }

    /* ─── Dataframe ─── */
    .stDataFrame {
        border: 1px solid var(--nba-border) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .stDataFrame thead th {
        background: linear-gradient(135deg, var(--nba-blue), #142e6a) !important;
        color: #fff !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        font-size: 0.82rem !important;
        padding: 10px 14px !important;
    }
    .stDataFrame tbody tr {
        background: var(--nba-card) !important;
        transition: background 0.15s !important;
    }
    .stDataFrame tbody tr:nth-child(even) {
        background: var(--nba-surface) !important;
    }
    .stDataFrame tbody tr:hover {
        background: rgba(200,16,46,0.08) !important;
    }
    .stDataFrame tbody td {
        color: var(--text-primary) !important;
        border-color: var(--nba-border) !important;
        font-size: 0.9rem !important;
        padding: 9px 14px !important;
    }

    /* ─── Alertas ─── */
    .stSuccess {
        background: rgba(46,204,113,0.08) !important;
        border: 1px solid rgba(46,204,113,0.3) !important;
        border-radius: 8px !important;
        color: #2ECC71 !important;
    }
    .stWarning {
        background: rgba(240,180,41,0.08) !important;
        border: 1px solid rgba(240,180,41,0.3) !important;
        border-radius: 8px !important;
        color: var(--nba-gold) !important;
    }
    .stError {
        background: rgba(200,16,46,0.08) !important;
        border: 1px solid rgba(200,16,46,0.3) !important;
        border-radius: 8px !important;
        color: #FF5567 !important;
    }
    .stInfo {
        background: rgba(29,66,138,0.12) !important;
        border: 1px solid rgba(29,66,138,0.4) !important;
        border-radius: 8px !important;
        color: #7BA3FF !important;
    }

    /* ─── Subheaders y texto general ─── */
    h1, h2, h3 {
        font-family: 'Bebas Neue', sans-serif !important;
        letter-spacing: 0.06em !important;
        color: var(--text-primary) !important;
    }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; }

    p, li, label, span { color: var(--text-primary) !important; }
    .stMarkdown p { color: var(--text-primary) !important; }

    /* ─── Caption ─── */
    .stCaption, .stCaption p {
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
    }

    /* ─── Footer ─── */
    .nba-footer {
        text-align: center;
        padding: 2rem 1rem;
        border-top: 1px solid var(--nba-border);
        margin-top: 2rem;
        position: relative;
    }
    .nba-footer-logo {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.1rem;
        letter-spacing: 0.15em;
        background: linear-gradient(90deg, var(--nba-red), var(--nba-gold));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
    }
    .nba-footer-sub {
        color: var(--text-muted);
        font-size: 0.78rem;
        font-family: 'Barlow', sans-serif;
        letter-spacing: 0.04em;
    }

    /* ─── Scrollbar ─── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--nba-dark); }
    ::-webkit-scrollbar-thumb {
        background: var(--nba-border);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--nba-red); }

    /* ─── Animación de entrada ─── */
    @keyframes fadeSlideUp {
        from { opacity: 0; transform: translateY(18px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .game-header, .team-card, .stat-box, .h2h-card {
        animation: fadeSlideUp 0.38s ease both;
    }
</style>
"""


def apply_dashboard_styles():
    """Inyecta estilos en cada ejecución para evitar pérdida de CSS en multipágina."""
    st.markdown(DASHBOARD_STYLES, unsafe_allow_html=True)


def check_backend_health(max_retries: int = 2, timeout: int = 6) -> bool:
    """Verifica salud del backend con reintentos para evitar falsos negativos por timeout transitorio."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=timeout)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        if attempt < max_retries:
            time.sleep(0.35 * (attempt + 1))

    return False

# ============================================================================
# FUNCIONES DE API
# ============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_todays_games(date: str = None) -> List[Dict]:
    """Obtiene los partidos de una fecha específica."""
    try:
        params = {}
        if date:
            params["date"] = date

        response = requests.get(
            f"{BACKEND_URL}/api/games/today",
            params=params,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error obteniendo partidos: {e}")
        return []


@st.cache_data(ttl=180, show_spinner=False)
def get_game_preview(game_id: str, as_of_date: Optional[str] = None) -> Dict:
    """Obtiene la vista previa consolidada del partido desde el backend."""
    try:
        params = {}
        if as_of_date:
            params['date'] = as_of_date
        response = requests.get(
            f"{BACKEND_URL}/api/game/{game_id}/preview",
            params=params,
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


def get_team_recent_games(team_id: int, last_n: int = 5, as_of_date: Optional[str] = None) -> pd.DataFrame:
    """
    Obtiene los últimos N partidos de un equipo.
    Usa el endpoint de team_gamelogs indirectamente a través del backend.
    """
    try:
        # Este endpoint aún no existe, lo agregaremos al backend
        response = requests.get(
            f"{BACKEND_URL}/api/team/{team_id}/recent-games",
            params={
                "last_n": last_n,
                "as_of_date": as_of_date,
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('games', []))
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=180, show_spinner=False)
def get_team_stats(team_id: int) -> Dict:
    """Obtiene estadísticas generales del equipo."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/team/{team_id}/stats",
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=180, show_spinner=False)
def get_h2h_history(home_team_id: int, away_team_id: int, as_of_date: Optional[str] = None) -> Dict:
    """Obtiene el historial H2H entre dos equipos."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/h2h",
            params={
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "last_n": 10,
                "as_of_date": as_of_date,
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=180, show_spinner=False)
def get_injury_report_data() -> List[Dict]:
    """Obtiene lesiones globales con cache para evitar golpear el backend en cada rerun."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/injury-report", timeout=30)
        if response.status_code == 200:
            return response.json().get('injuries', [])
        return []
    except Exception:
        return []


def _safe_mean(values: List[float]) -> float:
    clean = [float(v) for v in values if v is not None]
    return sum(clean) / len(clean) if clean else 0.0


def _extract_pts_against(result_text: str) -> Optional[int]:
    """Extrae puntos en contra desde un string tipo 'W 112-108'."""
    if not result_text:
        return None
    match = re.search(r"[WL]\s+(\d+)-(\d+)", str(result_text).strip(), re.IGNORECASE)
    if not match:
        return None
    return int(match.group(2))


def _team_recent_profile(recent_games) -> Dict[str, float]:
    """Calcula perfil ofensivo/defensivo reciente para el modelo de total."""
    # Convertir lista a DataFrame si es necesario
    if isinstance(recent_games, list):
        recent_games = pd.DataFrame(recent_games)
    elif not isinstance(recent_games, pd.DataFrame):
        recent_games = pd.DataFrame()
    
    if recent_games.empty:
        return {
            "avg_for": 0.0,
            "avg_against": 0.0,
            "avg_total": 0.0,
            "win_rate": 0.0,
            "sample": 0,
        }

    pts_for = pd.to_numeric(recent_games.get("pts"), errors="coerce") if "pts" in recent_games.columns else pd.Series(dtype=float)
    pts_against = recent_games.get("result", pd.Series(dtype=str)).apply(_extract_pts_against) if "result" in recent_games.columns else pd.Series(dtype=float)

    results = recent_games.get("result", pd.Series(dtype=str)).fillna("").astype(str)
    wins = (results.str.strip().str.upper().str.startswith("W")).sum()
    sample = len(recent_games)

    avg_for = _safe_mean(pts_for.dropna().tolist())
    avg_against = _safe_mean([x for x in pts_against.tolist() if x is not None])

    return {
        "avg_for": avg_for,
        "avg_against": avg_against,
        "avg_total": avg_for + avg_against,
        "win_rate": (wins / sample) if sample else 0.0,
        "sample": sample,
    }


def build_game_betting_insights(game: Dict, as_of_date: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
    """Construye predicciones de total, moneyline y team totals para un partido."""
    context = context or {}
    away_recent = context.get("away_recent_games")
    home_recent = context.get("home_recent_games")
    h2h_data = context.get("h2h")

    if away_recent is None:
        away_recent = get_team_recent_games(game["away_team_id"], last_n=5, as_of_date=as_of_date)
    if home_recent is None:
        home_recent = get_team_recent_games(game["home_team_id"], last_n=5, as_of_date=as_of_date)
    if h2h_data is None:
        h2h_data = get_h2h_history(game["home_team_id"], game["away_team_id"], as_of_date=as_of_date)

    away_profile = _team_recent_profile(away_recent)
    home_profile = _team_recent_profile(home_recent)

    away_proj = (away_profile["avg_for"] * 0.55) + (home_profile["avg_against"] * 0.45)
    home_proj = (home_profile["avg_for"] * 0.55) + (away_profile["avg_against"] * 0.45)
    base_total = away_proj + home_proj

    h2h_totals: List[float] = []
    for row in h2h_data.get("matchups", []):
        pts_for = row.get("pts_for")
        pts_against = row.get("pts_against")
        try:
            if pts_for is not None and pts_against is not None:
                h2h_totals.append(float(pts_for) + float(pts_against))
        except Exception:
            continue

    h2h_avg_total = _safe_mean(h2h_totals)
    projected_total = (base_total * 0.75 + h2h_avg_total * 0.25) if h2h_avg_total > 0 else base_total

    model_line = round(projected_total * 2) / 2

    projected_margin = (home_proj + 2.5) - away_proj
    if projected_margin >= 2:
        moneyline_pick = f"ML {game['home_team']}"
    elif projected_margin <= -2:
        moneyline_pick = f"ML {game['away_team']}"
    else:
        moneyline_pick = "Sin edge claro"

    moneyline_conf = min(82.0, 52.0 + abs(projected_margin) * 4)

    return {
        "projected_total": projected_total,
        "model_line": model_line,
        "away_proj": away_proj,
        "home_proj": home_proj,
        "h2h_avg_total": h2h_avg_total,
        "h2h_sample": len(h2h_totals),
        "moneyline_pick": moneyline_pick,
        "moneyline_conf": moneyline_conf,
        "projected_margin": projected_margin,
        "away_profile": away_profile,
        "home_profile": home_profile,
    }


def evaluate_over_under_pick(projected_total: float, market_line: float, sample_boost: float = 0.0) -> Dict:
    """Evalúa recomendación O/U comparando modelo vs línea de mercado."""
    diff = projected_total - market_line
    if diff >= 3:
        pick = "OVER"
        css_class = "bet-over"
    elif diff <= -3:
        pick = "UNDER"
        css_class = "bet-under"
    else:
        pick = "PASS"
        css_class = "bet-pass"

    confidence = 55.0 + min(24.0, abs(diff) * 4.0) + sample_boost
    if pick == "PASS":
        confidence = min(confidence, 60.0)
    confidence = min(confidence, 87.0)

    reasons = []
    reasons.append(f"Modelo: {projected_total:.1f} pts vs mercado {market_line:.1f}")
    reasons.append(f"Diferencia estimada: {diff:+.1f} pts")
    if abs(diff) >= 5:
        reasons.append("Ventaja estadística amplia frente a la línea")
    elif abs(diff) >= 3:
        reasons.append("Ventaja moderada frente a la línea")
    else:
        reasons.append("Línea muy ajustada, evitar sobreexposición")

    return {
        "pick": pick,
        "class": css_class,
        "confidence": confidence,
        "edge": diff,
        "reasons": reasons,
    }


def format_game_time(
    game_time_str: str,
    game_status: str = None,
    display_date: Optional[str] = None,
) -> str:
    """Convierte la hora del partido a hora de Colombia y conserva la fecha elegida si el juego no ha iniciado."""
    if not game_time_str or game_time_str == 'TBD':
        return game_status or 'TBD'
    
    if game_status and any(kw in game_status.lower() for kw in ['final', 'q1', 'q2', 'q3', 'q4', 'ot']):
        return game_status

    try:
        et_zone = tz.gettz('America/New_York')
        col_zone = tz.gettz('America/Bogota')
        
        et_time = parser.parse(game_time_str)
        if et_time.tzinfo is None:
            et_time = et_time.replace(tzinfo=et_zone)
        
        col_time = et_time.astimezone(col_zone)
        if display_date and display_date != col_time.strftime('%Y-%m-%d'):
            return f"{display_date[8:10]}/{display_date[5:7]} {col_time.strftime('%I:%M %p COT')}"
        return col_time.strftime('%d/%m %I:%M %p COT')
    except Exception:
        if display_date:
            return display_date
        return game_status or game_time_str


def get_team_logo_url(team_id: Optional[int]) -> str:
    """Retorna la URL del logo oficial NBA para un team_id."""
    if not team_id:
        return ""
    return f"https://cdn.nba.com/logos/nba/{int(team_id)}/global/L/logo.svg"


def deduplicate_games(games: List[Dict]) -> List[Dict]:
    """Elimina partidos duplicados priorizando game_id."""
    unique_games: List[Dict] = []
    seen_keys = set()

    for game in games:
        key = game.get('game_id') or (
            game.get('away_team'),
            game.get('home_team'),
            game.get('game_time')
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_games.append(game)

    return unique_games


def style_nba_table(df: pd.DataFrame, format_map: Optional[Dict[str, str]] = None):
    """Aplica estilo oscuro consistente a tablas del dashboard."""
    styler = df.style

    if format_map:
        available_formats = {k: v for k, v in format_map.items() if k in df.columns}
        if available_formats:
            styler = styler.format(available_formats)

    styler = styler.set_table_styles([
        {'selector': 'th', 'props': 'background-color: #1D428A; color: #F5F5F0; border: 1px solid #2A2A3E; font-weight: 700;'},
        {'selector': 'td', 'props': 'background-color: #1A1A26; color: #F5F5F0; border: 1px solid #2A2A3E;'},
        {'selector': 'tr:nth-child(even) td', 'props': 'background-color: #12121A;'}
    ])

    return styler


def render_bootstrap_table(
    df: pd.DataFrame,
    format_map: Optional[Dict[str, str]] = None,
    highlight_columns: Optional[List[str]] = None,
) -> str:
    """Renderiza una tabla HTML con look tipo Bootstrap para Streamlit."""
    if df.empty:
        return '<div class="nba-table-empty">Sin datos para mostrar</div>'

    display_df = df.copy()
    highlight_columns = highlight_columns or []

    if format_map:
        for column, fmt in format_map.items():
            if column in display_df.columns:
                def _format_value(value):
                    try:
                        if pd.isna(value):
                            return ''
                    except Exception:
                        pass
                    try:
                        return fmt.format(value)
                    except Exception:
                        return str(value)

                display_df[column] = display_df[column].apply(_format_value)

    def _cell_html(column: str, value) -> str:
        text = '' if value is None else str(value)
        escaped = html.escape(text)
        if column in highlight_columns:
            normalized = text.strip().upper()
            if normalized.startswith('W'):
                return f'<span class="nba-result-win">{escaped}</span>'
            if normalized.startswith('L'):
                return f'<span class="nba-result-loss">{escaped}</span>'
        return escaped

    header_html = ''.join(f'<th>{html.escape(str(column))}</th>' for column in display_df.columns)
    body_rows = []
    for _, row in display_df.iterrows():
        cells = ''.join(
            f'<td>{_cell_html(column, row[column])}</td>'
            for column in display_df.columns
        )
        body_rows.append(f'<tr>{cells}</tr>')

    table_html = f'''
    <div class="table-responsive nba-table-shell">
        <table class="table table-dark table-striped table-hover table-sm nba-bootstrap-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{''.join(body_rows)}</tbody>
        </table>
    </div>
    '''

    return table_html


def display_betting_predictions(game: Dict, as_of_date: Optional[str] = None, context: Optional[Dict] = None):
    """Renderiza predicciones de apuestas del partido (total, ML y props)."""
    st.header("💸 Predicción y Sugerencias de Apuesta")
    st.caption("Modelo rápido con forma reciente + H2H hasta la fecha seleccionada. Usa las sugerencias como apoyo, no como garantía.")

    insights = build_game_betting_insights(game, as_of_date=as_of_date, context=context)

    market_line = st.number_input(
        "Línea de mercado Over/Under (Total del partido)",
        min_value=150.0,
        max_value=280.0,
        value=float(insights["model_line"]),
        step=0.5,
        key=f"ou_market_line_{game['game_id']}",
    )

    sample_boost = 3.0 if insights["h2h_sample"] >= 5 else 0.0
    total_pick = evaluate_over_under_pick(
        projected_total=insights["projected_total"],
        market_line=float(market_line),
        sample_boost=sample_boost,
    )

    col_ou, col_ml = st.columns(2)

    with col_ou:
        st.markdown(
            f"""
            <div class="bet-card">
                <h4>Total del Partido (Over/Under)</h4>
                <div class="bet-main {total_pick['class']}">{total_pick['pick']}</div>
                <p class="bet-meta">Proyección modelo: <strong>{insights['projected_total']:.1f}</strong> · Línea mercado: <strong>{market_line:.1f}</strong></p>
                <p class="bet-meta">Confianza estimada: <strong>{total_pick['confidence']:.0f}%</strong> · Edge: <strong>{total_pick['edge']:+.1f}</strong></p>
                {''.join([f"<p class='bet-reason'>{html.escape(reason)}</p>" for reason in total_pick['reasons']])}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_ml:
        home_team_total_line = round(insights["home_proj"] * 2) / 2
        away_team_total_line = round(insights["away_proj"] * 2) / 2
        st.markdown(
            f"""
            <div class="bet-card">
                <h4>Picks Complementarios</h4>
                <p class="bet-main" style="color:#7BA3FF;">{html.escape(insights['moneyline_pick'])}</p>
                <p class="bet-meta">Confianza Moneyline: <strong>{insights['moneyline_conf']:.0f}%</strong> · Margen proyectado: <strong>{insights['projected_margin']:+.1f}</strong></p>
                <p class="bet-reason">Total de equipo {html.escape(game['home_team'])}: <strong>{home_team_total_line:.1f}</strong> (línea modelo)</p>
                <p class="bet-reason">Total de equipo {html.escape(game['away_team'])}: <strong>{away_team_total_line:.1f}</strong> (línea modelo)</p>
                <p class="bet-reason">H2H promedio total usado: <strong>{insights['h2h_avg_total']:.1f}</strong> en {insights['h2h_sample']} juegos</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.info("Esta sección muestra solo sugerencias del partido (totales y moneyline).")


# ============================================================================
# COMPONENTES DE UI
# ============================================================================
def display_game_header(game: Dict, selected_date: Optional[str] = None):
    """Muestra el encabezado principal del partido."""
    game_time = format_game_time(game.get('game_time'), game.get('game_status'), selected_date)
    away_logo = get_team_logo_url(game.get('away_team_id'))
    home_logo = get_team_logo_url(game.get('home_team_id'))
    
    st.markdown(f"""
    <div class="game-header">
        <img src="{away_logo}" alt="{game['away_team']}" class="game-header-side-logo left" onerror="this.style.display='none';"/>
        <img src="{home_logo}" alt="{game['home_team']}" class="game-header-side-logo right" onerror="this.style.display='none';"/>
        <div class="game-header-content" style="text-align: center;">
            <div class="game-header-matchup">
                <div class="game-header-team">
                    <img src="{away_logo}" alt="{game['away_team']}" class="team-logo-header" onerror="this.style.display='none';"/>
                    <span class="team-name-header">{game['away_team']}</span>
                </div>
                <span class="at-separator">@</span>
                <div class="game-header-team">
                    <img src="{home_logo}" alt="{game['home_team']}" class="team-logo-header" onerror="this.style.display='none';"/>
                    <span class="team-name-header">{game['home_team']}</span>
                </div>
            </div>
            <h3 style="margin: 0.5rem 0;">
                📅 {game_time}
            </h3>
            <p style="margin: 0;">
                Game ID: {game['game_id']}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_team_stats(team_name: str, team_id: int, is_away: bool = False, team_stats: Optional[Dict] = None):
    """Muestra estadísticas generales del equipo."""
    with st.container():
        st.subheader(f"{'🏃 Visitante' if is_away else '🏠 Local'}: {team_name}")

        stats = team_stats or get_team_stats(team_id)
        if not stats:
            st.warning("No se pudieron cargar las estadísticas")
            return

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Promedio Pts</div>
                <div class="stat-value">{stats.get('pts_per_game', 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Promedio Reb</div>
                <div class="stat-value">{stats.get('reb_per_game', 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Promedio Ast</div>
                <div class="stat-value">{stats.get('ast_per_game', 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Record</div>
                <div class="stat-value">{stats.get('wins', 0)}-{stats.get('losses', 0)}</div>
            </div>
            """, unsafe_allow_html=True)

        # Estadísticas adicionales en fila expandible
        with st.expander("📊 Estadísticas Completas"):
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.metric("FG%", f"{stats.get('fg_pct', 0)*100:.1f}%")

            with col_b:
                st.metric("3P%", f"{stats.get('fg3_pct', 0)*100:.1f}%")

            with col_c:
                st.metric("Win %", f"{stats.get('win_pct', 0)*100:.1f}%")


def display_recent_games(team_name: str, team_id: int, as_of_date: Optional[str] = None, recent_games: Optional[pd.DataFrame] = None):
    """Muestra los últimos 5 partidos del equipo."""
    st.subheader(f"📊 Últimos 5 Partidos - {team_name}")
    
    df = recent_games if recent_games is not None else get_team_recent_games(team_id, last_n=5, as_of_date=as_of_date)
    if df.empty:
        st.info("Sin datos de partidos recientes disponibles")
        return

    # Seleccionar columnas y renombrar
    display_cols = {
        'date': 'Fecha',
        'matchup': 'Rival',
        'result': 'Resultado',
        'pts': 'Pts',
        'reb': 'Reb',
        'ast': 'Ast'
    }

    df_display = df[[col for col in display_cols.keys() if col in df.columns]].copy()
    df_display = df_display.rename(columns=display_cols)
    if 'Fecha' in df_display.columns:
        df_display['Fecha'] = pd.to_datetime(df_display['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_display['Fecha'] = df_display['Fecha'].fillna('')

    st.markdown(
        render_bootstrap_table(df_display, highlight_columns=['Resultado']),
        unsafe_allow_html=True
    )


def display_h2h(home_team: str, away_team: str, home_id: int, away_id: int, as_of_date: Optional[str] = None, h2h_data: Optional[Dict] = None):
    """Muestra el historial H2H entre los dos equipos."""
    st.subheader(f"🔄 Historial H2H: {away_team} vs {home_team}")
    
    h2h_data = h2h_data or get_h2h_history(home_id, away_id, as_of_date=as_of_date)
    matchups = h2h_data.get('matchups', []) if h2h_data else []

    if not matchups:
        st.info("Sin enfrentamientos previos encontrados")
        return

    df_h2h = pd.DataFrame(matchups)
    h2h_display_cols = {
        'date': 'FECHA',
        'matchup': 'ENFRENTAMIENTO',
        'result': 'RESULTADO',
        'pts_for': 'PTS A FAVOR',
        'pts_against': 'PTS EN CONTRA',
        'reb_home': 'REB LOCAL',
        'reb_away': 'REB VISITANTE'
    }
    df_h2h = df_h2h[[col for col in h2h_display_cols.keys() if col in df_h2h.columns]].copy()
    df_h2h = df_h2h.rename(columns=h2h_display_cols)
    if 'FECHA' in df_h2h.columns:
        df_h2h['FECHA'] = pd.to_datetime(df_h2h['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_h2h['FECHA'] = df_h2h['FECHA'].fillna('')

    # Estadísticas H2H
    away_wins = h2h_data.get('away_wins', 0)
    home_wins = h2h_data.get('home_wins', 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        record = f"{away_wins}-{home_wins}"
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">{away_team} vs {home_team}</div>
            <div class="stat-value">{record}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if not df_h2h.empty:
            avg_away = df_h2h['PTS A FAVOR'].mean() if 'PTS A FAVOR' in df_h2h.columns else 0
            avg_home = df_h2h['PTS EN CONTRA'].mean() if 'PTS EN CONTRA' in df_h2h.columns else 0
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Promedio Pts</div>
                <div class="stat-value">{avg_away:.1f}-{avg_home:.1f}</div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        if not df_h2h.empty:
            total_pts = (df_h2h['PTS A FAVOR'] + df_h2h['PTS EN CONTRA']).mean() if all(col in df_h2h.columns for col in ['PTS A FAVOR', 'PTS EN CONTRA']) else 0
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">Promedio Total</div>
                <div class="stat-value">{total_pts:.1f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(
        render_bootstrap_table(
            df_h2h,
            format_map={
                'PTS A FAVOR': '{:.0f}',
                'PTS EN CONTRA': '{:.0f}',
                'REB LOCAL': '{:.0f}',
                'REB VISITANTE': '{:.0f}'
            },
            highlight_columns=['RESULTADO']
        ),
        unsafe_allow_html=True
    )


def display_injury_report(home_team: str, away_team: str, injuries: Optional[List[Dict]] = None):
    """Muestra lesiones de ambos equipos."""
    st.subheader("🏥 Reporte de Lesiones")
    
    injuries = injuries if injuries is not None else get_injury_report_data()
    if not injuries:
        st.info("Sin datos de lesiones disponibles")
        return

    df_injuries = pd.DataFrame(injuries)

    # Filtrar por equipos en el partido
    df_filtered = df_injuries[
        (df_injuries['TEAM_NAME'].str.contains(home_team, case=False, na=False)) |
        (df_injuries['TEAM_NAME'].str.contains(away_team, case=False, na=False))
    ]

    if not df_filtered.empty:
        st.markdown("""
        <div class="injury-alert">
            ⚠️ Hay jugadores lesionados o cuestionables en este partido.
        </div>
        """, unsafe_allow_html=True)

        injury_table = df_filtered[['PLAYER_NAME', 'TEAM_NAME', 'Current_Status', 'Comment']]
        st.markdown(render_bootstrap_table(injury_table), unsafe_allow_html=True)
    else:
        st.info("✅ Sin lesiones reportadas en estos equipos")


# ============================================================================
# MAIN
# ============================================================================
def main():
    apply_dashboard_styles()

    # Header NBA Premium
    st.markdown("""
    <div style="text-align:center; padding: 2.5rem 1rem 1rem;">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:0.85rem; font-weight:600;
                    letter-spacing:0.35em; color:#F0B429; text-transform:uppercase; margin-bottom:0.4rem;">
            Game Intelligence · Real-Time Stats
        </div>
        <div style="display:flex; align-items:flex-end; justify-content:center; gap:0.45rem;">
            <span style="font-size:clamp(2.2rem,5.4vw,4.3rem); line-height:1; filter:drop-shadow(0 4px 10px rgba(0,0,0,0.35));">🏀</span>
            <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(2.8rem,6vw,5rem);
                        letter-spacing:0.06em; line-height:1;
                        background:linear-gradient(135deg,#FFFFFF 30%,#F0B429 80%);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                        background-clip:text;">
                NBA Game Dashboard
            </div>
        </div>
        <div style="display:inline-block; width:60px; height:3px;
                    background:linear-gradient(90deg,#C8102E,#F0B429);
                    border-radius:2px; margin:0.8rem auto 0;">
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Verificar salud del backend sin bloquear toda la UI por un timeout transitorio.
    backend_ok = check_backend_health(max_retries=2, timeout=6)
    if not backend_ok:
        st.warning("⚠️ El backend está lento o no responde temporalmente. Reintentando cargas en esta ejecución...")
    
    # Sidebar: selección de fecha y refresco
    with st.sidebar:
        st.header("Seleccionar Partido")
        selected_date = st.date_input(
            "📅 Selecciona una fecha:",
            value=datetime.now().date(),
            key="dashboard_selected_date"
        )
        date_str = selected_date.strftime("%Y-%m-%d") if selected_date else None
        refresh_button = st.button("🔄 Actualizar Partidos", use_container_width=True)

    # Obtener partidos según fecha (cacheados en sesión)
    if "games" not in st.session_state or refresh_button:
        with st.spinner("🔍 Cargando partidos..."):
            st.session_state.games = get_todays_games(date=date_str)
            st.session_state.current_date = date_str

    if st.session_state.get("current_date") != date_str:
        with st.spinner("🔍 Cargando partidos..."):
            st.session_state.games = get_todays_games(date=date_str)
            st.session_state.current_date = date_str

    games = deduplicate_games(st.session_state.get("games", []))
    
    if not games:
        st.warning(f"📭 No hay partidos disponibles para la fecha seleccionada: {date_str}")
        return
    
    # Selector de partido
    game_options = [f"{g['away_team']} @ {g['home_team']}" for g in games]
    selected_game_idx = st.sidebar.selectbox(
        "Elige un partido:",
        range(len(games)),
        format_func=lambda i: game_options[i]
    )
    
    selected_game = games[selected_game_idx]
    preview_data = get_game_preview(selected_game['game_id'], as_of_date=date_str)
    
    # ====== GAME OVERVIEW ======
    st.divider()
    display_game_header(selected_game, selected_date=date_str)
    
    # ====== TEAM STATS ======
    st.divider()
    st.header("📈 Estadísticas Generales")
    
    col_away, col_home = st.columns(2)
    
    with col_away:
        display_team_stats(
            selected_game['away_team'],
            selected_game['away_team_id'],
            is_away=True,
            team_stats=preview_data.get('away_team') if preview_data else None
        )
    
    with col_home:
        display_team_stats(
            selected_game['home_team'],
            selected_game['home_team_id'],
            is_away=False,
            team_stats=preview_data.get('home_team') if preview_data else None
        )
    
    # ====== RECENT GAMES ======
    st.divider()
    st.header("🎬 Últimos Partidos")
    
    col_away_recent, col_home_recent = st.columns(2)
    
    with col_away_recent:
        display_recent_games(
            selected_game['away_team'],
            selected_game['away_team_id'],
            as_of_date=date_str,
            recent_games=pd.DataFrame(preview_data.get('away_recent_games', [])) if preview_data else None,
        )
    
    with col_home_recent:
        display_recent_games(
            selected_game['home_team'],
            selected_game['home_team_id'],
            as_of_date=date_str,
            recent_games=pd.DataFrame(preview_data.get('home_recent_games', [])) if preview_data else None,
        )
    
    # ====== H2H HISTORY ======
    st.divider()
    st.header("🔄 Enfrentamientos Previos (H2H) Esta Temporada")
    
    display_h2h(
        selected_game['home_team'],
        selected_game['away_team'],
        selected_game['home_team_id'],
        selected_game['away_team_id'],
        as_of_date=date_str,
        h2h_data=preview_data.get('h2h') if preview_data else None,
    )

    # ====== BETTING PREDICTIONS ======
    st.divider()
    display_betting_predictions(selected_game, as_of_date=date_str, context=preview_data)
    
    # ====== INJURY REPORT ======
    st.divider()
    display_injury_report(
        selected_game['home_team'],
        selected_game['away_team'],
        injuries=preview_data.get('injuries') if preview_data else None,
    )
    
    # ====== FOOTER ======
    st.divider()
    st.markdown("""
    <div class="nba-footer">
        <div class="nba-footer-logo">🏀 NBA BETTING ANALYZER PRO · GAME DASHBOARD</div>
        <div class="nba-footer-sub">Esta herramienta proporciona análisis educativo únicamente.</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()