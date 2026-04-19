"""
interface.py
Frontend interactivo con Streamlit para el sistema de análisis de apuestas NBA.
Interfaz intuitiva para seleccionar partidos y visualizar sugerencias de apuestas.
"""

import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt # Importación explícita para evitar errores en pandas
from datetime import datetime
from dateutil import parser, tz
import time
import html
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


# Configuración de la página
st.set_page_config(
    page_title="NBA Betting Analyzer Pro",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL del backend
BACKEND_URL = "http://localhost:8000"

# Estilos CSS personalizados — Diseño NBA Premium
st.markdown("""
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

    /* ─── Header principal ─── */
    .main-header-wrap {
        text-align: center;
        padding: 2.5rem 1rem 1rem;
        position: relative;
        overflow: hidden;
    }
    .main-header-eyebrow {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.35em;
        color: var(--nba-gold);
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }
    .main-header-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: clamp(2.8rem, 6vw, 5rem);
        letter-spacing: 0.06em;
        line-height: 1;
        background: linear-gradient(135deg, #FFFFFF 30%, var(--nba-gold) 80%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        text-shadow: none;
    }
    .main-header-accent {
        display: inline-block;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, var(--nba-red), var(--nba-gold));
        border-radius: 2px;
        margin: 0.8rem auto 0;
    }

    /* ─── Divider ─── */
    hr, .stMarkdown hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, var(--nba-border), transparent) !important;
        margin: 1.5rem 0 !important;
    }

    /* ─── Tarjeta de partido ─── */
    .game-card {
        background: linear-gradient(135deg, var(--nba-card) 0%, rgba(29,66,138,0.15) 100%);
        border: 1px solid var(--nba-border);
        border-left: 4px solid var(--nba-red);
        padding: 1.6rem 1.8rem;
        border-radius: 12px;
        margin: 1.2rem 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .game-card::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 70% 45% at 50% 10%, rgba(255,255,255,0.03), transparent);
        pointer-events: none;
    }
    .game-card-side-logo {
        position: absolute;
        width: 150px;
        height: 150px;
        object-fit: contain;
        top: 50%;
        transform: translateY(-50%);
        opacity: 0.12;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.55));
        pointer-events: none;
        z-index: 0;
    }
    .game-card-side-logo.left {
        left: 4px;
    }
    .game-card-side-logo.right {
        right: 4px;
    }
    .game-card-content {
        position: relative;
        z-index: 1;
    }
    .game-card-meta {
        text-align: center;
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
    .nba-table-empty {
        padding: 1rem 1.2rem;
        border: 1px dashed var(--nba-border);
        border-radius: 12px;
        color: var(--text-muted);
        background: rgba(26,26,38,0.5);
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 0.05em;
    }
    .game-card-side-logo[style*='display:none'] {
        opacity: 0;
    }
    .game-card::after {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(240,180,41,0.45), transparent);
        pointer-events: none;
    }
    .game-card h3 {
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.8rem !important;
        letter-spacing: 0.05em;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem !important;
    }
    .game-card p {
        color: var(--text-muted) !important;
        font-size: 0.9rem;
        margin: 0.2rem 0 !important;
    }
    .game-card p strong {
        color: var(--nba-gold) !important;
    }
    .game-card-matchup {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.7rem;
        flex-wrap: wrap;
        margin-bottom: 0.4rem;
    }
    .game-card-team {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .team-logo-inline {
        width: 34px;
        height: 34px;
        object-fit: contain;
        filter: drop-shadow(0 3px 6px rgba(0,0,0,0.45));
    }
    .team-name-inline {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.45rem;
        letter-spacing: 0.05em;
        color: var(--text-primary);
        line-height: 1;
    }
    .at-inline {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        color: var(--nba-gold);
        margin: 0 0.2rem;
    }

    /* ─── Tarjeta de apuesta ─── */
    .bet-card {
        background: linear-gradient(135deg, #1C1C2E 0%, #16162A 100%);
        border: 1px solid var(--nba-border);
        border-top: 3px solid var(--nba-red);
        color: var(--text-primary);
        padding: 1.8rem;
        border-radius: 12px;
        margin: 0.8rem 0;
        box-shadow:
            0 12px 40px rgba(0,0,0,0.6),
            0 0 0 0 transparent,
            inset 0 1px 0 rgba(255,255,255,0.06);
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.25s ease;
    }
    .bet-card:hover {
        transform: translateY(-2px);
        box-shadow:
            0 18px 50px rgba(0,0,0,0.7),
            0 0 30px var(--nba-glow-red);
    }
    .bet-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(ellipse 70% 40% at 80% 20%, rgba(200,16,46,0.08), transparent);
        pointer-events: none;
    }
    .bet-card h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
        letter-spacing: 0.03em;
        margin-bottom: 0.3rem !important;
    }
    .bet-card hr {
        border-color: rgba(255,255,255,0.1) !important;
        margin: 0.8rem 0 !important;
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
        transition: border-color 0.2s;
    }
    .stat-box:hover {
        border-color: var(--nba-gold);
    }
    .stat-box::before {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--nba-red), var(--nba-gold));
    }

    /* ─── Confianza ─── */
    .confidence-high {
        color: #2ECC71 !important;
        font-weight: 700;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.1em;
        letter-spacing: 0.05em;
    }
    .confidence-medium {
        color: var(--nba-gold) !important;
        font-weight: 700;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.1em;
    }
    .confidence-low {
        color: var(--nba-red) !important;
        font-weight: 700;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.1em;
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

    /* ─── Date input ─── */
    .stDateInput input {
        background-color: var(--nba-card) !important;
        border: 1px solid var(--nba-border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Barlow', sans-serif !important;
    }

    /* ─── Tabs ─── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 2px solid var(--nba-border) !important;
        gap: 0.3rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-muted) !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0.04em !important;
        border-radius: 6px 6px 0 0 !important;
        border: none !important;
        padding: 0.6rem 1.1rem !important;
        transition: color 0.2s, background 0.2s !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background: rgba(255,255,255,0.05) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--nba-gold) !important;
        border-bottom: 2px solid var(--nba-gold) !important;
        background: rgba(240,180,41,0.06) !important;
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

    /* ─── Spinner ─── */
    .stSpinner > div {
        border-top-color: var(--nba-red) !important;
    }

    /* ─── Progress bar ─── */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--nba-red), var(--nba-gold)) !important;
        border-radius: 4px !important;
    }
    .stProgress > div > div > div {
        background: var(--nba-border) !important;
        border-radius: 4px !important;
    }

    /* ─── Download button ─── */
    .stDownloadButton button {
        background: transparent !important;
        border: 1px solid var(--nba-gold) !important;
        color: var(--nba-gold) !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        border-radius: 8px !important;
        transition: background 0.2s, color 0.2s !important;
    }
    .stDownloadButton button:hover {
        background: var(--nba-gold) !important;
        color: var(--nba-dark) !important;
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
    .nba-footer-disclaimer {
        font-size: 0.72rem;
        color: #55556A;
        margin-top: 0.6rem;
        max-width: 540px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.5;
    }

    /* ─── Sidebar info ─── */
    [data-testid="stSidebar"] .stInfo {
        background: rgba(29,66,138,0.15) !important;
        border-color: rgba(29,66,138,0.45) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] .stInfo p {
        color: #8FAAEE !important;
        font-size: 0.87rem !important;
    }

    /* ─── Container border ─── */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        border-radius: 10px;
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
    .game-card, .bet-card, .stat-box {
        animation: fadeSlideUp 0.38s ease both;
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health() -> bool:
    """Verifica que el backend esté operativo."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_todays_games(date: str = None) -> List[Dict]:
    """Obtiene los partidos del día desde el backend."""
    try:
        params = {}
        if date:
            params['date'] = date
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


def analyze_game(game_id: str, date: str = None) -> Dict:
    """Solicita el análisis completo de un partido al backend."""
    try:
        with st.spinner("🔍 Analizando partido y calculando proyecciones..."):
            params = {}
            if date:
                params['date'] = date
                
            response = requests.get(
                f"{BACKEND_URL}/api/analysis/{game_id}",
                params=params,
                timeout=720
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error en el análisis: {response.status_code} - {response.text}")
                return {}
    except Exception as e:
        st.error(f"Error comunicándose con el servidor: {e}")
        return {}


def get_live_game_stats(game_id: str) -> Dict:
    """Obtiene estadísticas en tiempo real de un partido."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/live/game/{game_id}",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


def get_player_gamelog(player_id: int) -> List[Dict]:
    """Obtiene los últimos 5 partidos de un jugador."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/player/{player_id}",
            params={'stat_type': 'gamelog', 'last_n': 10},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def get_confidence_class(confidence: float) -> str:
    """Retorna la clase CSS según el nivel de confianza."""
    if confidence >= 70:
        return "confidence-high"
    elif confidence >= 50:
        return "confidence-medium"
    else:
        return "confidence-low"


def format_bet_direction(direction: str) -> str:
    """Formatea la dirección de la apuesta con emoji."""
    if direction == "OVER":
        return "📈 OVER"
    elif direction == "UNDER":
        return "📉 UNDER"
    else:
        return "⚠️ NO BET"


def format_game_time(game_time_str: str, game_status: str = None) -> str:
    """
    Convierte la hora del partido a hora de Colombia (COT, UTC-5).
    
    - game_time_str: timestamp ISO en zona ET (ej. "2025-04-18T19:30:00")
    - game_status: texto del estado (ej. "7:30 pm ET", "Final", "Q3 4:20")
    
    Si el partido ya empezó o finalizó, muestra el game_status directamente.
    Si es un partido futuro, convierte el timestamp ET → COT.
    """
    # Mostrar estado tal cual para partidos en curso o finalizados
    if game_status and any(kw in game_status.lower() for kw in ['final', 'q1', 'q2', 'q3', 'q4', 'ot', 'half']):
        return game_status

    if not game_time_str or game_time_str == 'TBD':
        return game_status or 'TBD'

    try:
        et_zone = tz.gettz('America/New_York')
        col_zone = tz.gettz('America/Bogota')

        # Parsear el timestamp y asignarle zona ET (el campo viene sin offset explícito)
        et_time = parser.parse(game_time_str)
        if et_time.tzinfo is None:
            et_time = et_time.replace(tzinfo=et_zone)

        # Convertir a Colombia
        col_time = et_time.astimezone(col_zone)
        return col_time.strftime('%d/%m/%Y %I:%M %p COT')
    except Exception:
        return game_status or game_time_str


def get_team_logo_url(team_id: Optional[int]) -> str:
    """Retorna la URL del logo oficial NBA para un team_id."""
    if not team_id:
        return ""
    return f"https://cdn.nba.com/logos/nba/{int(team_id)}/global/L/logo.svg"


def render_bootstrap_table(df: pd.DataFrame, format_map: Optional[Dict[str, str]] = None) -> str:
    """Renderiza una tabla HTML con look tipo Bootstrap para Streamlit."""
    if df.empty:
        return '<div class="nba-table-empty">Sin datos para mostrar</div>'

    display_df = df.copy()
    highlight_columns: List[str] = []

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


def style_nba_table(df: pd.DataFrame, format_map: Optional[Dict[str, str]] = None):
    """Aplica estilo oscuro consistente a tablas de la interfaz."""
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


def display_game_card(game: Dict):
    """Muestra una tarjeta visual para un partido."""
    formatted_time = format_game_time(game.get('game_time', 'TBD'), game.get('game_status'))
    away_logo = get_team_logo_url(game.get('away_team_id'))
    home_logo = get_team_logo_url(game.get('home_team_id'))
    game_id = game.get('game_id') or game.get('id') or "N/A"
    st.markdown(f"""
    <div class="game-card">
        <img src="{away_logo}" alt="{game['away_team']}" class="game-card-side-logo left" onerror="this.style.display='none';"/>
        <img src="{home_logo}" alt="{game['home_team']}" class="game-card-side-logo right" onerror="this.style.display='none';"/>
        <div class="game-card-content">
            <div class="game-card-matchup">
                <div class="game-card-team">
                    <img src="{away_logo}" alt="{game['away_team']}" class="team-logo-inline" onerror="this.style.display='none';"/>
                    <span class="team-name-inline">{game['away_team']}</span>
                </div>
                <span class="at-inline">@</span>
                <div class="game-card-team">
                    <img src="{home_logo}" alt="{game['home_team']}" class="team-logo-inline" onerror="this.style.display='none';"/>
                    <span class="team-name-inline">{game['home_team']}</span>
                </div>
            </div>
            <div class="game-card-meta">
                <p><strong>Hora:</strong> {formatted_time}</p>
                <p><strong>Game ID:</strong> {game_id}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_bet_suggestion(bet: Dict, rank: int):
    """Muestra una sugerencia de apuesta de forma atractiva."""
    confidence = bet.get('confidence', 50)
    rating = bet.get('final_rating', 0)
    bet_quality = bet.get('bet_quality', 'MALA')
    reasons = bet.get('reasons', [])
    
    # Determinar emoji de ranking
    rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
    
    # Color según calidad
    quality_colors = {
        'EXCELENTE': '#2ECC71',
        'BUENA': '#F0B429',
        'MALA': '#FF5567'
    }
    quality_color = quality_colors.get(bet_quality, '#F0B429')
    
    # Color según confianza
    conf_class = get_confidence_class(confidence)
    
    st.markdown(f"""
    <div class="bet-card">
        <h3>{rank_emoji} {bet['player_name']} ({bet.get('team', 'N/A')}) — {bet['stat_type']}</h3>
        <p style="font-family:'Barlow Condensed',sans-serif; font-size:1.15rem; color:{quality_color}; font-weight:700; letter-spacing:0.08em; margin:0.2rem 0 0.6rem;">
            ◆ {bet_quality}
        </p>
        <hr style="border-color:rgba(255,255,255,0.08)!important;">
        <div style="display:flex; justify-content:space-around; margin-top:1rem; flex-wrap:wrap; gap:0.5rem;">
            <div style="text-align:center; min-width:90px;">
                <p style="font-family:'Barlow Condensed',sans-serif; font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase; color:#8888AA; margin:0 0 4px;">Proyección</p>
                <p style="font-family:'Bebas Neue',sans-serif; font-size:2rem; letter-spacing:0.04em; color:#FFFFFF; margin:0; line-height:1;">{bet['projection']}</p>
            </div>
            <div style="text-align:center; min-width:90px;">
                <p style="font-family:'Barlow Condensed',sans-serif; font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase; color:#8888AA; margin:0 0 4px;">Línea Sugerida</p>
                <p style="font-family:'Bebas Neue',sans-serif; font-size:2rem; letter-spacing:0.04em; color:#FFFFFF; margin:0; line-height:1;">{bet['suggested_line']}</p>
            </div>
            <div style="text-align:center; min-width:90px;">
                <p style="font-family:'Barlow Condensed',sans-serif; font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase; color:#8888AA; margin:0 0 4px;">Confianza</p>
                <p style="font-family:'Bebas Neue',sans-serif; font-size:2rem; letter-spacing:0.04em; color:#F0B429; margin:0; line-height:1;">{confidence:.0f}%</p>
            </div>
        </div>
        <div style="margin-top:1.2rem; padding:12px 14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); border-radius:8px;">
            <p style="font-family:'Barlow Condensed',sans-serif; font-size:0.78rem; letter-spacing:0.1em; text-transform:uppercase; color:#8888AA; margin:0 0 8px;">Razones</p>
            {''.join([f"<p style='font-size:0.88rem; margin:4px 0; color:#D0D0E8;'><span style='color:#C8102E; font-weight:700;'>›</span> {reason}</p>" for reason in reasons])}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas adicionales simplificadas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Rating", f"{rating:.1f}/100")
    
    with col2:
        back_to_back_status = "⚠️ Sí" if bet.get('back_to_back', False) else "✅ No"
        st.metric("Back-to-Back", back_to_back_status)
    
    with col3:
        st.metric("Calidad", bet_quality)


def generate_gemini_analysis(game_data: Dict) -> str:
    """
    Análisis táctico del partido usando Google Gemini API.
    Requiere: GOOGLE_API_KEY en variables de entorno
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "⚠️ API key de Gemini no configurada. Configura GOOGLE_API_KEY en .env"
        
        genai.configure(api_key=api_key)

        # Selección dinámica de modelo compatible
        selected_model = None
        try:
            models = list(genai.list_models())
            # Filtrar modelos que soportan generateContent
            candidates = [
                m for m in models
                if hasattr(m, 'supported_generation_methods')
                and 'generateContent' in m.supported_generation_methods
            ]
            # Prioridad por versiones más nuevas
            preferred_order = [
                'gemini-1.5-flash-latest',
                'gemini-1.5-pro-latest',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-1.0-pro',
                'gemini-pro'
            ]
            # Mapear nombres disponibles
            available_names = [
                (getattr(m, 'name', '') or '')
                .replace('models/','') for m in candidates
            ]
            for name in preferred_order:
                if name in available_names:
                    selected_model = name
                    break
        except Exception:
            # Si falla el listado, usar fallback
            selected_model = 'gemini-1.5-flash'

        if not selected_model:
            selected_model = 'gemini-1.5-flash'

        model = genai.GenerativeModel(selected_model)
        
        home = game_data.get('home_team', 'Home')
        away = game_data.get('away_team', 'Away')
        
        prompt = f"""
        Proporciona un análisis táctico breve y profesional (máximo 300 palabras) del partido:
        {away} vs {home} en la NBA.
        
        Incluye:
        1. Matchups clave (1-2 comparaciones)
        2. Factores principales que afectarán el juego (ritmo, defensa, lesiones)
        3. Predicción general del resultado
        
        Formato: usa markdown con listas cortas.
        """
        
        response = model.generate_content(prompt)
        # Verificar si hay contenido
        if response and hasattr(response, 'text'):
            return response.text
        elif response and hasattr(response, 'parts'):
            return ''.join(part.text for part in response.parts)
        else:
            return "⚠️ No se recibió respuesta de Gemini"
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            return (
                "❌ Error al conectar con Gemini: " + error_msg + "\n\n"
                "Sugerencias:\n"
                "- Actualiza el paquete: pip install --upgrade google-generativeai\n"
                "- Usa modelos: gemini-1.5-flash-latest o gemini-1.5-pro-latest\n"
                "- Verifica tu API key en .env (GOOGLE_API_KEY)\n"
            )
        return (
            "❌ Error al obtener análisis de Gemini: " + error_msg + "\n\n"
            "Verifica tu conexión a internet y que la API key sea válida."
        )


def main():
    """Función principal de la interfaz Streamlit."""
    
    # Header NBA Premium
    st.markdown("""
    <div class="main-header-wrap">
        <div class="main-header-eyebrow">Advanced Analytics · Betting Intelligence</div>
        <div class="main-header-title">🏀 NBA Betting Analyzer Pro</div>
        <div class="main-header-accent"></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    # Verificar conexión con backend
    if not check_backend_health():
        st.error("⚠️ No se puede conectar con el servidor backend. Asegúrate de que está corriendo en http://localhost:8000")
        st.info("Para iniciar el backend, ejecuta: `uvicorn main:app --reload`")
        st.stop()
    
    st.success("✅ Conectado al servidor de análisis")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Selector de fecha
        selected_date = st.date_input(
            "📅 Selecciona una fecha:",
            value=datetime.now().date()
        )
        date_str = selected_date.strftime('%Y-%m-%d') if selected_date else None
        
        refresh_button = st.button("🔄 Actualizar Partidos", use_container_width=True)
        
        st.markdown("---")
        
        st.markdown("### 📊 Acerca del Sistema")
        st.info("""
        Este sistema analiza partidos de NBA en tiempo real y calcula 
        proyecciones estadísticas avanzadas para identificar apuestas de valor.
        
        **Funcionalidades:**
        - ✅ Datos en tiempo real
        - ✅ Filtro de lesiones
        - ✅ Análisis de tendencias
        - ✅ Ajuste por oponente
        - ✅ Detección de back-to-back
        """)
        
        st.markdown("---")
        st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    
    # Obtener partidos del día
    if 'games' not in st.session_state or refresh_button:
        with st.spinner("🔍 Cargando partidos..."):
            st.session_state.games = get_todays_games(date=date_str)
            st.session_state.current_date = date_str
    
    # Si cambió la fecha, recargar partidos
    if 'current_date' in st.session_state and st.session_state.current_date != date_str:
        with st.spinner("🔍 Cargando partidos..."):
            st.session_state.games = get_todays_games(date=date_str)
            st.session_state.current_date = date_str
    
    games = st.session_state.games
    
    if not games:
        st.warning("📅 No hay partidos programados para hoy o no se pudieron cargar los datos.")
        st.info("Los datos se actualizan automáticamente. Intenta recargar en unos minutos.")
        return
    
    # Mostrar resumen de partidos
    st.subheader(f"📅 Partidos de Hoy ({len(games)} encuentros)")
    
    # Selector de partido
    game_options = {
        f"{game['away_team']} @ {game['home_team']}": game 
        for game in games
    }
    
    selected_game_name = st.selectbox(
        "Selecciona un partido para análisis detallado:",
        options=list(game_options.keys()),
        key="game_selector"
    )
    
    if selected_game_name:
        selected_game = game_options[selected_game_name]
        
        # Mostrar info del partido seleccionado
        st.markdown("---")
        display_game_card(selected_game)
        
        # Botón de análisis
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button(
                "🎯 Analizar Partido y Generar Sugerencias",
                use_container_width=True,
                type="primary"
            )
        
        if analyze_button or f"analysis_{selected_game['game_id']}" in st.session_state:
            # Realizar análisis
            if analyze_button:
                analysis = analyze_game(selected_game['game_id'], date=date_str)
                st.session_state[f"analysis_{selected_game['game_id']}"] = analysis
            else:
                analysis = st.session_state[f"analysis_{selected_game['game_id']}"]
            
            if analysis and analysis.get('best_bets'):
                st.success(f"✅ Análisis completado. Se encontraron {analysis['total_opportunities']} oportunidades de valor.")
                
                # Tabs para organizar información
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "🎯 Mejores Apuestas",
                    "📊 Todas las Oportunidades",
                    "🤖 Análisis Táctico",
                    "🏥 Reporte de Lesiones",
                    "🔴 Live Tracker"
                ])
                
                with tab1:
                    st.subheader("🏆 Top 5 Mejores Oportunidades")
                    
                    best_bets = analysis['best_bets'][:5]
                    
                    for idx, bet in enumerate(best_bets, 1):
                        display_bet_suggestion(bet, idx)
                        st.markdown("---")
                
                with tab2:
                    st.subheader("📋 Todas las Oportunidades Detectadas")
                    
                    # Crear DataFrame para tabla
                    bets_df = pd.DataFrame(analysis['best_bets'])
                    
                    if not bets_df.empty:
                        # Formatear columnas con la nueva estructura
                        display_df = bets_df[[
                            'player_name', 'team', 'stat_type', 'projection', 
                            'suggested_line', 'bet_quality', 'confidence', 'final_rating'
                        ]].copy()
                        
                        display_df.columns = [
                            'Jugador', 'Equipo', 'Stat', 'Proyección', 'Línea Sugerida', 
                            'Calidad', 'Confianza %', 'Rating'
                        ]

                        styled_opportunities = style_nba_table(
                            display_df,
                            format_map={
                                'Proyección': '{:.1f}',
                                'Línea Sugerida': '{:.1f}',
                                'Confianza %': '{:.1f}%',
                                'Rating': '{:.1f}'
                            }
                        )

                        def highlight_rating(val):
                            try:
                                value = float(val)
                            except Exception:
                                return ''
                            if value >= 70:
                                return 'color: #2ECC71; font-weight: 700;'
                            if value >= 55:
                                return 'color: #F0B429; font-weight: 700;'
                            return 'color: #FF5567; font-weight: 700;'

                        def highlight_quality(val):
                            if isinstance(val, str):
                                val_norm = val.lower()
                                if 'excelente' in val_norm:
                                    return 'color: #2ECC71; font-weight: 700;'
                                if 'buena' in val_norm:
                                    return 'color: #F0B429; font-weight: 700;'
                                return 'color: #FF5567; font-weight: 700;'
                            return ''

                        if 'Rating' in display_df.columns:
                            styled_opportunities = styled_opportunities.map(highlight_rating, subset=['Rating'])
                        if 'Calidad' in display_df.columns:
                            styled_opportunities = styled_opportunities.map(highlight_quality, subset=['Calidad'])
                        
                        st.markdown(render_bootstrap_table(display_df), unsafe_allow_html=True)
                        
                        # Botón de descarga
                        csv = bets_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Descargar Análisis Completo (CSV)",
                            data=csv,
                            file_name=f"nba_analysis_{selected_game['game_id']}.csv",
                            mime="text/csv"
                        )
                        
                        st.markdown("---")
                        st.subheader("🔍 Detalle de Jugador (Últimos 5 Partidos)")
                        
                        # Selector de jugador para ver detalles
                        # Crear opciones legibles
                        player_options = {
                            f"{row['player_name']} ({row['stat_type']}) - {row['bet_quality']}": row 
                            for _, row in bets_df.iterrows()
                        }
                        
                        selected_player_key = st.selectbox(
                            "Selecciona una oportunidad para ver estadísticas recientes:",
                            options=list(player_options.keys()),
                            key="player_detail_selector"
                        )
                        
                        if selected_player_key:
                            selected_bet_detail = player_options[selected_player_key]
                            player_id = selected_bet_detail.get('player_id')
                            
                            if player_id:
                                with st.spinner(f"Cargando últimos juegos de {selected_bet_detail['player_name']}..."):
                                    gamelog = get_player_gamelog(player_id)
                                    
                                    if gamelog:
                                        gamelog_df = pd.DataFrame(gamelog)
                                        
                                        # Calcular PRA
                                        if all(c in gamelog_df.columns for c in ['PTS', 'REB', 'AST']):
                                            gamelog_df['PRA'] = gamelog_df['PTS'] + gamelog_df['REB'] + gamelog_df['AST']
                                        
                                        # Seleccionar columnas relevantes
                                        cols_to_show = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PRA', 'PTS', 'REB', 'AST', 'FG3M', 'FG_PCT']
                                        # Filtrar solo las que existen
                                        cols_to_show = [c for c in cols_to_show if c in gamelog_df.columns]

                                        gamelog_table = gamelog_df[cols_to_show]
                                        styled_gamelog = style_nba_table(
                                            gamelog_table,
                                            format_map={'FG_PCT': '{:.1%}'}
                                        )
                                        
                                        st.markdown(render_bootstrap_table(gamelog_table, format_map={'FG_PCT': '{:.1%}'}), unsafe_allow_html=True)
                                    else:
                                        st.warning("No se encontraron datos recientes para este jugador.")
                            else:
                                st.error("No se pudo identificar el ID del jugador.")
                
                with tab3:
                    st.subheader("🤖 Análisis Táctico con IA")
                    
                    with st.spinner("Generando análisis con Gemini..."):
                        time.sleep(1)  # Simular tiempo de procesamiento
                        gemini_analysis = generate_gemini_analysis(selected_game)
                    
                    st.markdown(gemini_analysis)
                
                with tab4:
                    st.subheader("🏥 Reporte de Lesiones")
                    
                    injuries = analysis.get('injuries', [])
                    if injuries:
                        injuries_df = pd.DataFrame(injuries)
                        
                        # Renombrar columnas para mejor visualización
                        injuries_df = injuries_df.rename(columns={
                            'PLAYER_NAME': 'Jugador',
                            'TEAM_NAME': 'Equipo',
                            'Current_Status': 'Estado',
                            'Comment': 'Detalle'
                        })
                        
                        # Aplicar estilos condicionales
                        def highlight_status(val):
                            color = 'red' if val == 'Out' else 'orange' if val in ['Doubtful', 'Questionable'] else 'green'
                            return f'color: {color}; font-weight: bold'

                        st.markdown(render_bootstrap_table(injuries_df), unsafe_allow_html=True)
                        
                        st.info(f"ℹ️ Se encontraron {len(injuries)} jugadores en el reporte de lesiones para este partido.")
                    else:
                        st.success("✅ No se reportan lesiones significativas para los equipos de este partido.")


                with tab5:
                    st.subheader("🔴 Seguimiento en Vivo")
                    
                    col_refresh, _ = st.columns([1, 4])
                    with col_refresh:
                        if st.button("🔄 Actualizar Stats", key="refresh_live"):
                            st.rerun()
                        
                    live_stats = get_live_game_stats(selected_game['game_id'])
                    
                    if not live_stats:
                        st.info("El partido no ha comenzado o no hay datos disponibles aún.")
                    else:
                        st.markdown("#### 📊 Progreso de Oportunidades Detectadas")
                        
                        if not analysis.get('best_bets'):
                            st.info("No hay apuestas sugeridas para rastrear.")
                        else:
                            # Iterar sobre todas las apuestas sugeridas
                            for idx, bet in enumerate(analysis['best_bets']):
                                player_name = bet['player_name']
                                stat_type = bet['stat_type'].upper()
                                target_line = bet['suggested_line']
                                # Determinar tipo de apuesta (asumimos OVER si la proyección es mayor a la línea)
                                # En la estructura actual no tenemos explícitamente 'recommended_bet' en todos los casos,
                                # pero podemos inferirlo o usar 'recommended_bet' si existe.
                                bet_type = bet.get('recommended_bet', 'OVER')
                                if 'recommended_bet' not in bet:
                                    # Inferencia simple
                                    bet_type = 'OVER' if bet['projection'] > bet['suggested_line'] else 'UNDER'

                                # Buscar stats del jugador en vivo
                                player_live_data = None
                                for pid, pdata in live_stats.items():
                                    # Comparación flexible de nombres
                                    if pdata['name'] == player_name or player_name in pdata['name'] or pdata['name'] in player_name:
                                        player_live_data = pdata
                                        break
                                
                                # Redondear línea para visualización (Enteros)
                                display_line = int(round(target_line))

                                # Contenedor para la tarjeta
                                with st.container():
                                    col_info, col_viz = st.columns([2, 3])
                                    
                                    with col_info:
                                        st.markdown(f"**{player_name}**")
                                        st.caption(f"{stat_type} - Línea: {display_line} ({bet_type})")
                                        
                                        if player_live_data:
                                            # Calcular valor actual (Soporte para PRA)
                                            if stat_type == 'PRA':
                                                current_val = (player_live_data.get('pts', 0) + 
                                                             player_live_data.get('reb', 0) + 
                                                             player_live_data.get('ast', 0))
                                            else:
                                                current_val = player_live_data.get(stat_type.lower(), 0)
                                                
                                            st.metric("Actual", current_val, delta=f"{current_val - display_line}")
                                        else:
                                            st.warning("Sin datos")

                                    with col_viz:
                                        if player_live_data:
                                            # Recalcular current_val para asegurar disponibilidad
                                            if stat_type == 'PRA':
                                                current_val = (player_live_data.get('pts', 0) + 
                                                             player_live_data.get('reb', 0) + 
                                                             player_live_data.get('ast', 0))
                                            else:
                                                current_val = player_live_data.get(stat_type.lower(), 0)
                                            
                                            if bet_type == 'OVER':
                                                # Barra de progreso para OVER
                                                progress = min(current_val / display_line if display_line > 0 else 0, 1.0)
                                                st.progress(progress)
                                                
                                                if current_val >= display_line:
                                                    st.success(f"✅ ¡CUBIERTA! ({current_val})")
                                                else:
                                                    diff = display_line - current_val
                                                    st.caption(f"Faltan {diff} para cubrir")
                                            
                                            else: # UNDER
                                                # Barra de "Peligro" para UNDER
                                                risk = min(current_val / display_line if display_line > 0 else 0, 1.0)
                                                st.progress(risk)
                                                
                                                if current_val > display_line:
                                                    st.error(f"❌ PERDIDA ({current_val})")
                                                else:
                                                    cushion = display_line - current_val
                                                    st.success(f"✅ En juego (Margen: {cushion})")
                                        else:
                                            st.info("⏳ Esperando que ingrese al partido...")
                                    
                                    st.markdown("---")
            
            else:
                st.warning("No se encontraron oportunidades de valor significativas para este partido.")
                st.info("Esto puede deberse a que las líneas del mercado están muy ajustadas o faltan datos de jugadores.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="nba-footer">
        <div class="nba-footer-logo">🏀 NBA BETTING ANALYZER PRO · v2.0</div>
        <div class="nba-footer-sub">Desarrollado con FastAPI + Streamlit + NBA API</div>
        <div class="nba-footer-disclaimer">
            ⚠️ Disclaimer: Este sistema es solo para fines educativos.
            Las apuestas deportivas conllevan riesgos. Apuesta responsablemente.
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()