"""
main.py
Backend FastAPI para el sistema de análisis de apuestas NBA.
Expone endpoints REST para obtener partidos, análisis y predicciones.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import uvicorn

from api_client import NBADataClient
from engine import NBAPredictionEngine


def _season_from_date(date_str: Optional[str]) -> str:
    """Calcula temporada NBA (YYYY-YY) a partir de una fecha ISO; cae a temporada actual si falla."""
    if not date_str:
        return nba_client.current_season
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.month >= 10:
            start_year = dt.year
            end_year = (dt.year + 1) % 100
        else:
            start_year = dt.year - 1
            end_year = dt.year % 100
        return f"{start_year}-{end_year:02d}"
    except Exception:
        return nba_client.current_season

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


@lru_cache(maxsize=128)
def _get_team_stats_cached(team_id: int, season: str) -> Dict:
    from nba_api.stats.endpoints import leaguedashteamstats
    import time

    time.sleep(0.6)

    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
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
        "pts_allowed": round(float(row.get('PTS', 0)), 1),
        "season": season,
    }


@lru_cache(maxsize=256)
def _get_team_recent_games_cached(team_id: int, last_n: int, as_of_date: str, season: str) -> Dict:
    from nba_api.stats.endpoints import teamgamelogs
    import time

    time.sleep(0.6)

    game_logs = teamgamelogs.TeamGameLogs(
        season_nullable=season,
        team_id_nullable=team_id
    )

    df = game_logs.get_data_frames()[0]
    if df.empty:
        return {"team_id": team_id, "games": [], "total": 0}

    if 'GAME_DATE' in df.columns:
        df = df.copy()
        df['GAME_DATE_DT'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
        if as_of_date:
            cutoff = pd.to_datetime(as_of_date, errors='coerce')
            if pd.notna(cutoff):
                df = df[df['GAME_DATE_DT'].notna() & (df['GAME_DATE_DT'] < cutoff)]
        df = df.sort_values('GAME_DATE_DT', ascending=False)

    recent = df.head(last_n)

    games = []
    for _, row in recent.iterrows():
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

    return {"team_id": team_id, "games": games, "total": len(games)}


@lru_cache(maxsize=256)
def _get_h2h_history_cached(home_team_id: int, away_team_id: int, last_n: int, as_of_date: str, season: str) -> Dict:
    from nba_api.stats.endpoints import leaguegamefinder
    import time

    time.sleep(0.6)

    game_finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
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
            "total_matchups": 0,
        }

    teams_map = {t['id']: t for t in nba_client.teams_data}
    home_abbr = teams_map.get(home_team_id, {}).get('abbreviation', '').upper()
    away_abbr = teams_map.get(away_team_id, {}).get('abbreviation', '').upper()

    if 'GAME_DATE' in df.columns:
        df = df.copy()
        df['GAME_DATE_DT'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
        if as_of_date:
            cutoff = pd.to_datetime(as_of_date, errors='coerce')
            if pd.notna(cutoff):
                df = df[df['GAME_DATE_DT'].notna() & (df['GAME_DATE_DT'] < cutoff)]
        df = df.sort_values('GAME_DATE_DT', ascending=False)

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
            "total_matchups": 0,
        }

    away_reb_by_game = {}
    away_finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        team_id_nullable=away_team_id
    )
    away_df = away_finder.get_data_frames()[0]
    if not away_df.empty:
        if 'GAME_DATE' in away_df.columns:
            away_df = away_df.copy()
            away_df['GAME_DATE_DT'] = pd.to_datetime(away_df['GAME_DATE'], errors='coerce')
            if as_of_date:
                cutoff = pd.to_datetime(as_of_date, errors='coerce')
                if pd.notna(cutoff):
                    away_df = away_df[away_df['GAME_DATE_DT'].notna() & (away_df['GAME_DATE_DT'] < cutoff)]

        if 'OPPONENT_TEAM_ID' in away_df.columns:
            away_h2h = away_df[away_df['OPPONENT_TEAM_ID'] == home_team_id]
        elif home_abbr and 'MATCHUP' in away_df.columns:
            away_h2h = away_df[away_df['MATCHUP'].astype(str).str.contains(home_abbr, na=False)]
        else:
            away_h2h = away_df.head(0)

        for _, away_row in away_h2h.iterrows():
            away_game_id = away_row.get('GAME_ID') or away_row.get('Game_ID')
            if away_game_id:
                away_reb_by_game[str(away_game_id)] = int(away_row.get('REB', 0))

    matchups = []
    away_wins = 0
    home_wins = 0

    for _, row in h2h.iterrows():
        result = "W" if row['WL'] == 'W' else "L"
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
        home_reb = int(row.get('REB', 0))
        game_id = row.get('GAME_ID') or row.get('Game_ID')
        away_reb = away_reb_by_game.get(str(game_id)) if game_id else None

        matchups.append({
            "date": row.get('GAME_DATE', ''),
            "matchup": matchup_text,
            "result": result,
            "pts_for": pts_for,
            "pts_against": pts_against,
            "reb_home": home_reb,
            "reb_away": away_reb,
            "location": location,
        })

    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "matchups": matchups,
        "away_wins": away_wins,
        "home_wins": home_wins,
        "total_matchups": len(matchups),
        "away_win_pct": round(away_wins / len(matchups) * 100, 1) if matchups else 0,
    }


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
        return _get_team_stats_cached(team_id, nba_client.current_season)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas del equipo: {str(e)}"
        )
 
 
@app.get("/api/team/{team_id}/recent-games")
async def get_team_recent_games(team_id: int, last_n: int = 5, as_of_date: str = None):
    """
    Obtiene los últimos N partidos de un equipo.
    
    Args:
        team_id: ID del equipo NBA
        last_n: Número de partidos a retornar (default 5)
        
    Returns:
        Lista de diccionarios con información de los últimos partidos
    """
    try:
        target_season = _season_from_date(as_of_date)
        return _get_team_recent_games_cached(team_id, last_n, as_of_date or "", target_season)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo partidos recientes del equipo: {str(e)}"
        )
 
 
@app.get("/api/h2h")
async def get_h2h_history(home_team_id: int, away_team_id: int, last_n: int = 10, as_of_date: str = None):
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
        target_season = _season_from_date(as_of_date)
        return _get_h2h_history_cached(home_team_id, away_team_id, last_n, as_of_date or "", target_season)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo historial H2H: {str(e)}"
        )
 
 
@app.get("/api/game/{game_id}/preview")
async def get_game_preview(game_id: str, date: str = None):
    """
    Obtiene una vista previa completa del partido con estadísticas de ambos equipos.
    
    Args:
        game_id: ID único del partido
        
    Returns:
        Objeto con información consolidada del partido
    """
    try:
        # Obtener info del partido
        games = nba_client.get_todays_games(date=date)
        target_game = next((g for g in games if g['game_id'] == game_id), None)
        
        if not target_game:
            raise HTTPException(
                status_code=404,
                detail=f"Partido {game_id} no encontrado"
            )
        
        home_id = target_game['home_team_id']
        away_id = target_game['away_team_id']
        target_season = _season_from_date(date)
        target_as_of_date = date or ""
        
        # Obtener datos consolidados usando cachés locales
        home_stats_resp = _get_team_stats_cached(home_id, target_season)
        away_stats_resp = _get_team_stats_cached(away_id, target_season)
        home_recent_resp = _get_team_recent_games_cached(home_id, 5, target_as_of_date, target_season)
        away_recent_resp = _get_team_recent_games_cached(away_id, 5, target_as_of_date, target_season)
        h2h_resp = _get_h2h_history_cached(home_id, away_id, 10, target_as_of_date, target_season)
        injury_df = nba_client.get_injury_report()
        game_injuries = []
        if not injury_df.empty:
            home_team = target_game['home_team']
            away_team = target_game['away_team']
            relevant_injuries = injury_df[
                injury_df['TEAM_NAME'].str.contains(home_team, case=False, na=False) |
                injury_df['TEAM_NAME'].str.contains(away_team, case=False, na=False)
            ]
            game_injuries = relevant_injuries.to_dict('records')
        
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
            "injuries": game_injuries,
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
    print("Iniciando NBA Betting Analysis API...")
    print("Servidor corriendo en: http://localhost:8000")
    print("Documentación disponible en: http://localhost:8000/docs")
    
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
    
