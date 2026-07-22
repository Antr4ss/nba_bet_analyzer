"""
api_client.py
Módulo para conexión con la API de NBA y obtención de datos en tiempo real.
Maneja la sincronización diaria de partidos, estadísticas de jugadores y reportes de lesiones.
"""

from nba_api.live.nba.endpoints import scoreboard, boxscore
from nba_api.stats.endpoints import (
    leaguegamefinder, playergamelogs, commonplayerinfo,
    leaguedashplayerstats, teamgamelogs, scoreboardv2, scoreboardv3, commonteamroster, boxscoretraditionalv2
)
from nba_api.stats.static import teams, players
from datetime import datetime, timedelta
import pandas as pd
import time
import requests
import unicodedata
import re
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
        self._games_cache = {}
        self._injury_report_cache = {
            'timestamp': 0.0,
            'data': pd.DataFrame()
        }
        
    def _normalize_name(self, name: str) -> str:
        """Normaliza un nombre eliminando acentos y caracteres especiales."""
        if not isinstance(name, str):
            return ""
        # Normalizar unicode (NFD separa caracteres de sus acentos)
        nfkd_form = unicodedata.normalize('NFKD', name)
        # Filtrar caracteres no ASCII y convertir a minúsculas
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()

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

    def _get_default_game_date(self) -> str:
        """
        Devuelve la fecha en hora de Nueva York (ET).
        NBA publica horarios en ET, así que debe consultarse en esa zona.
        """
        # Convertir hora actual (cualquier zona) a ET
        now_et = pd.Timestamp.now(tz='America/New_York')
        return now_et.strftime('%Y-%m-%d')

    def _get_team_info_by_id(self, team_id: int) -> Dict:
        """Busca información estática de un equipo por ID."""
        teams_map = {team['id']: team for team in self.teams_data}
        return teams_map.get(int(team_id), {})

    def _get_team_id_from_tricode(self, tricode: str) -> Optional[int]:
        """Resuelve el ID del equipo a partir de su abreviatura."""
        if not tricode:
            return None

        tricode = str(tricode).upper().strip()
        for team in self.teams_data:
            if team.get('abbreviation', '').upper() == tricode:
                return team['id']
        return None

    def _build_game_info(self, game_id: str, home_team_id: int, away_team_id: int, game_time: str) -> Dict:
        """Construye el payload estándar de un partido."""
        home_team_info = self._get_team_info_by_id(home_team_id)
        away_team_info = self._get_team_info_by_id(away_team_id)

        return {
            'game_id': str(game_id),
            'home_team': home_team_info.get('nickname', 'Unknown'),
            'away_team': away_team_info.get('nickname', 'Unknown'),
            'game_time': game_time,
            'home_team_id': int(home_team_id),
            'away_team_id': int(away_team_id),
            'home_team_tricode': home_team_info.get('abbreviation', ''),
            'away_team_tricode': away_team_info.get('abbreviation', '')
        }

    def _normalize_game_time(self, date: Optional[str], raw_time: str) -> str:
        """Normaliza game_time a ISO UTC cuando se puede, si no deja el texto original."""
        if not raw_time:
            return raw_time

        time_text = str(raw_time).strip()

        # Formato con hora ET (ej: "7:30 pm ET") usando la fecha solicitada.
        if date and "ET" in time_text.upper():
            try:
                match = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)\s*ET", time_text, re.IGNORECASE)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    suffix = match.group(3).lower()
                    if suffix == "pm" and hour != 12:
                        hour += 12
                    if suffix == "am" and hour == 12:
                        hour = 0

                    et_time = pd.Timestamp(f"{date} {hour:02d}:{minute:02d}", tz="America/New_York")
                    return et_time.tz_convert("UTC").isoformat()
            except Exception:
                return raw_time

        # Formatos ISO (con o sin offset). Si es naive, asumir UTC.
        try:
            dt_utc = pd.to_datetime(time_text, errors="coerce", utc=True)
            if pd.notna(dt_utc):
                return dt_utc.isoformat()
        except Exception:
            return raw_time

        return raw_time

    def _get_espn_time_map(self, date: str) -> Dict:
        """Obtiene horarios desde ESPN y los indexa por (away_abbr, home_abbr)."""
        time_map = {}
        if not date:
            return time_map

        try:
            compact_date = date.replace("-", "")
            url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
            resp = requests.get(url, params={"dates": compact_date}, timeout=8)
            data = resp.json()

            for event in data.get("events", []):
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                comp_date = comp.get("date") or event.get("date")
                if not comp_date:
                    continue

                home_abbr = None
                away_abbr = None
                for competitor in comp.get("competitors", []):
                    team = competitor.get("team", {})
                    abbr = team.get("abbreviation")
                    if competitor.get("homeAway") == "home":
                        home_abbr = abbr
                    elif competitor.get("homeAway") == "away":
                        away_abbr = abbr

                if home_abbr and away_abbr:
                    time_map[(away_abbr.upper(), home_abbr.upper())] = comp_date

        except Exception as e:
            print(f"Info: No se pudo obtener horarios desde ESPN: {e}")

        return time_map

    def _get_games_from_static_api(self, date: str) -> List[Dict]:
        """
        Obtiene partidos desde la API estática de NBA.
        Mejorado: Mejor manejo de errores y timeouts.
        """
        try:
            import requests
            
            url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
            
            # Intentar con timeout generoso
            response = requests.get(url, timeout=15)
            
            # Verificar si la respuesta es válida (no siempre 200)
            if response.status_code not in [200, 304]:
                print(f"      API estática retornó código {response.status_code}")
                return []
            
            data = response.json()
            game_dates = data.get("leagueSchedule", {}).get("gameDates", [])
            
            if not game_dates:
                return []
            
            from datetime import datetime as dt
            date_obj = dt.strptime(date, "%Y-%m-%d")
            target_date = date_obj.strftime("%m/%d/%Y 00:00:00")
            
            # Buscar el día con esos partidos
            for day in game_dates:
                if day.get("gameDate") == target_date:
                    games = day.get("games", [])
                    parsed_games = []
                    
                    for game in games:
                        home_team = game.get("homeTeam", {})
                        away_team = game.get("awayTeam", {})
                        
                        home_team_id = home_team.get("teamId")
                        away_team_id = away_team.get("teamId")
                        game_id = game.get("gameId")
                        game_time_utc = self._normalize_game_time(date, game.get("gameDateTimeUTC", ""))
                        
                        if not game_id or home_team_id is None or away_team_id is None:
                            continue
                        
                        parsed_games.append(self._build_game_info(
                            game_id, 
                            home_team_id, 
                            away_team_id, 
                            game_time_utc
                        ))
                    
                    return parsed_games
            
            return []
            
        except requests.exceptions.Timeout:
            print("      API estática: Timeout (>15s)")
            return []
        except requests.exceptions.ConnectionError:
            print("      API estática: Error de conexión")
            return []
        except ValueError as e:  # JSON decode error
            print(f"      API estática: Respuesta inválida ({str(e)[:30]}...)")
            return []
        except Exception as e:
            print(f"      API estática: Error inesperado ({str(e)[:50]}...)")
            return []

    def _get_all_available(self, date: str) -> List[Dict]:
        """
        Obtiene partidos usando TODAS las APIs disponibles y combina resultados.
        Útil cuando una API tiene datos parciales.
        """
        all_games = []
        seen_game_ids = set()

        apis = [
            ("Estática", self._get_games_from_static_api),
            ("Live", self._get_games_from_live_scoreboard),
            ("V3", self._get_games_from_scoreboard_v2),
            ("Finder", self._get_games_from_league_game_finder),
        ]

        for api_name, api_func in apis:
            try:
                games = api_func(date)
                for game in games:
                    game_id = game.get('game_id')
                    if game_id not in seen_game_ids:
                        all_games.append(game)
                        seen_game_ids.add(game_id)
                        print(f"      [{api_name}] Agregado: {game['away_team']} @ {game['home_team']}")
            except Exception:
                pass

        return all_games
    
    def get_todays_games_combined(self, date: str = None) -> List[Dict]:
        """
            ALTERNATIVA: Obtiene partidos de TODAS las APIs y combina resultados.
            Usa esto si algunos partidos se pierden.
            Cambio de implementación: en lugar de usar la primera API que funcione,
        recolecta de todas ellas y elimina duplicados.
        """
        try:
            if date is None:
                date = self._get_default_game_date()

            if date in self._games_cache:
                cached_games = self._games_cache[date]
                if cached_games:
                    print(f"   📦 Usando cache para fecha {date} ({len(cached_games)} partidos)")
                    return cached_games
            
            print(f"📅 Buscando partidos para: {date} (ET - Eastern Time)")
            print(f"   Recolectando de TODAS las APIs...\n")
            
            all_games = self._get_all_available(date)
            
            if all_games:
                print(f"\n✅ Total de partidos combinados: {len(all_games)}\n")
            else:
                print(f"\n❌ No se encontraron partidos en ninguna API\n")
            
            self._games_cache[date] = all_games
            return all_games
                
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            return []
        
    def _get_games_from_live_scoreboard(self, date: str) -> List[Dict]:
        """Intenta obtener partidos desde el scoreboard live."""
        try:
            board = scoreboard.ScoreBoard()
            board_dict = board.get_dict()
            scoreboard_data = board_dict.get('scoreboard', {})

            if not isinstance(scoreboard_data, dict):
                return []

            games = scoreboard_data.get('games', [])
            if not games:
                return []

            parsed_games = []
            for game in games:
                home_team = game.get('homeTeam', {}) or {}
                away_team = game.get('awayTeam', {}) or {}

                home_team_id = (
                    home_team.get('teamId')
                    or home_team.get('teamID')
                    or home_team.get('id')
                    or self._get_team_id_from_tricode(home_team.get('teamTricode') or home_team.get('tricode'))
                )
                away_team_id = (
                    away_team.get('teamId')
                    or away_team.get('teamID')
                    or away_team.get('id')
                    or self._get_team_id_from_tricode(away_team.get('teamTricode') or away_team.get('tricode'))
                )

                game_id = game.get('gameId') or game.get('gameID') or game.get('id')
                raw_time = (
                    game.get('gameStatusText')
                    or game.get('gameStatus')
                    or game.get('gameClock')
                    or game.get('gameTimeUTC')
                    or game.get('gameDateTimeUTC')
                    or ''
                )
                game_time = self._normalize_game_time(date, raw_time)

                if not game_id or home_team_id is None or away_team_id is None:
                    continue

                parsed_games.append(self._build_game_info(game_id, home_team_id, away_team_id, game_time))

            return parsed_games
        except Exception as e:
            print(f"Error obteniendo partidos desde scoreboard live para {date}: {e}")
            return []

    def _get_games_from_scoreboard_v2(self, date: str) -> List[Dict]:
        """Obtiene partidos usando ScoreboardV3 (mejor: formato moderno, horarios precisos)."""
        try:
            time.sleep(0.6)
            board = scoreboardv3.ScoreboardV3(game_date=date)
            data = board.get_dict()
            
            if not data or 'scoreboard' not in data or 'games' not in data['scoreboard']:
                return []
            
            parsed_games = []
            for game in data['scoreboard']['games']:
                game_id = game.get('gameId')
                
                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})
                
                home_team_id = home_team.get('teamId')
                away_team_id = away_team.get('teamId')
                
                if not game_id or not home_team_id or not away_team_id:
                    continue
                
                # Obtener horario del juego
                game_time = game.get('gameTimeUTC')  # ISO format
                if not game_time:
                    game_time = self._normalize_game_time(date, f"{date} 8:00 PM ET")
                
                parsed_games.append(self._build_game_info(
                    game_id,
                    home_team_id,
                    away_team_id,
                    game_time
                ))
            
            return parsed_games
        except Exception as e:
            print(f"Error obteniendo partidos desde ScoreboardV3 para {date}: {e}")
            return []

    def _get_games_from_league_game_finder(self, date: str) -> List[Dict]:
        """Fallback: Intenta reconstruir el calendario del día con LeagueGameFinder (solo fechas)."""
        try:
            time.sleep(0.6)
            # NOTA: LeagueGameFinder solo devuelve fechas, no horarios
            # Se usa como último recurso cuando ScoreboardV2 y otros fallan
            finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=self.current_season,
                date_from_nullable=date,
                date_to_nullable=date
            )
            df = finder.get_data_frames()[0]

            if df.empty or 'GAME_ID' not in df.columns:
                return []

            parsed_games = []
            grouped_games = df.groupby('GAME_ID')

            for game_id, game_df in grouped_games:
                home_row = None
                away_row = None

                for _, row in game_df.iterrows():
                    matchup = str(row.get('MATCHUP', ''))
                    if 'vs.' in matchup:
                        home_row = row
                    elif '@' in matchup:
                        away_row = row

                if home_row is None or away_row is None:
                    continue

                home_id = int(home_row['TEAM_ID'])
                away_id = int(away_row['TEAM_ID'])
                
                # LeagueGameFinder solo da fechas. Usar medianoche ET como hora por defecto
                # (el Live Tracker usará BoxScoreTraditionalV2 que sí tiene stats)
                game_time = self._normalize_game_time(date, f"{date} 8:00 PM ET")

                parsed_games.append(self._build_game_info(
                    game_id,
                    home_id,
                    away_id,
                    game_time
                ))

            return parsed_games
        except Exception as e:
            print(f"Error obteniendo partidos desde LeagueGameFinder para {date}: {e}")
            return []
        
    def get_todays_games(self, date: str = None) -> List[Dict]:
        """
        Obtiene todos los partidos programados para una fecha específica.
        
        Args:
            date: Fecha en formato 'YYYY-MM-DD' (interpretada como ET)
                Si es None, usa la fecha actual en ET

        Returns:
            Lista de diccionarios con información de cada partido
        """
        try:
            if date is None:
                date = self._get_default_game_date()

            # Verificar caché primero
            if date in self._games_cache:
                cached_games = self._games_cache[date]
                if cached_games:  # Solo usar caché si no está vacío
                    print(f"   📦 Usando cache para fecha {date} ({len(cached_games)} partidos)")
                    return cached_games
            
            print(f"📅 Buscando partidos para: {date} (ET - Eastern Time)")
            print(f"   Intentando múltiples APIs...\n")
            
            todays_games = []
            api_source = None

            # INTENTO 1: API estática (la más confiable, pero puede bloquearse)
            print("   [1/5] Intentando API estática NBC...")
            try:
                todays_games = self._get_games_from_static_api(date)
                if todays_games:
                    api_source = "API Estática NBC"
                    print(f"   ✅ Éxito con API estática: {len(todays_games)} partidos\n")
                    self._games_cache[date] = todays_games
                    return todays_games
                else:
                    print(f"   ⚠️  API estática: 0 partidos (puede ser correcto si no hay juegos)\n")
            except Exception as e:
                print(f"   ❌ Error en API estática: {str(e)[:60]}...\n")

            # INTENTO 2: ScoreboardV3 (PRIORIDAD ALTA - formato moderno, horarios precisos)
            print("   [2/5] Intentando ScoreboardV3 (API moderna con horarios)...")
            try:
                todays_games = self._get_games_from_scoreboard_v2(date)
                if todays_games:
                    api_source = "ScoreboardV3"
                    print(f"   ✅ Éxito con ScoreboardV3: {len(todays_games)} partidos\n")
                    self._games_cache[date] = todays_games
                    return todays_games
                else:
                    print(f"   ⚠️  ScoreboardV3: 0 partidos\n")
            except Exception as e:
                print(f"   ❌ Error en ScoreboardV3: {str(e)[:60]}...\n")

            # INTENTO 3: Live Scoreboard (en tiempo real, bueno para hoy)
            print("   [3/5] Intentando Live Scoreboard (en tiempo real)...")
            if not todays_games and date == self._get_default_game_date():
                try:
                    todays_games = self._get_games_from_live_scoreboard(date)
                    if todays_games:
                        api_source = "Live Scoreboard"
                        print(f"   ✅ Éxito con Live Scoreboard: {len(todays_games)} partidos\n")
                        self._games_cache[date] = todays_games
                        return todays_games
                    else:
                        print(f"   ⚠️  Live Scoreboard: 0 partidos\n")
                except Exception as e:
                    print(f"   ❌ Error en Live Scoreboard: {str(e)[:60]}...\n")

            # INTENTO 4: LeagueGameFinder (ALTERNATIVA - solo fechas sin scraping)
            print("   [4/5] Intentando LeagueGameFinder (sin horarios, pero confiable)...")
            try:
                todays_games = self._get_games_from_league_game_finder(date)
                if todays_games:
                    api_source = "LeagueGameFinder"
                    print(f"   ✅ Éxito con LeagueGameFinder: {len(todays_games)} partidos\n")
                    print(f"   ⚠️  ADVERTENCIA: LeagueGameFinder devuelve solo fechas.")
                    print(f"   Intentando obtener horarios desde fuentes adicionales...\n")
                    self._games_cache[date] = todays_games
                    return todays_games
                else:
                    print(f"   ⚠️  LeagueGameFinder: 0 partidos\n")
            except Exception as e:
                print(f"   ❌ Error en LeagueGameFinder: {str(e)[:60]}...\n")

            # Si llegamos aquí, no hay partidos de ninguna API
            print("❌ No se encontraron partidos en ninguna API")
            print("   Posibles razones:")
            print("   - No hay partidos programados para esa fecha")
            print("   - Las APIs están bloqueadas/fuera de servicio")
            print("   - Hay un error de configuración")
            
            self._games_cache[date] = []
            return []
                
        except Exception as e:
            print(f"❌ Error crítico obteniendo partidos del día: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_injury_report(self) -> pd.DataFrame:
        """
        Obtiene el reporte de lesiones actualizado usando la API de ESPN.
        
        Returns:
            DataFrame con columnas: PLAYER_NAME, Current_Status, Comment
        """
        try:
            cache_ttl_seconds = 600
            now_ts = time.time()
            cached_df = self._injury_report_cache.get('data')
            cached_ts = self._injury_report_cache.get('timestamp', 0.0)
            if isinstance(cached_df, pd.DataFrame) and not cached_df.empty and (now_ts - cached_ts) < cache_ttl_seconds:
                return cached_df

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
                                    
                                    # ID del jugador de ESPN (para obtener foto)
                                    espn_id = athlete.get('id')
                                    
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
                self._injury_report_cache = {
                    'timestamp': now_ts,
                    'data': df
                }
                return df
            
            empty_df = pd.DataFrame()
            self._injury_report_cache = {
                'timestamp': now_ts,
                'data': empty_df
            }
            return empty_df
            
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
    
    def get_active_players_for_game(self, home_team_id: int, away_team_id: int, game_date_utc: str = None, game_id: str = None, as_of_date: str = None) -> Dict[str, List[int]]:
        """
        Obtiene los jugadores activos (no lesionados) de ambos equipos para un partido.
        
        Estrategia:
        1. Si game_id está disponible → intenta usar boxscore (para partidos completados)
        2. Si falla o no hay game_id → usa roster + reporte de lesiones de hoy
        
        Args:
            home_team_id: ID del equipo local
            away_team_id: ID del equipo visitante
            game_date_utc: Fecha del partido en UTC (opcional)
            game_id: ID del partido (si es disponible, permite usar boxscore)
            as_of_date: Fecha de referencia (opcional)
            
        Returns:
            Diccionario con listas de IDs de jugadores activos por equipo
        """
        try:
            # PRIORIDAD 1: Si tenemos game_id y el partido está completado, usar boxscore
            if game_id:
                print(f"📊 Intentando obtener jugadores reales del boxscore para {game_id}...")
                boxscore_players = self._get_players_from_boxscore(game_id)
                
                if boxscore_players['home'] and boxscore_players['away']:
                    print(f"✅ {len(boxscore_players['home'])} jugadores del equipo local, {len(boxscore_players['away'])} visitantes (desde boxscore)")
                    return boxscore_players
            
            # FALLBACK: Usar roster + reporte de lesiones de hoy
            print("📋 Fallback: usando roster + reporte de lesiones actual...")
            
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
                    normalized_injured_names = set()
                    
                    # Procesar lista de lesionados
                    if not injury_df.empty:
                        if 'Current_Status' in injury_df.columns:
                            # Estados que consideramos como no disponible para jugar
                            unavailable_states = ['Out', 'Doubtful', 'Questionable', 'Day-To-Day']
                            out_players = injury_df[injury_df['Current_Status'].isin(unavailable_states)]
                            if 'PLAYER_NAME' in out_players.columns:
                                for name in out_players['PLAYER_NAME'].values:
                                    normalized_injured_names.add(self._normalize_name(name))
                        elif 'PLAYER_NAME' in injury_df.columns:
                            # Si no hay columna de estado, marcar todos los listados como lesionados
                            for name in injury_df['PLAYER_NAME'].values:
                                normalized_injured_names.add(self._normalize_name(name))
                    
                    for _, player in roster_df.iterrows():
                        p_id = player['PLAYER_ID']
                        p_name = player['PLAYER']
                        p_name_norm = self._normalize_name(p_name)
                        
                        # Verificar lesión (coincidencia exacta o parcial)
                        is_injured = False
                        if p_name_norm in normalized_injured_names:
                            is_injured = True
                        else:
                            # Intento de coincidencia parcial (ej. "Luka Doncic" vs "L. Doncic")
                            for inj_name_norm in normalized_injured_names:
                                # Verificar que la coincidencia sea significativa (más de 4 caracteres para evitar falsos positivos cortos)
                                if len(inj_name_norm) > 4 and (p_name_norm in inj_name_norm or inj_name_norm in p_name_norm):
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

    def _get_players_from_boxscore(self, game_id: str) -> Dict[str, List[int]]:
        """
        Obtiene la lista de jugadores que realmente participaron en un partido completado.
        Usando el boxscore como fuente de verdad para partidos pasados.
        
        Args:
            game_id: ID del partido (ej. '0042500214')
            
        Returns:
            Diccionario con {'home': [player_ids], 'away': [player_ids]}
        """
        try:
            box = boxscore.BoxScore(game_id=game_id)
            data = box.get_dict()
            
            home_players = []
            away_players = []
            
            if 'game' in data:
                game_data = data['game']
                
                # Procesar jugadores del equipo local
                if 'homeTeam' in game_data:
                    for player in game_data['homeTeam'].get('players', []):
                        player_id = player.get('personId')
                        stats = player.get('statistics', {})
                        # Solo incluir si tiene minutos (jugó)
                        if player_id and stats.get('minutes', '00:00') != '00:00':
                            home_players.append(player_id)
                
                # Procesar jugadores del equipo visitante
                if 'awayTeam' in game_data:
                    for player in game_data['awayTeam'].get('players', []):
                        player_id = player.get('personId')
                        stats = player.get('statistics', {})
                        # Solo incluir si tiene minutos (jugó)
                        if player_id and stats.get('minutes', '00:00') != '00:00':
                            away_players.append(player_id)
            
            return {'home': home_players, 'away': away_players}
            
        except Exception as e:
            print(f"Error obteniendo boxscore para {game_id}: {e}")
            return {'home': [], 'away': []}

    def _get_boxscore_stats_v2(self, game_id: str) -> Dict:
        """Fallback: obtiene stats de jugadores desde BoxScoreTraditionalV2."""
        try:
            box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            players_df = box.player_stats.get_data_frame()

            if players_df.empty:
                return {}

            stats_map = {}
            for _, row in players_df.iterrows():
                player_id = row.get('PLAYER_ID')
                if not player_id:
                    continue

                stats_map[int(player_id)] = {
                    'name': row.get('PLAYER_NAME', 'Unknown'),
                    'team': row.get('TEAM_ABBREVIATION', ''),
                    'pts': int(row.get('PTS', 0)),
                    'reb': int(row.get('REB', 0)),
                    'ast': int(row.get('AST', 0)),
                    'fg3m': int(row.get('FG3M', 0)),
                    'stl': int(row.get('STL', 0)),
                    'blk': int(row.get('BLK', 0)),
                    'min': row.get('MIN', '00:00')
                }

            return stats_map
        except Exception as e:
            print(f"Error obteniendo boxscore tradicional para {game_id}: {e}")
            return {}

    def get_live_game_stats(self, game_id: str) -> Dict:
        """
        Obtiene estadísticas en tiempo real de un partido usando ScoreboardV3 y BoxScoreTraditionalV2.
        
        Args:
            game_id: ID del partido (ej. '0022400123')
            
        Returns:
            Diccionario con estadísticas de jugadores formateado {player_id: {stats}}
        """
        live_stats = {}
        
        try:
            # INTENTO 1: Usar CDN directo para live boxscore
            try:
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.nba.com/',
                    'Origin': 'https://www.nba.com',
                    'Accept': 'application/json, text/plain, */*'
                }
                url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'game' in data and data['game']:
                        game_data = data['game']
                        game_status = game_data.get('gameStatusText', '')
                        print(f"📊 Live BoxScore (CDN) - Estado: {game_status}")
                        
                        def safe_int(value, default=0):
                            """Convierte a entero de forma segura, manejando NaN y None."""
                            try:
                                if pd.isna(value):
                                    return default
                                return int(float(value))
                            except (ValueError, TypeError, NameError):
                                return default
                        
                        # Procesar jugadores del equipo local
                        if 'homeTeam' in game_data:
                            home_team = game_data['homeTeam']
                            home_tricode = home_team.get('teamTricode', '')
                            for player in home_team.get('players', []):
                                stats = player.get('statistics', {}) or {}
                                player_id = player.get('personId')
                                player_name = player.get('name', '')
                                
                                if player_id and player_name:
                                    live_stats[player_id] = {
                                        'name': str(player_name).strip(),
                                        'name_first': str(player.get('nameFirst', '')).strip(),
                                        'name_last': str(player.get('nameLast', '')).strip(),
                                        'team': home_tricode,
                                        'pts': safe_int(stats.get('points')),
                                        'reb': safe_int(stats.get('reboundsTotal')),
                                        'ast': safe_int(stats.get('assists')),
                                        'fg3m': safe_int(stats.get('threePointersMade')),
                                        'stl': safe_int(stats.get('steals')),
                                        'blk': safe_int(stats.get('blocks')),
                                        'min': str(stats.get('minutesCalculated', '00:00'))
                                    }
                        
                        # Procesar jugadores del equipo visitante
                        if 'awayTeam' in game_data:
                            away_team = game_data['awayTeam']
                            away_tricode = away_team.get('teamTricode', '')
                            for player in away_team.get('players', []):
                                stats = player.get('statistics', {}) or {}
                                player_id = player.get('personId')
                                player_name = player.get('name', '')
                                
                                if player_id and player_name:
                                    live_stats[player_id] = {
                                        'name': str(player_name).strip(),
                                        'name_first': str(player.get('nameFirst', '')).strip(),
                                        'name_last': str(player.get('nameLast', '')).strip(),
                                        'team': away_tricode,
                                        'pts': safe_int(stats.get('points')),
                                        'reb': safe_int(stats.get('reboundsTotal')),
                                        'ast': safe_int(stats.get('assists')),
                                        'fg3m': safe_int(stats.get('threePointersMade')),
                                        'stl': safe_int(stats.get('steals')),
                                        'blk': safe_int(stats.get('blocks')),
                                        'min': str(stats.get('minutesCalculated', '00:00'))
                                    }
                        
                        if live_stats:
                            print(f"✅ Live BoxScore (CDN): {len(live_stats)} jugadores encontrados")
                            print(f"   Nombres de ejemplo: {list(live_stats.values())[:3]}")
                            return live_stats
                else:
                    print(f"⚠️ Live BoxScore (CDN) no disponible: {response.status_code}")
                            
            except Exception as e:
                print(f"⚠️ Error directo a CDN Live BoxScore: {e}")
            
            # INTENTO 2: Usar BoxScoreTraditionalV2 para partidos finalizados
            if not live_stats:
                print("📊 Intentando BoxScoreTraditionalV2...")
                try:
                    import time
                    time.sleep(0.6)
                    
                    box_v2 = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
                    players_df = box_v2.player_stats.get_data_frame()
                    
                    if not players_df.empty:
                        # Mostrar columnas disponibles para debug
                        print(f"   Columnas BoxScoreTraditionalV2: {list(players_df.columns)}")
                        
                        # Limpiar valores NaN
                        players_df = players_df.fillna(0)
                        
                        for _, row in players_df.iterrows():
                            player_id = row.get('PLAYER_ID')
                            if not player_id or player_id == 0:
                                continue
                            
                            player_id = int(player_id)
                            player_name = str(row.get('PLAYER_NAME', '')).strip()
                            
                            if not player_name:
                                continue
                            
                            # Convertir minutos de forma segura
                            minutes = row.get('MIN')
                            if pd.isna(minutes):
                                minutes_str = '00:00'
                            else:
                                minutes_str = str(minutes)
                            
                            live_stats[player_id] = {
                                'name': player_name,
                                'name_first': '',
                                'name_last': '',
                                'team': str(row.get('TEAM_ABBREVIATION', '')).strip(),
                                'pts': int(float(row.get('PTS', 0))),
                                'reb': int(float(row.get('REB', 0))),
                                'ast': int(float(row.get('AST', 0))),
                                'fg3m': int(float(row.get('FG3M', 0))),
                                'stl': int(float(row.get('STL', 0))),
                                'blk': int(float(row.get('BLK', 0))),
                                'min': minutes_str
                            }
                        
                        print(f"✅ BoxScoreTraditionalV2: {len(live_stats)} jugadores encontrados")
                        print(f"   Nombres de ejemplo: {list(live_stats.values())[:3]}")
                        return live_stats
                        
                except Exception as e:
                    print(f"⚠️ BoxScoreTraditionalV2 no disponible: {e}")
                    import traceback
                    traceback.print_exc()
            
            # INTENTO 3: ScoreboardV3 para obtener estado del partido
            if not live_stats:
                print("📊 Intentando ScoreboardV3 para obtener estado...")
                try:
                    # Si es en vivo, la fecha suele ser hoy (hora ET)
                    # o se puede buscar usando hoy y ayer por si cruzamos la medianoche
                    game_date = self._get_default_game_date()
                    
                    import time
                    time.sleep(0.6)
                    
                    board = scoreboardv3.ScoreboardV3(game_date=game_date)
                    data = board.get_dict()
                    
                    # Chequear también ayer si no encontramos
                    games = data.get('scoreboard', {}).get('games', [])
                    if not any(g.get('gameId') == game_id for g in games):
                        try:
                            yesterday = (pd.Timestamp.now(tz='America/New_York') - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                            time.sleep(0.6)
                            board2 = scoreboardv3.ScoreboardV3(game_date=yesterday)
                            games.extend(board2.get_dict().get('scoreboard', {}).get('games', []))
                        except Exception:
                            pass

                    for game in games:
                        if game.get('gameId') == game_id:
                            status_text = game.get('gameStatusText', 'Unknown')
                            print(f"  Estado: {status_text}")
                            
                            # Si el partido finalizó, intentar boxscore de nuevo
                            if 'Final' in str(status_text):
                                print("  Partido finalizado - intentando BoxScoreTraditionalV2 nuevamente...")
                                try:
                                    time.sleep(0.6)
                                    
                                    box_v2 = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
                                    players_df = box_v2.player_stats.get_data_frame()
                                    
                                    if not players_df.empty:
                                        players_df = players_df.fillna(0)
                                        
                                        for _, row in players_df.iterrows():
                                            player_id = row.get('PLAYER_ID')
                                            if not player_id or player_id == 0:
                                                continue
                                            
                                            player_id = int(player_id)
                                            player_name = str(row.get('PLAYER_NAME', '')).strip()
                                            
                                            if not player_name:
                                                continue
                                                
                                                live_stats[player_id] = {
                                                    'name': player_name,
                                                    'name_first': '',
                                                    'name_last': '',
                                                    'team': str(row.get('TEAM_ABBREVIATION', '')).strip(),
                                                    'pts': int(float(row.get('PTS', 0))),
                                                    'reb': int(float(row.get('REB', 0))),
                                                    'ast': int(float(row.get('AST', 0))),
                                                    'fg3m': int(float(row.get('FG3M', 0))),
                                                    'stl': int(float(row.get('STL', 0))),
                                                    'blk': int(float(row.get('BLK', 0))),
                                                    'min': str(row.get('MIN', '00:00'))
                                                }
                                            
                                            if live_stats:
                                                print(f"✅ BoxScore recuperado: {len(live_stats)} jugadores")
                                                return live_stats
                                except Exception as e2:
                                    print(f"  Error en reintento BoxScore: {e2}")
                                
                                # Si aún no hay datos, retornar estado
                                return {
                                    'status': status_text,
                                    'period': game.get('period', 0),
                                    'clock': game.get('gameClock', ''),
                                    'home_score': game.get('homeTeam', {}).get('score', 0),
                                    'away_score': game.get('awayTeam', {}).get('score', 0)
                                }
                except Exception as e:
                    print(f"⚠️ ScoreboardV3 no disponible: {e}")
            
            return live_stats
            
        except Exception as e:
            print(f"❌ Error obteniendo stats en vivo: {e}")
            import traceback
            traceback.print_exc()
            return {}