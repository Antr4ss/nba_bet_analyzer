"""
interface.py
Frontend interactivo con Streamlit para el sistema de análisis de apuestas NBA.
Interfaz intuitiva para seleccionar partidos y visualizar sugerencias de apuestas.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
from typing import Dict, List

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


def get_todays_games() -> List[Dict]:
    """Obtiene los partidos del día desde el backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/games/today", timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error obteniendo partidos: {e}")
        return []


def analyze_game(game_id: str) -> Dict:
    """Solicita el análisis completo de un partido al backend."""
    try:
        with st.spinner("🔍 Analizando partido y calculando proyecciones..."):
            response = requests.get(
                f"{BACKEND_URL}/api/analysis/{game_id}",
                timeout=120
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error en el análisis: {response.status_code}")
                return {}
    except Exception as e:
        st.error(f"Error comunicándose con el servidor: {e}")
        return {}


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


def display_game_card(game: Dict):
    """Muestra una tarjeta visual para un partido."""
    st.markdown(f"""
    <div class="game-card">
        <h3>🏀 {game['away_team']} @ {game['home_team']}</h3>
        <p><strong>Hora:</strong> {game['game_time']}</p>
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
    Integración con Gemini API para análisis táctico del partido.
    
    NOTA: Requiere API key de Google Gemini.
    Por ahora retorna análisis simulado.
    """
    # TODO: Implementar conexión real con Gemini API
    # from google import generativeai as genai
    # genai.configure(api_key="TU_API_KEY")
    # model = genai.GenerativeModel('gemini-pro')
    
    # Análisis simulado
    home = game_data.get('home_team', 'Home')
    away = game_data.get('away_team', 'Away')
    
    analysis = f"""
    **Análisis Táctico del Partido**
    
    El enfrentamiento entre {away} y {home} promete ser un encuentro dinámico con 
    múltiples oportunidades de valor en el mercado de jugadores individuales. 
    
    Basándonos en las tendencias recientes y los matchups defensivos, identificamos 
    varias discrepancias significativas entre nuestras proyecciones estadísticas y 
    las líneas del mercado. Los jugadores en situación de back-to-back podrían 
    mostrar fatiga, mientras que aquellos con momentum positivo en sus últimos 
    5 juegos presentan las mejores oportunidades.
    
    **Factores Clave a Considerar:**
    - Ritmo de juego esperado y total de posesiones
    - Ventajas de matchup en posiciones específicas
    - Estado físico y minutos recientes de los jugadores clave
    - Historial directo entre ambos equipos
    """
    
    return analysis


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
        with st.spinner("🔍 Cargando partidos de hoy..."):
            st.session_state.games = get_todays_games()
    
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
                analysis = analyze_game(selected_game['game_id'])
                st.session_state[f"analysis_{selected_game['game_id']}"] = analysis
            else:
                analysis = st.session_state[f"analysis_{selected_game['game_id']}"]
            
            if analysis and analysis.get('best_bets'):
                st.success(f"✅ Análisis completado. Se encontraron {analysis['total_opportunities']} oportunidades de valor.")
                
                # Tabs para organizar información
                tab1, tab2, tab3 = st.tabs([
                    "🎯 Mejores Apuestas",
                    "📊 Todas las Oportunidades",
                    "🤖 Análisis Táctico"
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
                
                with tab3:
                    st.subheader("🤖 Análisis Táctico con IA")
                    
                    with st.spinner("Generando análisis con Gemini..."):
                        time.sleep(1)  # Simular tiempo de procesamiento
                        gemini_analysis = generate_gemini_analysis(selected_game)
                    
                    st.markdown(gemini_analysis)
                    
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
            
            else:
                st.warning("No se encontraron oportunidades de valor significativas para este partido.")
                st.info("Esto puede deberse a que las líneas del mercado están muy ajustadas o faltan datos de jugadores.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🏀 NBA Betting Analyzer Pro v1.0</p>
        <p>Desarrollado con FastAPI + Streamlit + NBA API</p>
        <p style="font-size: 0.8rem;">⚠️ Disclaimer: Este sistema es solo para fines educativos. 
        Las apuestas deportivas conllevan riesgos. Apuesta responsablemente.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()