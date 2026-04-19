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
async def get_todays_games(date: str = None):
    """
    Obtiene todos los partidos programados para una fecha específica.
    
    Args:
        date: Fecha en formato 'YYYY-MM-DD'. Si es None, usa la fecha actual.
    
    Returns:
        Lista de partidos con información básica
        
    Raises:
        HTTPException: Si hay error obteniendo los datos
    """
    try:
        games = nba_client.get_todays_games(date=date)
        
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


@app.get("/api/live/game/{game_id}")
async def get_live_game_stats(game_id: str):
    """
    Obtiene estadísticas en tiempo real de un partido.
    """
    try:
        stats = nba_client.get_live_game_stats(game_id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo stats en vivo: {str(e)}"
        )


@app.get("/api/analysis/{game_id}")
async def analyze_game(game_id: str, date: str = None):
    """
    Analiza un partido específico y genera sugerencias de apuestas.
    
    Args:
        game_id: ID único del partido a analizar
        date: Fecha del partido (opcional, para buscar en histórico)
        
    Returns:
        Análisis completo con mejores oportunidades de apuesta
        
    Raises:
        HTTPException: Si el partido no existe o hay error en el análisis
    """
    try:
        # Buscar información del partido
        # Si se proporciona fecha, buscar en esa fecha, si no, busca hoy
        games = nba_client.get_todays_games(date=date)
        target_game = next((g for g in games if g['game_id'] == game_id), None)
        
        if not target_game:
            # Si no se encuentra y no se especificó fecha, intentar buscar sin fecha (hoy)
            # (Aunque get_todays_games() ya hace esto por defecto si date es None)
            raise HTTPException(
                status_code=404,
                detail=f"Partido {game_id} no encontrado para la fecha {date or 'hoy'}"
            )
        
        # Realizar análisis completo
        print(f"Analizando partido: {target_game['away_team']} @ {target_game['home_team']}")
        
        best_bets = prediction_engine.analyze_game(
            game_id=game_id,
            home_team_id=target_game['home_team_id'],
            away_team_id=target_game['away_team_id'],
            game_date_utc=target_game.get('game_time')
        )
        
        # Obtener lesiones para este partido
        game_injuries = []
        try:
            injury_df = nba_client.get_injury_report()
            if not injury_df.empty:
                home_team = target_game['home_team']
                away_team = target_game['away_team']
                
                # Filtrar por nombre de equipo (contiene nickname)
                relevant_injuries = injury_df[
                    injury_df['TEAM_NAME'].str.contains(home_team, case=False, na=False) | 
                    injury_df['TEAM_NAME'].str.contains(away_team, case=False, na=False)
                ]
                game_injuries = relevant_injuries.to_dict('records')
        except Exception as e:
            print(f"Error obteniendo lesiones para respuesta: {e}")
        
        analysis = {
            "game_id": game_id,
            "home_team": target_game['home_team'],
            "away_team": target_game['away_team'],
            "game_time": target_game['game_time'],
            "best_bets": best_bets,
            "total_opportunities": len(best_bets),
            "injuries": game_injuries,
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
async def get_player_stats(player_id: int, stat_type: str = "season", last_n: int = 10):
    """
    Obtiene estadísticas detalladas de un jugador específico.
    
    Args:
        player_id: ID único del jugador
        stat_type: Tipo de estadísticas ('season', 'last5', 'last10', 'gamelog')
        last_n: Número de juegos para gamelog (default 5)
        
    Returns:
        Estadísticas del jugador según el tipo solicitado
    """
    try:
        if stat_type == "season":
            stats = nba_client.get_player_season_stats(player_id)
        elif stat_type == "gamelog":
            games = nba_client.get_player_recent_games(player_id, last_n=last_n)
            if games.empty:
                return []
            
            # Convertir a lista de diccionarios y limpiar NaNs
            games_dict = games.fillna(0).to_dict('records')
            return games_dict
            
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
                detail="stat_type debe ser 'season', 'last5', 'last10' o 'gamelog'"
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
        
        
@app.get("/api/team/{team_id}/stats")
async def get_team_stats(team_id: int):
    """
    Obtiene estadísticas generales del equipo para la temporada actual.
    
    Args:
        team_id: ID del equipo NBA
        
    Returns:
        Estadísticas ofensivas, defensivas y generales del equipo
    """
    try:
        from nba_api.stats.endpoints import leaguedashteamstats
        import time
        
        time.sleep(0.6)
        
        stats = leaguedashteamstats.LeagueDashTeamStats(
            season=nba_client.current_season,
            per_mode_detailed='PerGame'
        )
        
        df = stats.get_data_frames()[0]
        team_stats = df[df['TEAM_ID'] == team_id]
        
        if team_stats.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Equipo {team_id} no encontrado"
            )
        
        row = team_stats.iloc[0]
        
        return {
            "team_id": team_id,
            "team_name": row.get('TEAM_NAME', 'Unknown'),
            "wins": int(row.get('W', 0)),
            "losses": int(row.get('L', 0)),
            "win_pct": round(float(row.get('W_PCT', 0)), 3),
            "pts_per_game": round(float(row.get('PTS', 0)), 1),
            "reb_per_game": round(float(row.get('REB', 0)), 1),
            "ast_per_game": round(float(row.get('AST', 0)), 1),
            "fg_pct": round(float(row.get('FG_PCT', 0)), 3),
            "fg3_pct": round(float(row.get('FG3_PCT', 0)), 3),
            "pts_allowed": round(float(row.get('PTS', 0)), 1),  # Aprox, requeriría endpoint defensivo
            "season": nba_client.current_season
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas del equipo: {str(e)}"
        )
 
 
@app.get("/api/team/{team_id}/recent-games")
async def get_team_recent_games(team_id: int, last_n: int = 5):
    """
    Obtiene los últimos N partidos de un equipo.
    
    Args:
        team_id: ID del equipo NBA
        last_n: Número de partidos a retornar (default 5)
        
    Returns:
        Lista de diccionarios con información de los últimos partidos
    """
    try:
        from nba_api.stats.endpoints import teamgamelogs
        import time
        
        time.sleep(0.6)
        
        game_logs = teamgamelogs.TeamGameLogs(
            season_nullable=nba_client.current_season,
            team_id_nullable=team_id
        )
        
        df = game_logs.get_data_frames()[0]
        
        if df.empty:
            return {"team_id": team_id, "games": []}
        
        # Tomar los últimos N partidos
        recent = df.head(last_n)
        
        games = []
        for _, row in recent.iterrows():
            # Determinar W/L
            result = "W" if row['WL'] == 'W' else "L"
            pts_for = int(row.get('PTS', 0))
            plus_minus = int(row.get('PLUS_MINUS', 0))
            pts_against = pts_for - plus_minus
            
            games.append({
                "game_id": row.get('Game_ID', ''),
                "date": row.get('GAME_DATE', ''),
                "matchup": row.get('MATCHUP', ''),
                "result": f"{result} {pts_for}-{pts_against}",
                "pts": pts_for,
                "reb": int(row.get('REB', 0)),
                "ast": int(row.get('AST', 0)),
                "fg_pct": round(float(row.get('FG_PCT', 0)), 3),
                "fg3m": int(row.get('FG3M', 0)),
                "to": int(row.get('TOV', 0))
            })
        
        return {
            "team_id": team_id,
            "games": games,
            "total": len(games)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo partidos recientes del equipo: {str(e)}"
        )
 
 
@app.get("/api/h2h")
async def get_h2h_history(home_team_id: int, away_team_id: int, last_n: int = 10):
    """
    Obtiene el historial de enfrentamientos (H2H) entre dos equipos.
    
    Args:
        home_team_id: ID del equipo local
        away_team_id: ID del equipo visitante
        last_n: Número de enfrentamientos a retornar (default 10)
        
    Returns:
        Historial H2H con resultados y estadísticas
    """
    try:
        from nba_api.stats.endpoints import leaguegamefinder
        import time
        
        time.sleep(0.6)
        
        # Obtener todos los partidos del equipo local
        game_finder = leaguegamefinder.LeagueGameFinder(
            season_nullable=nba_client.current_season,
            team_id_nullable=home_team_id
        )
        
        df = game_finder.get_data_frames()[0]
        if df.empty:
            return {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "matchups": [],
                "away_wins": 0,
                "home_wins": 0,
                "total_matchups": 0
            }

        teams_map = {t['id']: t for t in nba_client.teams_data}
        away_abbr = teams_map.get(away_team_id, {}).get('abbreviation', '').upper()
        
        # Filtrar H2H de forma robusta: preferir OPPONENT_TEAM_ID si existe,
        # de lo contrario usar MATCHUP + abreviatura del rival.
        if 'OPPONENT_TEAM_ID' in df.columns:
            h2h = df[df['OPPONENT_TEAM_ID'] == away_team_id].head(last_n)
        elif away_abbr and 'MATCHUP' in df.columns:
            h2h = df[df['MATCHUP'].astype(str).str.contains(away_abbr, na=False)].head(last_n)
        else:
            h2h = df.head(0)
        
        if h2h.empty:
            return {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "matchups": [],
                "away_wins": 0,
                "home_wins": 0,
                "total_matchups": 0
            }
        
        matchups = []
        away_wins = 0
        home_wins = 0
        
        for _, row in h2h.iterrows():
            result = "W" if row['WL'] == 'W' else "L"
            
            # El DataFrame está en la perspectiva del equipo local (home_team_id)
            if result == "W":
                home_wins += 1
            else:
                away_wins += 1

            matchup_text = str(row.get('MATCHUP', ''))
            if 'vs.' in matchup_text:
                location = "HOME"
            elif '@' in matchup_text:
                location = "AWAY"
            else:
                location = "UNKNOWN"

            pts_for = int(row.get('PTS', 0))
            plus_minus = int(row.get('PLUS_MINUS', 0))
            pts_against = pts_for - plus_minus
            
            matchups.append({
                "date": row.get('GAME_DATE', ''),
                "matchup": matchup_text,
                "result": result,
                "pts_for": pts_for,
                "pts_against": pts_against,
                "location": location
            })
        
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "matchups": matchups,
            "away_wins": away_wins,
            "home_wins": home_wins,
            "total_matchups": len(matchups),
            "away_win_pct": round(away_wins / len(matchups) * 100, 1) if matchups else 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial H2H: {str(e)}"
        )
 
 
@app.get("/api/game/{game_id}/preview")
async def get_game_preview(game_id: str):
    """
    Obtiene una vista previa completa del partido con estadísticas de ambos equipos.
    
    Args:
        game_id: ID único del partido
        
    Returns:
        Objeto con información consolidada del partido
    """
    try:
        # Obtener info del partido
        games = nba_client.get_todays_games()
        target_game = next((g for g in games if g['game_id'] == game_id), None)
        
        if not target_game:
            raise HTTPException(
                status_code=404,
                detail=f"Partido {game_id} no encontrado"
            )
        
        home_id = target_game['home_team_id']
        away_id = target_game['away_team_id']
        
        # Obtener estadísticas de ambos equipos
        home_stats_resp = await get_team_stats(home_id)
        away_stats_resp = await get_team_stats(away_id)
        
        # Obtener últimos partidos
        home_recent_resp = await get_team_recent_games(home_id, last_n=5)
        away_recent_resp = await get_team_recent_games(away_id, last_n=5)
        
        # Obtener H2H
        h2h_resp = await get_h2h_history(home_id, away_id, last_n=10)
        
        return {
            "game_id": game_id,
            "game_info": {
                "home_team": target_game['home_team'],
                "away_team": target_game['away_team'],
                "game_time": target_game.get('game_time'),
                "game_status": target_game.get('game_status')
            },
            "home_team": home_stats_resp,
            "away_team": away_stats_resp,
            "home_recent_games": home_recent_resp.get('games', []),
            "away_recent_games": away_recent_resp.get('games', []),
            "h2h": h2h_resp,
            "preview_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo vista previa del partido: {str(e)}"
        )


# Ejecutar servidor
if __name__ == "__main__":
    print("🏀 Iniciando NBA Betting Analysis API...")
    print("📊 Servidor corriendo en: http://localhost:8000")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )