"""
main.py
Backend FastAPI para el sistema de análisis de apuestas NBA.
Expone endpoints REST para obtener partidos, análisis y predicciones.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uvicorn

from api_client import NBADataClient
from engine import NBAPredictionEngine

# Inicializar FastAPI
app = FastAPI(
    title="NBA Betting Analysis API",
    description="API para análisis y predicciones de apuestas NBA en tiempo real",
    version="1.0.0"
)

# Configurar CORS para permitir requests desde Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar clientes
nba_client = NBADataClient()
prediction_engine = NBAPredictionEngine()


# Modelos Pydantic para validación de datos
class GameInfo(BaseModel):
    """Modelo para información básica de un partido."""
    game_id: str
    home_team: str
    away_team: str
    game_time: str
    home_team_id: int
    away_team_id: int


class BetSuggestion(BaseModel):
    """Modelo para una sugerencia de apuesta."""
    player_name: str
    stat_type: str
    our_projection: float
    betting_line: float
    difference: float
    edge_percentage: float
    recommended_bet: str
    confidence: float
    final_rating: float


class GameAnalysis(BaseModel):
    """Modelo para análisis completo de un partido."""
    game_id: str
    home_team: str
    away_team: str
    best_bets: List[Dict]
    total_opportunities: int
    analysis_timestamp: str


@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "service": "NBA Betting Analysis API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "games": "/api/games/today",
            "analysis": "/api/analysis/{game_id}",
            "player_stats": "/api/player/{player_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud del servicio."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/games/today", response_model=List[GameInfo])
async def get_todays_games():
    """
    Obtiene todos los partidos programados para hoy.
    
    Returns:
        Lista de partidos con información básica
        
    Raises:
        HTTPException: Si hay error obteniendo los datos
    """
    try:
        games = nba_client.get_todays_games()
        
        if not games:
            return []
        
        # Formatear respuesta
        formatted_games = []
        for game in games:
            formatted_games.append(GameInfo(
                game_id=game['game_id'],
                home_team=game['home_team'],
                away_team=game['away_team'],
                game_time=game['game_time'],
                home_team_id=game['home_team_id'],
                away_team_id=game['away_team_id']
            ))
        
        return formatted_games
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo partidos del día: {str(e)}"
        )


@app.get("/api/analysis/{game_id}")
async def analyze_game(game_id: str):
    """
    Analiza un partido específico y genera sugerencias de apuestas.
    
    Args:
        game_id: ID único del partido a analizar
        
    Returns:
        Análisis completo con mejores oportunidades de apuesta
        
    Raises:
        HTTPException: Si el partido no existe o hay error en el análisis
    """
    try:
        # Buscar información del partido
        games = nba_client.get_todays_games()
        target_game = next((g for g in games if g['game_id'] == game_id), None)
        
        if not target_game:
            raise HTTPException(
                status_code=404,
                detail=f"Partido {game_id} no encontrado"
            )
        
        # Realizar análisis completo
        print(f"Analizando partido: {target_game['away_team']} @ {target_game['home_team']}")
        
        best_bets = prediction_engine.analyze_game(
            game_id=game_id,
            home_team_id=target_game['home_team_id'],
            away_team_id=target_game['away_team_id']
        )
        
        analysis = {
            "game_id": game_id,
            "home_team": target_game['home_team'],
            "away_team": target_game['away_team'],
            "game_time": target_game['game_time'],
            "best_bets": best_bets,
            "total_opportunities": len(best_bets),
            "analysis_timestamp": datetime.now().isoformat(),
            "top_3_summary": best_bets[:3] if len(best_bets) >= 3 else best_bets
        }
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando partido: {str(e)}"
        )


@app.get("/api/player/{player_id}")
async def get_player_stats(player_id: int, stat_type: str = "season"):
    """
    Obtiene estadísticas detalladas de un jugador específico.
    
    Args:
        player_id: ID único del jugador
        stat_type: Tipo de estadísticas ('season', 'last5', 'last10')
        
    Returns:
        Estadísticas del jugador según el tipo solicitado
    """
    try:
        if stat_type == "season":
            stats = nba_client.get_player_season_stats(player_id)
        elif stat_type in ["last5", "last10"]:
            n = 5 if stat_type == "last5" else 10
            games = nba_client.get_player_recent_games(player_id, last_n=n)
            
            if games.empty:
                return {"error": "No hay datos disponibles"}
            
            stats = {
                "player_id": player_id,
                "games_analyzed": len(games),
                "avg_pts": round(games['PTS'].mean(), 2) if 'PTS' in games.columns else 0,
                "avg_reb": round(games['REB'].mean(), 2) if 'REB' in games.columns else 0,
                "avg_ast": round(games['AST'].mean(), 2) if 'AST' in games.columns else 0,
                "avg_fg3m": round(games['FG3M'].mean(), 2) if 'FG3M' in games.columns else 0,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="stat_type debe ser 'season', 'last5' o 'last10'"
            )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas del jugador: {str(e)}"
        )


@app.get("/api/injury-report")
async def get_injury_report():
    """
    Obtiene el reporte actualizado de lesiones de la NBA.
    
    Returns:
        Lista de jugadores lesionados con su estado
    """
    try:
        injury_df = nba_client.get_injury_report()
        
        if injury_df.empty:
            return {"injuries": [], "total": 0}
        
        # Convertir DataFrame a lista de diccionarios
        injuries = injury_df.to_dict('records')
        
        return {
            "injuries": injuries,
            "total": len(injuries),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo reporte de lesiones: {str(e)}"
        )


@app.post("/api/custom-analysis")
async def custom_player_analysis(
    player_id: int,
    opponent_team_id: int,
    stat_types: List[str],
    back_to_back: bool = False
):
    """
    Realiza un análisis personalizado para un jugador específico.
    
    Args:
        player_id: ID del jugador a analizar
        opponent_team_id: ID del equipo oponente
        stat_types: Lista de tipos de estadísticas a proyectar ['PRA', 'PTS', 'FG3M', etc.]
        back_to_back: Si el equipo está en situación de partidos consecutivos
        
    Returns:
        Proyecciones personalizadas para las estadísticas solicitadas
    """
    try:
        results = {}
        
        for stat in stat_types:
            if stat == 'PRA':
                projection = prediction_engine.calculate_pra_projection(
                    player_id, opponent_team_id, back_to_back
                )
            elif stat == 'PTS':
                projection = prediction_engine.calculate_points_projection(
                    player_id, opponent_team_id, back_to_back
                )
            elif stat == 'FG3M':
                projection = prediction_engine.calculate_threes_projection(
                    player_id, opponent_team_id, back_to_back
                )
            else:
                continue
            
            if projection:
                results[stat] = projection
        
        return {
            "player_id": player_id,
            "opponent_team_id": opponent_team_id,
            "projections": results,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis personalizado: {str(e)}"
        )


# Ejecutar servidor
if __name__ == "__main__":
    print("🏀 Iniciando NBA Betting Analysis API...")
    print("📊 Servidor corriendo en: http://localhost:8000")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )