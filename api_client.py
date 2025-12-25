"""
api_client.py
Módulo para conexión con la API de NBA y obtención de datos en tiempo real.
Maneja la sincronización diaria de partidos, estadísticas de jugadores y reportes de lesiones.
"""

from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import (
    leaguegamefinder, playergamelogs, commonplayerinfo,
    leaguedashplayerstats, teamgamelogs, scoreboardv2
)
from nba_api.stats.static import teams, players
from datetime import datetime, timedelta
import pandas as pd
import time
import requests
from typing import Dict, List, Optional


class NBADataClient:
    """Cliente para interactuar con la API de NBA y obtener datos estructurados."""
    
    def __init__(self):
        self.current_season = "2024-25"
        self.teams_data = teams.get_teams()
        self.players_data = players.get_players()
        
        # Cache para reducir llamadas a la API
        self._season_stats_cache = {}
        self._recent_games_cache = {}
        self._defense_cache = {}
        
    def _get_all_players_stats(self) -> pd.DataFrame:
        """
        Obtiene estadísticas de TODOS los jugadores de una vez.
        Esto es mucho más eficiente que hacer llamadas individuales.
        """
        cache_key = f"all_players_{self.current_season}"
        
        if cache_key in self._season_stats_cache:
            return self._season_stats_cache[cache_key]
        
        try:
            time.sleep(0.6)
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=self.current_season,
                per_mode_detailed='PerGame'
            )
            df = stats.get_data_frames()[0]
            self._season_stats_cache[cache_key] = df
            return df
        except Exception as e:
            print(f"Error obteniendo estadísticas de todos los jugadores: {e}")
            return pd.DataFrame()
        
    def get_todays_games(self, date: str = None) -> List[Dict]:
        """
        Obtiene todos los partidos programados para una fecha específica.
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD'. Si es None, usa la fecha actual.
        
        Returns:
            Lista de diccionarios con información de cada partido:
            - game_id: ID único del partido
            - home_team: Equipo local
            - away_team: Equipo visitante
            - game_time: Hora del partido
            - home_team_id: ID del equipo local
            - away_team_id: ID del equipo visitante
        """
        try:
            # Si no se especifica fecha, usar la actual
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            print(f"📅 Buscando partidos para: {date}")
            
            # Verificar si es la fecha de hoy para usar endpoint en vivo
            today = datetime.now().strftime('%Y-%m-%d')
            
            if date == today:
                # Obtener scoreboard en vivo (mejor para el día actual)
                board = scoreboard.ScoreBoard()
                games = board.games.get_dict()
                
                todays_games = []
                for game in games:
                    game_info = {
                        'game_id': game['gameId'],
                        'home_team': game['homeTeam']['teamName'],
                        'away_team': game['awayTeam']['teamName'],
                        'game_time': game.get('gameTimeUTC', 'TBD'),
                        'home_team_id': game['homeTeam']['teamId'],
                        'away_team_id': game['awayTeam']['teamId'],
                        'home_team_tricode': game['homeTeam']['teamTricode'],
                        'away_team_tricode': game['awayTeam']['teamTricode']
                    }
                    todays_games.append(game_info)
                return todays_games
            
            else:
                # Usar ScoreboardV2 para fechas pasadas o futuras
                board = scoreboardv2.ScoreboardV2(game_date=date)
                games_header = board.game_header.get_dict()
                
                # Mapa de equipos para buscar nombres por ID
                teams_map = {t['id']: t for t in self.teams_data}
                
                todays_games = []
                
                # Indices de columnas en GameHeader
                headers = games_header['headers']
                if not games_header['data']:
                    return []
                    
                idx_game_id = headers.index('GAME_ID')
                idx_home_id = headers.index('HOME_TEAM_ID')
                idx_away_id = headers.index('VISITOR_TEAM_ID')
                idx_status = headers.index('GAME_STATUS_TEXT')
                
                for row in games_header['data']:
                    home_id = row[idx_home_id]
                    away_id = row[idx_away_id]
                    
                    home_team_info = teams_map.get(home_id, {})
                    away_team_info = teams_map.get(away_id, {})
                    
                    game_info = {
                        'game_id': row[idx_game_id],
                        'home_team': home_team_info.get('nickname', 'Unknown'), # Usamos nickname (ej. Lakers) para consistencia
                        'away_team': away_team_info.get('nickname', 'Unknown'),
                        'game_time': row[idx_status],
                        'home_team_id': home_id,
                        'away_team_id': away_id,
                        'home_team_tricode': home_team_info.get('abbreviation', ''),
                        'away_team_tricode': away_team_info.get('abbreviation', '')
                    }
                    todays_games.append(game_info)
                
                return todays_games
            
        except Exception as e:
            print(f"Error obteniendo partidos del día: {e}")
            return []
    
    def get_injury_report(self) -> pd.DataFrame:
        """
        Obtiene el reporte de lesiones actualizado.
        
        Nota: La NBA API oficial no tiene endpoint de lesiones actualizado.
        Esta función retorna un DataFrame vacío. Para producción, considera
        integrar APIs como:
        - ESPN API
        - RotoWire
        - FantasyData
        
        Returns:
            DataFrame vacío (para evitar errores, asume que todos juegan)
        """
        try:
            # Método alternativo: usar el scoreboard en vivo para detectar inactivos
            board = scoreboard.ScoreBoard()
            games = board.games.get_dict()
            
            injured_players = []
            
            for game in games:
                # Verificar jugadores inactivos del equipo local
                if 'homeTeam' in game and 'inactives' in game['homeTeam']:
                    for player in game['homeTeam']['inactives']:
                        injured_players.append({
                            'PLAYER_NAME': player.get('name', 'Unknown'),
                            'PLAYER_ID': player.get('personId', 0),
                            'TEAM_ID': game['homeTeam'].get('teamId', 0),
                            'Current_Status': 'Out',
                            'Comment': 'Inactive for today\'s game'
                        })
                
                # Verificar jugadores inactivos del equipo visitante
                if 'awayTeam' in game and 'inactives' in game['awayTeam']:
                    for player in game['awayTeam']['inactives']:
                        injured_players.append({
                            'PLAYER_NAME': player.get('name', 'Unknown'),
                            'PLAYER_ID': player.get('personId', 0),
                            'TEAM_ID': game['awayTeam'].get('teamId', 0),
                            'Current_Status': 'Out',
                            'Comment': 'Inactive for today\'s game'
                        })
            
            if injured_players:
                return pd.DataFrame(injured_players)
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Info: No se pudo obtener reporte de lesiones detallado: {e}")
            print("Asumiendo que todos los jugadores están disponibles...")
            return pd.DataFrame()
    
    def get_player_season_stats(self, player_id: int) -> Dict:
        """
        Obtiene las estadísticas promedio de la temporada actual para un jugador.
        Usa cache para evitar llamadas repetidas a la API.
        
        Args:
            player_id: ID único del jugador
            
        Returns:
            Diccionario con promedios de PTS, REB, AST, FG3M, etc.
        """
        try:
            # Verificar cache individual
            if player_id in self._season_stats_cache:
                return self._season_stats_cache[player_id]
            
            # Obtener estadísticas de todos los jugadores (más eficiente)
            all_stats = self._get_all_players_stats()
            
            if all_stats.empty:
                return {}
            
            player_stats = all_stats[all_stats['PLAYER_ID'] == player_id]
            
            if player_stats.empty:
                return {}
            
            stats_dict = {
                'player_name': player_stats['PLAYER_NAME'].values[0],
                'team': player_stats['TEAM_ABBREVIATION'].values[0],
                'gp': player_stats['GP'].values[0],
                'pts': player_stats['PTS'].values[0],
                'reb': player_stats['REB'].values[0],
                'ast': player_stats['AST'].values[0],
                'fg3m': player_stats['FG3M'].values[0],
                'fg_pct': player_stats['FG_PCT'].values[0],
                'fg3_pct': player_stats['FG3_PCT'].values[0],
                'min': player_stats['MIN'].values[0]
            }
            
            # Guardar en cache
            self._season_stats_cache[player_id] = stats_dict
            
            return stats_dict
            
        except Exception as e:
            print(f"Error obteniendo estadísticas de temporada para jugador {player_id}: {e}")
            return {}
    
    def get_player_recent_games(self, player_id: int, last_n: int = 10) -> pd.DataFrame:
        """
        Obtiene los últimos N partidos de un jugador para análisis de tendencias.
        Usa cache para evitar llamadas repetidas.
        
        Args:
            player_id: ID del jugador
            last_n: Número de partidos recientes a obtener (5 o 10 recomendado)
            
        Returns:
            DataFrame con estadísticas de los últimos N juegos
        """
        cache_key = f"{player_id}_{last_n}"
        
        if cache_key in self._recent_games_cache:
            return self._recent_games_cache[cache_key]
        
        try:
            time.sleep(0.6)
            game_logs = playergamelogs.PlayerGameLogs(
                season_nullable=self.current_season,
                player_id_nullable=player_id
            )
            
            df = game_logs.get_data_frames()[0]
            
            # Ordenar por fecha y tomar los últimos N
            df = df.sort_values('GAME_DATE', ascending=False).head(last_n)
            
            # Guardar en cache
            self._recent_games_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            print(f"Error obteniendo juegos recientes para jugador {player_id}: {e}")
            return pd.DataFrame()
    
    def check_back_to_back(self, team_id: int, game_date_utc: str = None) -> bool:
        """
        Verifica si un equipo jugó el día anterior al partido en cuestión.
        
        Args:
            team_id: ID del equipo
            game_date_utc: Fecha del partido actual en UTC (ISO format). 
                           Si es None, usa la fecha actual.
            
        Returns:
            True si el equipo jugó el día anterior, False en caso contrario
        """
        try:
            time.sleep(0.6)
            
            # Determinar la fecha de referencia (día del partido) en ET
            if game_date_utc:
                try:
                    # Parsear UTC y convertir a ET
                    utc_time = pd.to_datetime(game_date_utc)
                    if utc_time.tz is None:
                        utc_time = utc_time.tz_localize('UTC')
                    
                    et_time = utc_time.tz_convert('America/New_York')
                    reference_date = et_time.floor('D').tz_localize(None)
                except Exception as e:
                    print(f"Error parseando fecha {game_date_utc}: {e}")
                    reference_date = pd.Timestamp.now(tz='America/New_York').floor('D').tz_localize(None)
            else:
                reference_date = pd.Timestamp.now(tz='America/New_York').floor('D').tz_localize(None)

            game_logs = teamgamelogs.TeamGameLogs(
                season_nullable=self.current_season,
                team_id_nullable=team_id
            )
            
            df = game_logs.get_data_frames()[0]
            if df.empty:
                return False
            
            # Convertir GAME_DATE a datetime objects (pandas Timestamp)
            # GAME_DATE suele ser local/ET, así que lo tratamos como naive
            df['GAME_DATE_DT'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
            
            # Calcular diferencia en días
            df['DAYS_DIFF'] = (reference_date - df['GAME_DATE_DT']).dt.days
            
            # Si la diferencia es 1, jugaron ayer.
            # Nota: Si la diferencia es 0, es el partido de hoy (si ya está en los logs, que a veces pasa si ya empezó)
            yesterday_games = df[df['DAYS_DIFF'] == 1]
            
            return not yesterday_games.empty
            
        except Exception as e:
            print(f"Error verificando back-to-back para equipo {team_id}: {e}")
            return False
    
    def get_team_defensive_rating(self, team_id: int) -> Dict:
        """
        Obtiene el rating defensivo de un equipo por posición.
        Útil para ajustar proyecciones según el oponente.
        Usa cache para evitar llamadas repetidas.
        
        Args:
            team_id: ID del equipo
            
        Returns:
            Diccionario con ratings defensivos por categoría
        """
        if team_id in self._defense_cache:
            return self._defense_cache[team_id]
        
        try:
            time.sleep(0.6)
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=self.current_season,
                per_mode_detailed='PerGame',
                team_id_nullable=team_id
            )
            
            df = stats.get_data_frames()[0]
            
            # Calcular promedios permitidos
            defensive_stats = {
                'pts_allowed': df['PTS'].mean(),
                'reb_allowed': df['REB'].mean(),
                'ast_allowed': df['AST'].mean(),
                'fg3m_allowed': df['FG3M'].mean()
            }
            
            # Guardar en cache
            self._defense_cache[team_id] = defensive_stats
            
            return defensive_stats
            
        except Exception as e:
            print(f"Error obteniendo rating defensivo para equipo {team_id}: {e}")
            return {}
    
    def get_active_players_for_game(self, home_team_id: int, away_team_id: int) -> Dict[str, List[int]]:
        """
        Obtiene los jugadores activos (no lesionados) de ambos equipos para un partido.
        
        Args:
            home_team_id: ID del equipo local
            away_team_id: ID del equipo visitante
            
        Returns:
            Diccionario con listas de IDs de jugadores activos por equipo
        """
        try:
            # Obtener reporte de lesiones
            injury_df = self.get_injury_report()
            
            # Obtener todos los jugadores de ambos equipos
            time.sleep(0.6)
            home_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=self.current_season,
                team_id_nullable=home_team_id
            )
            home_df = home_stats.get_data_frames()[0]
            
            time.sleep(0.6)
            away_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=self.current_season,
                team_id_nullable=away_team_id
            )
            away_df = away_stats.get_data_frames()[0]
            
            # Filtrar jugadores OUT
            injured_players = set()
            if not injury_df.empty:
                if 'Current_Status' in injury_df.columns:
                    out_players = injury_df[injury_df['Current_Status'] == 'Out']
                    if 'PLAYER_NAME' in out_players.columns:
                        injured_players = set(out_players['PLAYER_NAME'].values)
                elif 'PLAYER_NAME' in injury_df.columns:
                    # Si no hay columna de estado, asumir que todos en la lista están out
                    injured_players = set(injury_df['PLAYER_NAME'].values)
            
            # Filtrar jugadores activos (no lesionados y con minutos significativos)
            home_active = home_df[
                (~home_df['PLAYER_NAME'].isin(injured_players)) & 
                (home_df['MIN'] > 10)  # Mínimo 10 minutos promedio (reducido de 15)
            ]['PLAYER_ID'].tolist()
            
            away_active = away_df[
                (~away_df['PLAYER_NAME'].isin(injured_players)) & 
                (away_df['MIN'] > 10)
            ]['PLAYER_ID'].tolist()
            
            # Si no hay jugadores activos, tomar los top jugadores por minutos
            if not home_active:
                home_active = home_df.nlargest(10, 'MIN')['PLAYER_ID'].tolist()
            
            if not away_active:
                away_active = away_df.nlargest(10, 'MIN')['PLAYER_ID'].tolist()
            
            return {
                'home': home_active,
                'away': away_active
            }
            
        except Exception as e:
            print(f"Error obteniendo jugadores activos: {e}")
            print("Retornando listas vacías - se reintentará...")
            return {'home': [], 'away': []}