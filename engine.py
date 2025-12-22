"""
engine.py
Motor de cálculo y predicción de apuestas NBA.
Implementa algoritmos para proyectar PRA, puntos, rebotes, asistencias y triples.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from api_client import NBADataClient


class NBAPredictionEngine:
    """Motor de predicción que calcula proyecciones y encuentra apuestas de valor."""
    
    def __init__(self):
        self.client = NBADataClient()
        # Líneas de apuestas promedio (simuladas - en producción conectar con API de odds)
        self.betting_lines = {}
        
    def calculate_weighted_average(self, season_avg: float, last5_avg: float, 
                                   last10_avg: float, back_to_back: bool) -> float:
        """
        Calcula un promedio ponderado considerando diferentes períodos de tiempo.
        
        Pesos:
        - Temporada: 30%
        - Últimos 10: 35%
        - Últimos 5: 35%
        - Penalización back-to-back: -8% si aplica
        
        Args:
            season_avg: Promedio de la temporada
            last5_avg: Promedio de últimos 5 juegos
            last10_avg: Promedio de últimos 10 juegos
            back_to_back: Si el equipo juega consecutivamente
            
        Returns:
            Proyección ponderada ajustada
        """
        # Pesos para cada período
        weights = {
            'season': 0.30,
            'last10': 0.35,
            'last5': 0.35
        }
        
        projection = (
            season_avg * weights['season'] +
            last10_avg * weights['last10'] +
            last5_avg * weights['last5']
        )
        
        # Penalización por back-to-back (fatiga)
        if back_to_back:
            projection *= 0.92  # -8% por fatiga
            
        return round(projection, 2)
    
    def adjust_for_opponent_defense(self, base_projection: float, 
                                    stat_type: str, 
                                    opponent_defense: Dict) -> float:
        """
        Ajusta la proyección base según la defensa del oponente.
        
        Args:
            base_projection: Proyección inicial del jugador
            stat_type: Tipo de estadística ('pts', 'reb', 'ast', 'fg3m')
            opponent_defense: Diccionario con ratings defensivos del rival
            
        Returns:
            Proyección ajustada por el factor defensivo del oponente
        """
        if not opponent_defense or stat_type not in ['pts', 'reb', 'ast', 'fg3m']:
            return base_projection
        
        # Mapa de estadísticas a métricas defensivas
        defense_map = {
            'pts': 'pts_allowed',
            'reb': 'reb_allowed',
            'ast': 'ast_allowed',
            'fg3m': 'fg3m_allowed'
        }
        
        defense_key = defense_map.get(stat_type)
        if not defense_key or defense_key not in opponent_defense:
            return base_projection
        
        # Obtener promedio de liga (valores aproximados NBA 2024)
        league_averages = {
            'pts_allowed': 114.0,
            'reb_allowed': 44.0,
            'ast_allowed': 26.0,
            'fg3m_allowed': 12.5
        }
        
        opponent_allowed = opponent_defense[defense_key]
        league_avg = league_averages[defense_key]
        
        # Factor de ajuste: si el rival permite más que el promedio, aumenta proyección
        adjustment_factor = opponent_allowed / league_avg
        
        adjusted = base_projection * adjustment_factor
        
        return round(adjusted, 2)
    
    def calculate_pra_projection(self, player_id: int, 
                                 opponent_team_id: int,
                                 is_back_to_back: bool) -> Dict:
        """
        Calcula la proyección de PRA (Puntos + Rebotes + Asistencias) para un jugador.
        
        Proceso:
        1. Obtener estadísticas de temporada, últimos 5 y 10 juegos
        2. Calcular promedio ponderado
        3. Ajustar por defensa del oponente
        4. Retornar proyección con nivel de confianza
        
        Args:
            player_id: ID del jugador
            opponent_team_id: ID del equipo rival
            is_back_to_back: Si el equipo juega en días consecutivos
            
        Returns:
            Diccionario con proyección, componentes y confianza
        """
        try:
            # 1. Obtener estadísticas de temporada
            season_stats = self.client.get_player_season_stats(player_id)
            if not season_stats:
                return {}
            
            # DEBUG: Mostrar datos de temporada obtenidos
            print(f"    DEBUG - {season_stats.get('player_name', 'Unknown')}")
            print(f"    DEBUG - Temporada: PTS={season_stats.get('pts')}, REB={season_stats.get('reb')}, AST={season_stats.get('ast')}")
            
            # 2. Obtener estadísticas recientes
            recent_games = self.client.get_player_recent_games(player_id, last_n=10)
            if recent_games.empty:
                print(f"    DEBUG - No hay datos de juegos recientes")
                return {}
            
            # Calcular promedios de últimos 5 y 10 juegos
            last5 = recent_games.head(5)
            last10 = recent_games.head(10)
            
            # DEBUG: Mostrar columnas disponibles
            print(f"    DEBUG - Columnas disponibles: {list(recent_games.columns)}")
            
            # Promedios por categoría
            season_pts = season_stats['pts']
            season_reb = season_stats['reb']
            season_ast = season_stats['ast']
            
            last5_pts = last5['PTS'].mean() if 'PTS' in last5.columns else season_pts
            last5_reb = last5['REB'].mean() if 'REB' in last5.columns else season_reb
            last5_ast = last5['AST'].mean() if 'AST' in last5.columns else season_ast
            
            last10_pts = last10['PTS'].mean() if 'PTS' in last10.columns else season_pts
            last10_reb = last10['REB'].mean() if 'REB' in last10.columns else season_reb
            last10_ast = last10['AST'].mean() if 'AST' in last10.columns else season_ast
            
            print(f"    DEBUG - Últimos 5: PTS={last5_pts:.1f}, REB={last5_reb:.1f}, AST={last5_ast:.1f}")
            print(f"    DEBUG - Últimos 10: PTS={last10_pts:.1f}, REB={last10_reb:.1f}, AST={last10_ast:.1f}")
            
            # 3. Calcular proyecciones ponderadas
            pts_projection = self.calculate_weighted_average(
                season_pts, last5_pts, last10_pts, is_back_to_back
            )
            reb_projection = self.calculate_weighted_average(
                season_reb, last5_reb, last10_reb, is_back_to_back
            )
            ast_projection = self.calculate_weighted_average(
                season_ast, last5_ast, last10_ast, is_back_to_back
            )
            
            # 4. Ajustar por defensa del oponente (DESACTIVADO TEMPORALMENTE PARA DEBUG)
            opponent_defense = self.client.get_team_defensive_rating(opponent_team_id)
            
            # Por ahora, NO ajustar - usar proyección directa
            pts_adjusted = pts_projection  # self.adjust_for_opponent_defense(pts_projection, 'pts', opponent_defense)
            reb_adjusted = reb_projection  # self.adjust_for_opponent_defense(reb_projection, 'reb', opponent_defense)
            ast_adjusted = ast_projection  # self.adjust_for_opponent_defense(ast_projection, 'ast', opponent_defense)
            
            print(f"    DEBUG - Proyecciones sin ajuste defensivo: PTS={pts_adjusted:.1f}, REB={reb_adjusted:.1f}, AST={ast_adjusted:.1f}")
            
            # PRA total
            pra_projection = pts_adjusted + reb_adjusted + ast_adjusted
            
            # 5. Calcular nivel de confianza basado en consistencia
            consistency = self._calculate_consistency(recent_games, ['PTS', 'REB', 'AST'])
            
            # 6. Detectar tendencia al alza
            pra_last5 = last5_pts + last5_reb + last5_ast
            pra_season = season_pts + season_reb + season_ast
            trending_up = pra_last5 > pra_season * 1.05  # 5% mejor que promedio
            
            return {
                'player_name': season_stats['player_name'],
                'team': season_stats['team'],
                'stat_type': 'PRA',
                'projection': round(pra_projection, 1),
                'components': {
                    'pts': round(pts_adjusted, 1),
                    'reb': round(reb_adjusted, 1),
                    'ast': round(ast_adjusted, 1)
                },
                'confidence': consistency,
                'trending_up': trending_up,
                'back_to_back': is_back_to_back,
                'games_played': season_stats['gp']
            }
            
        except Exception as e:
            print(f"Error calculando PRA para jugador {player_id}: {e}")
            return {}
    
    def calculate_points_projection(self, player_id: int, 
                                   opponent_team_id: int,
                                   is_back_to_back: bool) -> Dict:
        """
        Calcula proyección específica de puntos para un jugador.
        Similar a PRA pero enfocado solo en anotación.
        """
        try:
            season_stats = self.client.get_player_season_stats(player_id)
            if not season_stats:
                return {}
            
            recent_games = self.client.get_player_recent_games(player_id, last_n=10)
            if recent_games.empty:
                return {}
            
            last5 = recent_games.head(5)
            last10 = recent_games.head(10)
            
            season_pts = season_stats['pts']
            last5_pts = last5['PTS'].mean() if 'PTS' in last5.columns else season_pts
            last10_pts = last10['PTS'].mean() if 'PTS' in last10.columns else season_pts
            
            pts_projection = self.calculate_weighted_average(
                season_pts, last5_pts, last10_pts, is_back_to_back
            )
            
            opponent_defense = self.client.get_team_defensive_rating(opponent_team_id)
            pts_adjusted = pts_projection  # Desactivar ajuste defensivo temporalmente
            
            print(f"    DEBUG PTS - Proyección: {pts_adjusted:.1f}")
            
            consistency = self._calculate_consistency(recent_games, ['PTS'])
            
            # Detectar tendencia
            trending_up = last5_pts > season_pts * 1.05
            
            return {
                'player_name': season_stats['player_name'],
                'team': season_stats['team'],
                'stat_type': 'PTS',
                'projection': round(pts_adjusted, 1),
                'confidence': consistency,
                'trending_up': trending_up,
                'back_to_back': is_back_to_back
            }
            
        except Exception as e:
            print(f"Error calculando puntos para jugador {player_id}: {e}")
            return {}
    
    def calculate_threes_projection(self, player_id: int, 
                                   opponent_team_id: int,
                                   is_back_to_back: bool) -> Dict:
        """
        Calcula proyección de triples anotados (FG3M).
        """
        try:
            season_stats = self.client.get_player_season_stats(player_id)
            if not season_stats:
                return {}
            
            recent_games = self.client.get_player_recent_games(player_id, last_n=10)
            if recent_games.empty:
                return {}
            
            last5 = recent_games.head(5)
            last10 = recent_games.head(10)
            
            season_fg3m = season_stats['fg3m']
            last5_fg3m = last5['FG3M'].mean() if 'FG3M' in last5.columns else season_fg3m
            last10_fg3m = last10['FG3M'].mean() if 'FG3M' in last10.columns else season_fg3m
            
            fg3m_projection = self.calculate_weighted_average(
                season_fg3m, last5_fg3m, last10_fg3m, is_back_to_back
            )
            
            # Sin ajuste defensivo temporalmente
            fg3m_adjusted = fg3m_projection
            
            consistency = self._calculate_consistency(recent_games, ['FG3M'])
            trending_up = last5_fg3m > season_fg3m * 1.05
            
            return {
                'player_name': season_stats['player_name'],
                'team': season_stats['team'],
                'stat_type': 'FG3M',
                'projection': round(fg3m_adjusted, 1),
                'confidence': consistency,
                'trending_up': trending_up,
                'back_to_back': is_back_to_back
            }
            
        except Exception as e:
            print(f"Error calculando triples para jugador {player_id}: {e}")
            return {}
    
    def calculate_rebounds_projection(self, player_id: int, 
                                     opponent_team_id: int,
                                     is_back_to_back: bool) -> Dict:
        """
        Calcula proyección de rebotes totales (REB).
        """
        try:
            season_stats = self.client.get_player_season_stats(player_id)
            if not season_stats:
                return {}
            
            recent_games = self.client.get_player_recent_games(player_id, last_n=10)
            if recent_games.empty:
                return {}
            
            last5 = recent_games.head(5)
            last10 = recent_games.head(10)
            
            season_reb = season_stats['reb']
            last5_reb = last5['REB'].mean() if 'REB' in last5.columns else season_reb
            last10_reb = last10['REB'].mean() if 'REB' in last10.columns else season_reb
            
            reb_projection = self.calculate_weighted_average(
                season_reb, last5_reb, last10_reb, is_back_to_back
            )
            
            reb_adjusted = reb_projection
            
            consistency = self._calculate_consistency(recent_games, ['REB'])
            trending_up = last5_reb > season_reb * 1.05
            
            return {
                'player_name': season_stats['player_name'],
                'team': season_stats['team'],
                'stat_type': 'REB',
                'projection': round(reb_adjusted, 1),
                'confidence': consistency,
                'trending_up': trending_up,
                'back_to_back': is_back_to_back
            }
            
        except Exception as e:
            print(f"Error calculando rebotes para jugador {player_id}: {e}")
            return {}
    
    def calculate_assists_projection(self, player_id: int, 
                                    opponent_team_id: int,
                                    is_back_to_back: bool) -> Dict:
        """
        Calcula proyección de asistencias (AST).
        """
        try:
            season_stats = self.client.get_player_season_stats(player_id)
            if not season_stats:
                return {}
            
            recent_games = self.client.get_player_recent_games(player_id, last_n=10)
            if recent_games.empty:
                return {}
            
            last5 = recent_games.head(5)
            last10 = recent_games.head(10)
            
            season_ast = season_stats['ast']
            last5_ast = last5['AST'].mean() if 'AST' in last5.columns else season_ast
            last10_ast = last10['AST'].mean() if 'AST' in last10.columns else season_ast
            
            ast_projection = self.calculate_weighted_average(
                season_ast, last5_ast, last10_ast, is_back_to_back
            )
            
            ast_adjusted = ast_projection
            
            consistency = self._calculate_consistency(recent_games, ['AST'])
            trending_up = last5_ast > season_ast * 1.05
            
            return {
                'player_name': season_stats['player_name'],
                'team': season_stats['team'],
                'stat_type': 'AST',
                'projection': round(ast_adjusted, 1),
                'confidence': consistency,
                'trending_up': trending_up,
                'back_to_back': is_back_to_back
            }
            
        except Exception as e:
            print(f"Error calculando asistencias para jugador {player_id}: {e}")
            return {}
    
    def _calculate_consistency(self, recent_games: pd.DataFrame, stat_columns: List[str]) -> float:
        """
        Calcula un score de consistencia (0-100) basado en la desviación estándar.
        
        Una menor desviación = mayor consistencia = mayor confianza en la proyección.
        
        Args:
            recent_games: DataFrame con juegos recientes
            stat_columns: Columnas de estadísticas a evaluar
            
        Returns:
            Score de confianza de 0 a 100
        """
        if recent_games.empty:
            return 50.0  # Confianza neutral
        
        try:
            # Calcular coeficiente de variación para cada estadística
            cv_scores = []
            for col in stat_columns:
                if col in recent_games.columns:
                    mean = recent_games[col].mean()
                    std = recent_games[col].std()
                    
                    if mean > 0:
                        cv = (std / mean) * 100  # Coeficiente de variación
                        # Invertir: menor variación = mayor score
                        consistency_score = max(0, 100 - cv)
                        cv_scores.append(consistency_score)
            
            # Promedio de consistencia de todas las estadísticas
            if cv_scores:
                return round(np.mean(cv_scores), 1)
            else:
                return 50.0
                
        except Exception as e:
            print(f"Error calculando consistencia: {e}")
            return 50.0
    
    def identify_good_bet(self, projection: Dict, recent_stats: Dict) -> Dict:
        """
        Identifica si una proyección es una buena apuesta basándose en:
        - Consistencia del jugador (baja variación)
        - Tendencia positiva (mejora en últimos juegos)
        - Proyección significativa
        - Confianza alta
        
        Args:
            projection: Diccionario con la proyección del motor
            recent_stats: Estadísticas de últimos 5 y 10 juegos
            
        Returns:
            Diccionario con análisis y recomendación de apuesta
        """
        if not projection or 'projection' not in projection:
            return {}
        
        our_projection = projection['projection']
        confidence = projection.get('confidence', 50)
        stat_type = projection.get('stat_type', 'N/A')
        
        # Criterios para considerar una buena apuesta:
        is_good_bet = False
        bet_quality = "MALA"
        reasons = []
        
        # 1. Proyección significativa según tipo de estadística
        min_thresholds = {'PRA': 15, 'PTS': 10, 'REB': 5, 'AST': 4, 'FG3M': 2}
        min_value = min_thresholds.get(stat_type, 10)
        
        if our_projection >= min_value:
            reasons.append(f"Proyección sólida: {our_projection}")
            
            # 2. Consistencia alta (confianza > 60)
            if confidence >= 60:
                reasons.append(f"Alta consistencia: {confidence}%")
                is_good_bet = True
                bet_quality = "BUENA"
                
                # 3. Bonus por tendencia positiva
                if recent_stats and recent_stats.get('trending_up', False):
                    reasons.append("Tendencia al alza")
                    bet_quality = "EXCELENTE"
            
            # 4. Proyección muy alta incluso con consistencia media
            elif our_projection >= min_value * 2 and confidence >= 50:
                reasons.append("Proyección muy alta")
                is_good_bet = True
                bet_quality = "BUENA"
        
        # Línea sugerida: ligeramente por debajo de la proyección
        suggested_line = round(our_projection * 0.95, 1)
        
        # Rating final basado en proyección y confianza
        final_rating = (our_projection / min_value) * 30 + (confidence / 100) * 70
        
        return {
            'player_name': projection.get('player_name', 'Unknown'),
            'team': projection.get('team', 'N/A'),
            'stat_type': stat_type,
            'projection': our_projection,
            'suggested_line': suggested_line,
            'confidence': confidence,
            'bet_quality': bet_quality,
            'is_good_bet': is_good_bet,
            'reasons': reasons,
            'final_rating': round(final_rating, 2),
            'back_to_back': projection.get('back_to_back', False)
        }
    
    def analyze_game(self, game_id: str, home_team_id: int, 
                    away_team_id: int) -> List[Dict]:
        """
        Analiza un partido completo y genera todas las sugerencias de apuestas.
        
        Args:
            game_id: ID del partido
            home_team_id: ID del equipo local
            away_team_id: ID del equipo visitante
            
        Returns:
            Lista de mejores apuestas ordenadas por rating
        """
        all_bets = []
        
        print(f"\n📊 Iniciando análisis completo...")
        print(f"🔍 Cargando datos de todos los jugadores...")
        
        # Pre-cargar todas las estadísticas de una vez (mucho más eficiente)
        self.client._get_all_players_stats()
        
        # Verificar back-to-back para ambos equipos
        print("🏃 Verificando situación back-to-back...")
        home_b2b = self.client.check_back_to_back(home_team_id)
        away_b2b = self.client.check_back_to_back(away_team_id)
        
        if home_b2b:
            print("  ⚠️  Equipo local en back-to-back")
        if away_b2b:
            print("  ⚠️  Equipo visitante en back-to-back")
        
        # Obtener jugadores activos
        print("👥 Obteniendo jugadores activos...")
        active_players = self.client.get_active_players_for_game(home_team_id, away_team_id)
        
        total_players = len(active_players['home']) + len(active_players['away'])
        print(f"✅ {len(active_players['home'])} jugadores locales, {len(active_players['away'])} visitantes")
        
        # Analizar jugadores del equipo local
        print(f"\n🏠 Analizando equipo local...")
        analyzed = 0
        home_players_count = len(active_players['home'])
        for player_id in active_players['home']:  # Todos los jugadores
            analyzed += 1
            
            # PRA
            pra = self.calculate_pra_projection(player_id, away_team_id, home_b2b)
            if pra and pra.get('projection', 0) > 0:
                player_name = pra.get('player_name', 'Unknown')
                pts_comp = pra.get('components', {}).get('pts', 0)
                reb_comp = pra.get('components', {}).get('reb', 0)
                ast_comp = pra.get('components', {}).get('ast', 0)
                projection = pra.get('projection', 0)
                confidence = pra.get('confidence', 0)
                
                print(f"  [{analyzed}/{home_players_count}] {player_name}")
                print(f"    📊 PRA: {projection} (Pts:{pts_comp} + Reb:{reb_comp} + Ast:{ast_comp}) | Conf: {confidence:.0f}%")
                
                recent_stats = {'trending_up': pra.get('trending_up', False)}
                bet_analysis = self.identify_good_bet(pra, recent_stats)
                if bet_analysis.get('is_good_bet'):
                    all_bets.append(bet_analysis)
                    quality = bet_analysis['bet_quality']
                    print(f"    💰 [{quality}] PRA Over {bet_analysis['suggested_line']}")
                
                # Puntos
                pts = self.calculate_points_projection(player_id, away_team_id, home_b2b)
                if pts and pts.get('projection', 0) > 0:
                    projection = pts.get('projection', 0)
                    confidence = pts.get('confidence', 0)
                    print(f"    📊 PTS: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': pts.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(pts, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] PTS Over {bet_analysis['suggested_line']}")
                
                # Rebotes
                reb = self.calculate_rebounds_projection(player_id, away_team_id, home_b2b)
                if reb and reb.get('projection', 0) > 0:
                    projection = reb.get('projection', 0)
                    confidence = reb.get('confidence', 0)
                    print(f"    📊 REB: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': reb.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(reb, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] REB Over {bet_analysis['suggested_line']}")
                
                # Asistencias
                ast = self.calculate_assists_projection(player_id, away_team_id, home_b2b)
                if ast and ast.get('projection', 0) > 0:
                    projection = ast.get('projection', 0)
                    confidence = ast.get('confidence', 0)
                    print(f"    📊 AST: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': ast.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(ast, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] AST Over {bet_analysis['suggested_line']}")
                
                # Triples
                fg3m = self.calculate_threes_projection(player_id, away_team_id, home_b2b)
                if fg3m and fg3m.get('projection', 0) > 0:
                    projection = fg3m.get('projection', 0)
                    confidence = fg3m.get('confidence', 0)
                    print(f"    📊 3PT: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': fg3m.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(fg3m, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] 3PT Over {bet_analysis['suggested_line']}")
        
        # Analizar jugadores del equipo visitante
        print(f"\n✈️  Analizando equipo visitante...")
        analyzed = 0
        away_players_count = len(active_players['away'])
        for player_id in active_players['away']:  # Todos los jugadores
            analyzed += 1
            
            pra = self.calculate_pra_projection(player_id, home_team_id, away_b2b)
            if pra and pra.get('projection', 0) > 0:
                player_name = pra.get('player_name', 'Unknown')
                pts_comp = pra.get('components', {}).get('pts', 0)
                reb_comp = pra.get('components', {}).get('reb', 0)
                ast_comp = pra.get('components', {}).get('ast', 0)
                projection = pra.get('projection', 0)
                confidence = pra.get('confidence', 0)
                
                print(f"  [{analyzed}/{away_players_count}] {player_name}")
                print(f"    📊 PRA: {projection} (Pts:{pts_comp} + Reb:{reb_comp} + Ast:{ast_comp}) | Conf: {confidence:.0f}%")
                
                recent_stats = {'trending_up': pra.get('trending_up', False)}
                bet_analysis = self.identify_good_bet(pra, recent_stats)
                if bet_analysis.get('is_good_bet'):
                    all_bets.append(bet_analysis)
                    quality = bet_analysis['bet_quality']
                    print(f"    💰 [{quality}] PRA Over {bet_analysis['suggested_line']}")
                
                # Puntos
                pts = self.calculate_points_projection(player_id, home_team_id, away_b2b)
                if pts and pts.get('projection', 0) > 0:
                    projection = pts.get('projection', 0)
                    confidence = pts.get('confidence', 0)
                    print(f"    📊 PTS: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': pts.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(pts, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] PTS Over {bet_analysis['suggested_line']}")
                
                # Rebotes
                reb = self.calculate_rebounds_projection(player_id, home_team_id, away_b2b)
                if reb and reb.get('projection', 0) > 0:
                    projection = reb.get('projection', 0)
                    confidence = reb.get('confidence', 0)
                    print(f"    📊 REB: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': reb.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(reb, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] REB Over {bet_analysis['suggested_line']}")
                
                # Asistencias
                ast = self.calculate_assists_projection(player_id, home_team_id, away_b2b)
                if ast and ast.get('projection', 0) > 0:
                    projection = ast.get('projection', 0)
                    confidence = ast.get('confidence', 0)
                    print(f"    📊 AST: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': ast.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(ast, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] AST Over {bet_analysis['suggested_line']}")
                
                # Triples
                fg3m = self.calculate_threes_projection(player_id, home_team_id, away_b2b)
                if fg3m and fg3m.get('projection', 0) > 0:
                    projection = fg3m.get('projection', 0)
                    confidence = fg3m.get('confidence', 0)
                    print(f"    📊 3PT: {projection} | Conf: {confidence:.0f}%")
                    
                    recent_stats = {'trending_up': fg3m.get('trending_up', False)}
                    bet_analysis = self.identify_good_bet(fg3m, recent_stats)
                    if bet_analysis.get('is_good_bet'):
                        all_bets.append(bet_analysis)
                        quality = bet_analysis['bet_quality']
                        print(f"    💰 [{quality}] 3PT Over {bet_analysis['suggested_line']}")
        
        # Ordenar por rating final (mejores primero)
        all_bets.sort(key=lambda x: x.get('final_rating', 0), reverse=True)
        
        print(f"\n✅ Análisis completado: {len(all_bets)} oportunidades encontradas")
        
        return all_bets  # Retornar todas las apuestas encontradas