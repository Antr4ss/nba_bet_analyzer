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
from typing import Dict, List
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

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .game-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #1f77b4;
    }
    .bet-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
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
            params={'stat_type': 'gamelog', 'last_n': 5},
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


def format_game_time(utc_time_str: str) -> str:
    """Convierte la hora UTC a hora local (ET) formateada."""
    if not utc_time_str or utc_time_str == 'TBD':
        return 'TBD'
    try:
        # Parsear la fecha UTC
        utc_time = parser.parse(utc_time_str)
        
        # Convertir a Eastern Time (ET)
        to_zone = tz.gettz('America/New_York')
        local_time = utc_time.astimezone(to_zone)
        
        return local_time.strftime('%d/%m/%Y %I:%M %p ET')
    except Exception:
        return utc_time_str


def display_game_card(game: Dict):
    """Muestra una tarjeta visual para un partido."""
    formatted_time = format_game_time(game.get('game_time', 'TBD'))
    st.markdown(f"""
    <div class="game-card">
        <h3>🏀 {game['away_team']} @ {game['home_team']}</h3>
        <p><strong>Hora:</strong> {formatted_time}</p>
        <p><strong>Game ID:</strong> {game['game_id']}</p>
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
        'EXCELENTE': '#00ff00',
        'BUENA': '#4CAF50',
        'MALA': '#ff6b6b'
    }
    quality_color = quality_colors.get(bet_quality, '#4CAF50')
    
    # Color según confianza
    conf_class = get_confidence_class(confidence)
    
    st.markdown(f"""
    <div class="bet-card">
        <h3>{rank_emoji} {bet['player_name']} ({bet.get('team', 'N/A')}) - {bet['stat_type']}</h3>
        <p style="font-size: 1.3rem; color: {quality_color}; font-weight: bold;">📊 {bet_quality}</p>
        <hr style="border-color: rgba(255,255,255,0.3);">
        <div style="display: flex; justify-content: space-around; margin-top: 1rem;">
            <div>
                <p style="font-size: 0.9rem; opacity: 0.8;">Proyección</p>
                <p style="font-size: 1.5rem; font-weight: bold;">{bet['projection']}</p>
            </div>
            <div>
                <p style="font-size: 0.9rem; opacity: 0.8;">Línea Sugerida</p>
                <p style="font-size: 1.5rem; font-weight: bold;">{bet['suggested_line']}</p>
            </div>
            <div>
                <p style="font-size: 0.9rem; opacity: 0.8;">Confianza</p>
                <p style="font-size: 1.5rem; font-weight: bold; color: #ffd700;">{confidence:.0f}%</p>
            </div>
        </div>
        <div style="margin-top: 1rem; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 5px;">
            <p style="font-size: 0.9rem; margin-bottom: 5px;"><strong>Razones:</strong></p>
            {''.join([f'<p style="font-size: 0.85rem; margin: 3px 0;">✓ {reason}</p>' for reason in reasons])}
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
    
    # Header
    st.markdown('<p class="main-header">🏀 NBA Betting Analyzer Pro</p>', 
                unsafe_allow_html=True)
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
                        
                        # Aplicar formato
                        st.dataframe(
                            display_df.style.format({
                                'Proyección': '{:.1f}',
                                'Línea': '{:.1f}',
                                'Edge %': '{:.1f}%',
                                'Confianza %': '{:.1f}%',
                                'Rating': '{:.1f}'
                            }).background_gradient(
                                subset=['Rating'],
                                cmap='RdYlGn'
                            ),
                            use_container_width=True,
                            height=400
                        )
                        
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
                                        
                                        st.dataframe(
                                            gamelog_df[cols_to_show].style.format({
                                                'FG_PCT': '{:.1%}'
                                            }),
                                            use_container_width=True
                                        )
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

                        st.dataframe(
                            injuries_df.style.map(highlight_status, subset=['Estado']),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.info(f"ℹ️ Se encontraron {len(injuries)} jugadores en el reporte de lesiones para este partido.")
                    else:
                        st.success("✅ No se reportan lesiones significativas para los equipos de este partido.")

                    
                    # Estadísticas del partido
                    st.markdown("---")
                    st.markdown("### 📈 Resumen Estadístico")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
                        st.metric("Total Apuestas", analysis['total_opportunities'])
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col2:
                        avg_rating = sum(b['final_rating'] for b in analysis['best_bets'][:5]) / min(5, len(analysis['best_bets']))
                        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
                        st.metric("Rating Promedio Top 5", f"{avg_rating:.1f}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col3:
                        avg_conf = sum(b['confidence'] for b in analysis['best_bets'][:5]) / min(5, len(analysis['best_bets']))
                        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
                        st.metric("Confianza Promedio", f"{avg_conf:.1f}%")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col4:
                        high_value = len([b for b in analysis['best_bets'] if b['final_rating'] >= 60])
                        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
                        st.metric("Apuestas Alta Confianza", high_value)
                        st.markdown('</div>', unsafe_allow_html=True)

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
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🏀 NBA Betting Analyzer Pro v2.0</p>
        <p>Desarrollado con FastAPI + Streamlit + NBA API</p>
        <p style="font-size: 0.8rem;">⚠️ Disclaimer: Este sistema es solo para fines educativos. 
        Las apuestas deportivas conllevan riesgos. Apuesta responsablemente.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()