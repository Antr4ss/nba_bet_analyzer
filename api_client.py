"""
api_client.py
Módulo para conexión con la API de NBA y obtención de datos en tiempo real.
Maneja la sincronización diaria de partidos, estadísticas de jugadores y reportes de lesiones.
"""

from nba_api.live.nba.endpoints import scoreboard, boxscore
from nba_api.stats.endpoints import (
    leaguegamefinder, playergamelogs, commonplayerinfo,
    leaguedashplayerstats, teamgamelogs, scoreboardv2, commonteamroster
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
        # Calcular temporada actual dinámicamente
        # Si estamos en oct/nov/dic, la temporada empezó este año. Si no, empezó el año pasado.
        now = datetime.now()
        if now.month >= 10:
            start_year = now.year
            end_year = (now.year + 1) % 100
        else:
            start_year = now.year - 1
            end_year = now.year % 100
            
        self.current_season = f"{start_year}-{end_year:02d}"
        print(f"ℹ️ Temporada detectada: {self.current_season}")
        
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
            
            # Usamos ScoreboardV2 para todas las fechas (pasadas, presentes y futuras)
            # El endpoint 'scoreboard' (live) a veces devuelve lista vacía temprano en el día
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
        Obtiene el reporte de lesiones actualizado usando la API de ESPN.
        
        Returns:
            DataFrame con columnas: PLAYER_NAME, Current_Status, Comment
        """
        try:
            print("🏥 Consultando reporte de lesiones (ESPN)...")
            url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            injured_players = []
            
            # Mapeo de estados de ESPN a nuestros estados
            status_map = {
                'Out': 'Out',
                'Day-to-Day': 'Day-To-Day',
                'Questionable': 'Questionable',
                'Doubtful': 'Doubtful',
                'Probable': 'Probable'
            }
            
            # Iterar sobre partidos para encontrar equipos
            for event in data.get('events', []):
                for competition in event.get('competitions', []):
                    for competitor in competition.get('competitors', []):
                        team_id = competitor.get('id')
                        team_name = competitor.get('team', {}).get('displayName')
                        
                        # Consultar roster específico del equipo para detalles de lesiones
                        try:
                            roster_url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
                            roster_resp = requests.get(roster_url, timeout=5)
                            roster_data = roster_resp.json()
                            
                            for athlete in roster_data.get('athletes', []):
                                if athlete.get('injuries'):
                                    # Tomar la lesión más reciente
                                    injury = athlete['injuries'][0]
                                    status = injury.get('status', 'Unknown')
                                    mapped_status = status_map.get(status, status)
                                    
                                    # Normalizar nombre para coincidir con NBA API
                                    # ESPN usa "LeBron James", NBA usa "LeBron James" (generalmente coinciden)
                                    full_name = athlete.get('fullName')
                                    
                                    injured_players.append({
                                        'PLAYER_NAME': full_name,
                                        'TEAM_NAME': team_name,
                                        'Current_Status': mapped_status,
                                        'Comment': injury.get('details', {}).get('type', 'Injury')
                                    })
                                    
                        except Exception as e:
                            print(f"Error obteniendo roster de {team_name}: {e}")
                            continue
            
            if injured_players:
                df = pd.DataFrame(injured_players)
                print(f"✅ {len(df)} jugadores lesionados encontrados.")
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Info: No se pudo obtener reporte de lesiones detallado: {e}")
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
            
            # Si hay múltiples filas (traspasos), preferir TOT para las estadísticas
            if len(player_stats) > 1:
                tot_stats = player_stats[player_stats['TEAM_ABBREVIATION'] == 'TOT']
                if not tot_stats.empty:
                    player_stats = tot_stats

            # Tomar la primera fila disponible
            row = player_stats.iloc[0]
            
            stats_dict = {
                'player_name': row['PLAYER_NAME'],
                'team': row['TEAM_ABBREVIATION'],
                'gp': row['GP'],
                'pts': row['PTS'],
                'reb': row['REB'],
                'ast': row['AST'],
                'fg3m': row['FG3M'],
                'fg_pct': row['FG_PCT'],
                'fg3_pct': row['FG3_PCT'],
                'min': row['MIN']
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
        Usa el roster oficial actual y filtra por minutos y lesiones.
        
        Args:
            home_team_id: ID del equipo local
            away_team_id: ID del equipo visitante
            
        Returns:
            Diccionario con listas de IDs de jugadores activos por equipo
        """
        try:
            # Obtener reporte de lesiones
            injury_df = self.get_injury_report()
            
            # Obtener estadísticas globales para filtrar por minutos (más robusto para traspasos)
            # Aseguramos que all_stats esté cargado
            all_stats = self._get_all_players_stats()
            
            def get_team_active_players(team_id):
                try:
                    time.sleep(0.6)
                    # Obtener roster oficial actual
                    roster = commonteamroster.CommonTeamRoster(
                        team_id=team_id, 
                        season=self.current_season
                    )
                    roster_df = roster.get_data_frames()[0]
                    
                    if roster_df.empty:
                        return []
                        
                    active_ids = []
                    injured_names = set()
                    
                    # Procesar lista de lesionados
                    if not injury_df.empty:
                        if 'Current_Status' in injury_df.columns:
                            # Filtrar solo los que están definitivamente fuera
                            out_players = injury_df[injury_df['Current_Status'].isin(['Out', 'Doubtful'])]
                            if 'PLAYER_NAME' in out_players.columns:
                                injured_names = set(out_players['PLAYER_NAME'].values)
                        elif 'PLAYER_NAME' in injury_df.columns:
                            injured_names = set(injury_df['PLAYER_NAME'].values)
                    
                    for _, player in roster_df.iterrows():
                        p_id = player['PLAYER_ID']
                        p_name = player['PLAYER']
                        
                        # Verificar lesión (coincidencia exacta o parcial)
                        is_injured = False
                        if p_name in injured_names:
                            is_injured = True
                        else:
                            # Intento de coincidencia parcial (ej. "Luka Doncic" vs "L. Doncic")
                            for inj_name in injured_names:
                                if p_name in inj_name or inj_name in p_name:
                                    is_injured = True
                                    break
                        
                        if is_injured:
                            continue
                            
                        # Verificar minutos (usando stats globales)
                        p_stats = all_stats[all_stats['PLAYER_ID'] == p_id]
                        
                        if not p_stats.empty:
                            # MIN en all_stats es PerGame
                            avg_min = p_stats['MIN'].values[0]
                            if avg_min > 10:
                                active_ids.append(p_id)
                        
                    return active_ids
                    
                except Exception as e:
                    print(f"Error procesando equipo {team_id}: {e}")
                    return []

            home_active = get_team_active_players(home_team_id)
            away_active = get_team_active_players(away_team_id)
            
            return {
                'home': home_active,
                'away': away_active
            }
            
        except Exception as e:
            print(f"Error obteniendo jugadores activos: {e}")
            print("Retornando listas vacías - se reintentará...")
            return {'home': [], 'away': []}

    def get_live_game_stats(self, game_id: str) -> Dict:
        """
        Obtiene estadísticas en tiempo real de un partido en curso.
        
        Args:
            game_id: ID del partido
            
        Returns:
            Diccionario con estadísticas de jugadores en tiempo real
        """
        try:
            # Usar el endpoint live boxscore
            box = boxscore.BoxScore(game_id=game_id)
            data = box.get_dict()
            
            live_stats = {}
            
            if 'game' in data:
                game_data = data['game']
                
                # Función auxiliar para procesar jugadores de un equipo
                def process_team_players(team_data):
                    team_code = team_data.get('teamTricode', '')
                    for player in team_data.get('players', []):
                        stats = player.get('statistics', {})
                        live_stats[player['personId']] = {
                            'name': player.get('name', 'Unknown'),
                            'team': team_code,
                            'pts': stats.get('points', 0),
                            'reb': stats.get('reboundsTotal', 0),
                            'ast': stats.get('assists', 0),
                            'fg3m': stats.get('threePointersMade', 0),
                            'stl': stats.get('steals', 0),
                            'blk': stats.get('blocks', 0),
                            'min': stats.get('minutes', '00:00')
                        }

                if 'homeTeam' in game_data:
                    process_team_players(game_data['homeTeam'])
                
                if 'awayTeam' in game_data:
                    process_team_players(game_data['awayTeam'])
                    
            return live_stats
            
        except Exception as e:
            print(f"Error obteniendo stats en vivo para {game_id}: {e}")
            return {}