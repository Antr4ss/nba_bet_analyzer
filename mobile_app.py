"""
mobile_app.py
Aplicación móvil NBA Betting Analyzer con Flet.
Diseño moderno inspirado en la NBA con colores dinámicos.
"""

import flet as ft
import requests
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
# Para emulador Android usa: "http://10.0.2.2:8000"
# Para dispositivo físico usa la IP de tu PC: "http://192.168.x.x:8000"
# Para desarrollo en PC usa: "http://localhost:8000"
#API_URL = "http://localhost:8000"
API_URL = " https://mixible-unbumptiously-alexia.ngrok-free.dev"

# Colores NBA
NBA_BLUE = "#17408B"
NBA_RED = "#C9082A"
NBA_ORANGE = "#F58426"
NBA_GOLD = "#FDB927"
NBA_BLACK = "#1D1D1D"
NBA_WHITE = "#FFFFFF"
NBA_GRAY = "#707070"
CARD_BG = "#252525"
SURFACE_BG = "#1A1A1A"

# Mapeo de nombres de equipos a abreviaciones de ESPN para logos a COLOR
TEAM_ABBREV = {
    "Atlanta Hawks": "atl",
    "Boston Celtics": "bos",
    "Brooklyn Nets": "bkn",
    "Charlotte Hornets": "cha",
    "Chicago Bulls": "chi",
    "Cleveland Cavaliers": "cle",
    "Dallas Mavericks": "dal",
    "Denver Nuggets": "den",
    "Detroit Pistons": "det",
    "Golden State Warriors": "gs",
    "Houston Rockets": "hou",
    "Indiana Pacers": "ind",
    "LA Clippers": "lac",
    "Los Angeles Clippers": "lac",
    "Los Angeles Lakers": "lal",
    "LA Lakers": "lal",
    "Memphis Grizzlies": "mem",
    "Miami Heat": "mia",
    "Milwaukee Bucks": "mil",
    "Minnesota Timberwolves": "min",
    "New Orleans Pelicans": "no",
    "New York Knicks": "ny",
    "Oklahoma City Thunder": "okc",
    "Orlando Magic": "orl",
    "Philadelphia 76ers": "phi",
    "Phoenix Suns": "phx",
    "Portland Trail Blazers": "por",
    "Sacramento Kings": "sac",
    "San Antonio Spurs": "sa",
    "Toronto Raptors": "tor",
    "Utah Jazz": "utah",
    "Washington Wizards": "wsh",
}

def get_team_logo_url(team_name: str) -> str:
    """Obtiene la URL del logo del equipo usando ESPN CDN (logos a COLOR)."""
    abbrev = TEAM_ABBREV.get(team_name)
    if abbrev:
        # ESPN CDN - logos PNG a color
        return f"https://a.espncdn.com/i/teamlogos/nba/500/{abbrev}.png"
    # Fallback: intentar buscar por coincidencia parcial
    for name, ab in TEAM_ABBREV.items():
        if team_name in name or name in team_name:
            return f"https://a.espncdn.com/i/teamlogos/nba/500/{ab}.png"
    return ""

def get_player_image_url(player_id) -> str:
    """Obtiene la URL de la foto del jugador."""
    if not player_id:
        return ""
    # Convertir a int si es string
    try:
        pid = int(player_id)
    except (ValueError, TypeError):
        return ""
    # NBA CDN para fotos de jugadores
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"

# ============================================================================
# FUNCIONES DE API
# ============================================================================
def check_backend_health() -> bool:
    """Verifica que el backend esté operativo."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_todays_games(date: str = None) -> List[Dict]:
    """Obtiene los partidos del día desde el backend."""
    try:
        params = {}
        if date:
            params['date'] = date
        response = requests.get(f"{API_URL}/api/games/today", params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def analyze_game(game_id: str, date: str = None) -> Dict:
    """Solicita el análisis completo de un partido al backend."""
    try:
        params = {}
        if date:
            params['date'] = date
        response = requests.get(f"{API_URL}/api/analysis/{game_id}", params=params, timeout=720)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


def get_live_game_stats(game_id: str) -> Dict:
    """Obtiene estadísticas en tiempo real de un partido."""
    try:
        response = requests.get(f"{API_URL}/api/live/game/{game_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception:
        return {}


def get_player_gamelog(player_id: int) -> List[Dict]:
    """Obtiene los últimos partidos de un jugador."""
    try:
        response = requests.get(
            f"{API_URL}/api/player/{player_id}",
            params={'stat_type': 'gamelog', 'last_n': 10},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def format_game_time(utc_time_str: str) -> str:
    """Formatea la hora del partido."""
    if not utc_time_str or utc_time_str == 'TBD':
        return 'Por definir'
    try:
        from dateutil import parser, tz
        utc_time = parser.parse(utc_time_str)
        to_zone = tz.gettz('America/New_York')
        local_time = utc_time.astimezone(to_zone)
        return local_time.strftime('%I:%M %p ET')
    except Exception:
        return utc_time_str


# ============================================================================
# COMPONENTES UI REUTILIZABLES
# ============================================================================
def create_gradient_container(content, colors=[NBA_BLUE, NBA_RED], height=None, border_radius=15):
    """Crea un contenedor con efecto gradiente simulado."""
    return ft.Container(
        content=content,
        height=height,
        border_radius=border_radius,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=colors,
        ),
        padding=15,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=10,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        ),
    )


def create_stat_chip(label: str, value: str, color: str = NBA_GOLD):
    """Crea un chip de estadística."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(label, size=10, color=NBA_GRAY, weight=ft.FontWeight.W_500),
                ft.Text(value, size=16, color=color, weight=ft.FontWeight.BOLD),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.1, NBA_WHITE),
    )


def create_quality_badge(quality: str):
    """Crea un badge según la calidad de la apuesta."""
    colors = {
        'EXCELENTE': (ft.Colors.GREEN_400, ft.Colors.GREEN_900),
        'BUENA': (NBA_GOLD, NBA_ORANGE),
        'MALA': (ft.Colors.RED_400, ft.Colors.RED_900),
    }
    bg_color, text_color = colors.get(quality, (NBA_GRAY, NBA_WHITE))
    
    return ft.Container(
        content=ft.Text(quality, size=11, color=NBA_WHITE, weight=ft.FontWeight.BOLD),
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=20,
        bgcolor=bg_color,
    )


# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================
def main(page: ft.Page):
    # Configuración de la página
    page.title = "NBA Bet Analyzer"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = SURFACE_BG
    page.padding = 0
    page.window.width = 400
    page.window.height = 800
    
    # Estado de la aplicación
    current_games: List[Dict] = []
    current_analysis: Dict = {}
    selected_game: Dict = {}
    selected_date: str = datetime.now().strftime('%Y-%m-%d')
    current_tab_index: int = 0
    
    # ========================================================================
    # VISTAS
    # ========================================================================
    
    # Vista de carga inicial
    loading_view = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(color=NBA_ORANGE, stroke_width=4),
                ft.Text("Cargando...", color=NBA_WHITE, size=14),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=15,
        ),
        expand=True,
        alignment=ft.Alignment(0, 0),
    )
    
    # Contenedor principal de contenido
    main_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
    
    # ========================================================================
    # FUNCIONES DE NAVEGACIÓN Y ACTUALIZACIÓN
    # ========================================================================
    
    def show_snackbar(message: str, color: str = NBA_WHITE):
        """Muestra un mensaje temporal."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=color),
            bgcolor=CARD_BG,
            duration=3000,
        )
        page.snack_bar.open = True
        page.update()
    
    def show_loading():
        """Muestra indicador de carga."""
        main_content.controls.clear()
        main_content.controls.append(loading_view)
        page.update()
    
    def build_game_card(game: Dict):
        """Construye una tarjeta de partido."""
        formatted_time = format_game_time(game.get('game_time', 'TBD'))
        away_logo = get_team_logo_url(game['away_team'])
        home_logo = get_team_logo_url(game['home_team'])
        
        return ft.Container(
            content=ft.Column(
                [
                    # Header del partido
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SPORTS_BASKETBALL, color=NBA_ORANGE, size=24),
                            ft.Text("NBA", color=NBA_GRAY, size=12, weight=ft.FontWeight.W_500),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, NBA_WHITE)),
                    
                    # Equipos
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Image(
                                                src=away_logo,
                                                width=40,
                                                height=40,
                                                fit="contain",
                                                error_content=ft.Text("🏀", size=28),
                                            ),
                                            width=50,
                                            height=50,
                                            border_radius=25,
                                            bgcolor=ft.Colors.with_opacity(0.2, NBA_BLUE),
                                            alignment=ft.Alignment(0, 0),
                                            padding=5,
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(game['away_team'], size=16, color=NBA_WHITE, weight=ft.FontWeight.BOLD),
                                                ft.Text("Visitante", size=11, color=NBA_GRAY),
                                            ],
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                ft.Row(
                                    [
                                        ft.Text("@", size=18, color=NBA_ORANGE, weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Image(
                                                src=home_logo,
                                                width=40,
                                                height=40,
                                                fit="contain",
                                                error_content=ft.Text("🏀", size=28),
                                            ),
                                            width=50,
                                            height=50,
                                            border_radius=25,
                                            bgcolor=ft.Colors.with_opacity(0.2, NBA_RED),
                                            alignment=ft.Alignment(0, 0),
                                            padding=5,
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(game['home_team'], size=16, color=NBA_WHITE, weight=ft.FontWeight.BOLD),
                                                ft.Text("Local", size=11, color=NBA_GRAY),
                                            ],
                                            spacing=2,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.symmetric(vertical=10),
                    ),
                    
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, NBA_WHITE)),
                    
                    # Footer con hora y botón
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.ACCESS_TIME, color=NBA_GRAY, size=16),
                                    ft.Text(formatted_time, size=12, color=NBA_GRAY),
                                ],
                                spacing=5,
                            ),
                            ft.ElevatedButton(
                                "Analizar",
                                icon=ft.Icons.ANALYTICS,
                                bgcolor=NBA_ORANGE,
                                color=NBA_WHITE,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                on_click=lambda e, g=game: on_analyze_game(g),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=10,
            ),
            padding=15,
            border_radius=15,
            bgcolor=CARD_BG,
            margin=ft.margin.only(bottom=12),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            ),
        )
    
    def build_bet_card(bet: Dict, rank: int):
        """Construye una tarjeta de apuesta sugerida."""
        confidence = bet.get('confidence', 50)
        rating = bet.get('final_rating', 0)
        bet_quality = bet.get('bet_quality', 'MALA')
        reasons = bet.get('reasons', [])[:3]  # Máximo 3 razones
        player_id = bet.get('player_id')
        player_image = get_player_image_url(player_id) if player_id else ""
        team_name = bet.get('team', '')
        team_logo = get_team_logo_url(team_name) if team_name else ""
        
        # Emoji de ranking
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_display = rank_icons.get(rank, f"#{rank}")
        
        # Color de la barra de confianza
        conf_color = ft.Colors.GREEN_400 if confidence >= 70 else NBA_GOLD if confidence >= 50 else ft.Colors.RED_400
        
        return ft.Container(
            content=ft.Column(
                [
                    # Header con foto del jugador
                    ft.Row(
                        [
                            ft.Text(rank_display, size=24),
                            # Foto del jugador
                            ft.Container(
                                content=ft.Image(
                                    src=player_image,
                                    width=50,
                                    height=50,
                                    fit="cover",
                                    border_radius=ft.border_radius.all(25),
                                    error_content=ft.Icon(ft.Icons.PERSON, color=NBA_GRAY, size=30),
                                ) if player_image else ft.Icon(ft.Icons.PERSON, color=NBA_GRAY, size=30),
                                width=55,
                                height=55,
                                border_radius=28,
                                bgcolor=ft.Colors.with_opacity(0.3, NBA_BLUE),
                                alignment=ft.Alignment(0, 0),
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        bet['player_name'],
                                        size=16,
                                        color=NBA_WHITE,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Image(
                                                src=team_logo,
                                                width=16,
                                                height=16,
                                                fit="contain",
                                            ) if team_logo else ft.Container(),
                                            ft.Text(
                                                f"{bet.get('team', 'N/A')} • {bet['stat_type']}",
                                                size=12,
                                                color=NBA_GRAY,
                                            ),
                                        ],
                                        spacing=5,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            create_quality_badge(bet_quality),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, NBA_WHITE)),
                    
                    # Stats principales
                    ft.Row(
                        [
                            create_stat_chip("Proyección", f"{bet['projection']:.1f}"),
                            create_stat_chip("Línea", f"{bet['suggested_line']:.1f}", NBA_ORANGE),
                            create_stat_chip("Rating", f"{rating:.0f}", conf_color),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                    
                    # Barra de confianza
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("Confianza", size=11, color=NBA_GRAY),
                                        ft.Text(f"{confidence:.0f}%", size=11, color=conf_color, weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.ProgressBar(
                                    value=confidence / 100,
                                    color=conf_color,
                                    bgcolor=ft.Colors.with_opacity(0.2, NBA_WHITE),
                                    height=6,
                                    border_radius=3,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=ft.padding.only(top=10),
                    ),
                    
                    # Razones (expandible)
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Razones:", size=11, color=NBA_GRAY, weight=ft.FontWeight.W_500),
                                *[
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=14),
                                            ft.Text(reason, size=11, color=NBA_WHITE, expand=True),
                                        ],
                                        spacing=6,
                                    )
                                    for reason in reasons
                                ],
                            ],
                            spacing=4,
                        ),
                        padding=ft.padding.only(top=10),
                        visible=len(reasons) > 0,
                    ),
                    
                    # Indicador Back-to-Back
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.WARNING_AMBER if bet.get('back_to_back', False) else ft.Icons.CHECK,
                                    color=NBA_ORANGE if bet.get('back_to_back', False) else ft.Colors.GREEN_400,
                                    size=14,
                                ),
                                ft.Text(
                                    "Back-to-Back" if bet.get('back_to_back', False) else "Descansado",
                                    size=11,
                                    color=NBA_ORANGE if bet.get('back_to_back', False) else ft.Colors.GREEN_400,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=ft.padding.only(top=8),
                    ),
                ],
                spacing=8,
            ),
            padding=15,
            border_radius=15,
            bgcolor=CARD_BG,
            margin=ft.margin.only(bottom=12),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, NBA_GOLD)),
        )
    
    def build_injury_row(injury: Dict):
        """Construye una fila de lesión con foto del jugador."""
        status = injury.get('Current_Status', '') or injury.get('status', 'Unknown')
        status_color = ft.Colors.RED_400 if status == 'Out' else NBA_ORANGE if status in ['Doubtful', 'Questionable'] else ft.Colors.GREEN_400
        
        # Obtener foto del jugador - usar HEADSHOT de ESPN directamente si está disponible
        player_image = injury.get('HEADSHOT', '') or injury.get('headshot', '')
        
        # Si no hay headshot directo, intentar con player_id
        if not player_image:
            player_id = (
                injury.get('PLAYER_ID') or 
                injury.get('player_id') or 
                injury.get('PersonId') or
                injury.get('PERSON_ID') or
                injury.get('id')
            )
            player_image = get_player_image_url(player_id) if player_id else ""
        
        # Obtener logo del equipo - buscar en múltiples campos
        team_name = (
            injury.get('TEAM_NAME', '') or 
            injury.get('team_name', '') or
            injury.get('Team', '') or
            injury.get('team', '')
        )
        team_logo = get_team_logo_url(team_name) if team_name else ""
        
        return ft.Container(
            content=ft.Row(
                [
                    # Foto del jugador lesionado
                    ft.Container(
                        content=ft.Image(
                            src=player_image,
                            width=44,
                            height=44,
                            fit="cover",
                            border_radius=ft.border_radius.all(22),
                            error_content=ft.Icon(
                                ft.Icons.PERSONAL_INJURY,
                                color=status_color,
                                size=24,
                            ),
                        ) if player_image else ft.Icon(
                            ft.Icons.PERSONAL_INJURY,
                            color=status_color,
                            size=24,
                        ),
                        width=50,
                        height=50,
                        border_radius=25,
                        bgcolor=ft.Colors.with_opacity(0.2, status_color),
                        alignment=ft.Alignment(0, 0),
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        border=ft.border.all(2, status_color),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                injury.get('PLAYER_NAME') or injury.get('player_name') or injury.get('name', 'Desconocido'),
                                size=14,
                                color=NBA_WHITE,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Row(
                                [
                                    ft.Image(
                                        src=team_logo,
                                        width=14,
                                        height=14,
                                        fit="contain",
                                    ) if team_logo else ft.Container(width=0),
                                    ft.Text(
                                        team_name,
                                        size=11,
                                        color=NBA_GRAY,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Text(status, size=10, color=NBA_WHITE, weight=ft.FontWeight.BOLD),
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                border_radius=10,
                                bgcolor=status_color,
                            ),
                            ft.Text(
                                injury.get('Comment', '')[:30] + '...' if len(injury.get('Comment', '')) > 30 else injury.get('Comment', ''),
                                size=10,
                                color=NBA_GRAY,
                            ),
                        ],
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=12,
            ),
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.05, NBA_WHITE),
            margin=ft.margin.only(bottom=8),
        )
    
    def build_live_tracker_item(bet: Dict, live_stats: Dict):
        """Construye un item del tracker en vivo."""
        player_name = bet['player_name']
        stat_type = bet['stat_type'].upper()
        target_line = bet['suggested_line']
        player_id = bet.get('player_id')
        player_image = get_player_image_url(player_id) if player_id else ""
        
        # Determinar tipo de apuesta
        bet_type = bet.get('recommended_bet', 'OVER')
        if 'recommended_bet' not in bet:
            bet_type = 'OVER' if bet['projection'] > bet['suggested_line'] else 'UNDER'
        
        # Buscar stats del jugador
        player_live_data = None
        for pid, pdata in live_stats.items():
            if pdata.get('name') == player_name or player_name in pdata.get('name', '') or pdata.get('name', '') in player_name:
                player_live_data = pdata
                break
        
        display_line = int(round(target_line))
        
        if player_live_data:
            if stat_type == 'PRA':
                current_val = player_live_data.get('pts', 0) + player_live_data.get('reb', 0) + player_live_data.get('ast', 0)
            else:
                current_val = player_live_data.get(stat_type.lower(), 0)
            
            progress = min(current_val / display_line if display_line > 0 else 0, 1.0)
            
            if bet_type == 'OVER':
                is_covered = current_val >= display_line
                status_color = ft.Colors.GREEN_400 if is_covered else NBA_ORANGE
                status_text = "✅ CUBIERTA" if is_covered else f"Faltan {display_line - current_val}"
            else:
                is_safe = current_val <= display_line
                status_color = ft.Colors.GREEN_400 if is_safe else ft.Colors.RED_400
                status_text = f"✅ Margen: {display_line - current_val}" if is_safe else "❌ PERDIDA"
        else:
            current_val = 0
            progress = 0
            status_color = NBA_GRAY
            status_text = "⏳ Esperando..."
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            # Foto del jugador en live tracker
                            ft.Container(
                                content=ft.Image(
                                    src=player_image,
                                    width=40,
                                    height=40,
                                    fit="cover",
                                    border_radius=ft.border_radius.all(20),
                                    error_content=ft.Icon(ft.Icons.PERSON, color=NBA_GRAY, size=24),
                                ) if player_image else ft.Icon(ft.Icons.PERSON, color=NBA_GRAY, size=24),
                                width=45,
                                height=45,
                                border_radius=23,
                                bgcolor=ft.Colors.with_opacity(0.3, status_color),
                                alignment=ft.Alignment(0, 0),
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            ),
                            ft.Column(
                                [
                                    ft.Text(player_name, size=14, color=NBA_WHITE, weight=ft.FontWeight.W_500),
                                    ft.Text(f"{stat_type} • Línea: {display_line} ({bet_type})", size=11, color=NBA_GRAY),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Text(
                                str(current_val),
                                size=24,
                                color=status_color,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.ProgressBar(
                        value=progress,
                        color=status_color,
                        bgcolor=ft.Colors.with_opacity(0.2, NBA_WHITE),
                        height=8,
                        border_radius=4,
                    ),
                    ft.Text(status_text, size=11, color=status_color),
                ],
                spacing=8,
            ),
            padding=12,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.05, NBA_WHITE),
            margin=ft.margin.only(bottom=8),
        )
    
    # ========================================================================
    # PANTALLAS
    # ========================================================================
    
    def build_home_screen():
        """Construye la pantalla principal con lista de partidos."""
        nonlocal current_games
        
        if not current_games:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SPORTS_BASKETBALL, color=NBA_GRAY, size=64),
                        ft.Text("No hay partidos programados", size=16, color=NBA_GRAY),
                        ft.Text(f"para el {selected_date}", size=14, color=NBA_GRAY),
                        ft.ElevatedButton(
                            "Reintentar",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: load_games(),
                            bgcolor=NBA_ORANGE,
                            color=NBA_WHITE,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=15,
                ),
                expand=True,
                alignment=ft.Alignment(0, 0),
            )
        
        game_cards = [build_game_card(game) for game in current_games]
        
        return ft.Container(
            content=ft.Column(
                [
                    # Header con fecha
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"📅 {len(current_games)} Partidos",
                                            size=18,
                                            color=NBA_WHITE,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            selected_date,
                                            size=12,
                                            color=NBA_GRAY,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CALENDAR_TODAY,
                                    icon_color=NBA_ORANGE,
                                    on_click=lambda e: show_date_picker(),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.padding.only(bottom=15),
                    ),
                    # Lista de partidos
                    *game_cards,
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=15,
            expand=True,
        )
    
    def build_analysis_screen():
        """Construye la pantalla de análisis detallado."""
        nonlocal current_analysis, selected_game
        
        if not current_analysis or not current_analysis.get('best_bets'):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SEARCH_OFF, color=NBA_GRAY, size=64),
                        ft.Text("No hay datos de análisis", size=16, color=NBA_GRAY),
                        ft.ElevatedButton(
                            "Volver",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: navigate_to_home(),
                            bgcolor=NBA_BLUE,
                            color=NBA_WHITE,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=15,
                ),
                expand=True,
                alignment=ft.Alignment(0, 0),
            )
        
        best_bets = current_analysis['best_bets'][:5]
        
        # Estado del tab seleccionado - usar contenedor mutable
        selected_tab = {"index": current_tab_index}
        
        # Contenedores para cada sección
        top_bets_content = ft.Container(
            content=ft.Column(
                [build_bet_card(bet, idx+1) for idx, bet in enumerate(best_bets)],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=15,
            visible=selected_tab["index"] == 0,
            expand=True,
        )
        
        all_bets_content = ft.Container(
            content=ft.Column(
                [build_bet_card(bet, idx+1) for idx, bet in enumerate(current_analysis['best_bets'])],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=15,
            visible=selected_tab["index"] == 1,
            expand=True,
        )
        
        injuries_content = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"🏥 {len(current_analysis.get('injuries', []))} Jugadores",
                        size=16,
                        color=NBA_WHITE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, NBA_WHITE)),
                    *[build_injury_row(inj) for inj in current_analysis.get('injuries', [])],
                ] if current_analysis.get('injuries') else [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=48),
                    ft.Text("Sin lesiones reportadas", size=14, color=ft.Colors.GREEN_400),
                ],
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER if not current_analysis.get('injuries') else ft.CrossAxisAlignment.STRETCH,
            ),
            padding=15,
            visible=selected_tab["index"] == 2,
            expand=True,
        )
        
        live_content = ft.Container(
            content=build_live_tab_content(),
            visible=selected_tab["index"] == 3,
            expand=True,
        )
        
        # Función para cambiar de tab
        def change_tab(index):
            selected_tab["index"] = index
            top_bets_content.visible = index == 0
            all_bets_content.visible = index == 1
            injuries_content.visible = index == 2
            live_content.visible = index == 3
            
            # Actualizar estilos de botones
            for i, btn in enumerate(tab_buttons):
                btn.style = ft.ButtonStyle(
                    bgcolor=NBA_ORANGE if i == index else ft.Colors.TRANSPARENT,
                    color=NBA_WHITE if i == index else NBA_GRAY,
                    shape=ft.RoundedRectangleBorder(radius=20),
                )
            page.update()
        
        # Botones de navegación de tabs
        tab_buttons = [
            ft.ElevatedButton(
                "⭐ Top",
                style=ft.ButtonStyle(
                    bgcolor=NBA_ORANGE if selected_tab["index"] == 0 else ft.Colors.TRANSPARENT,
                    color=NBA_WHITE if selected_tab["index"] == 0 else NBA_GRAY,
                    shape=ft.RoundedRectangleBorder(radius=20),
                ),
                on_click=lambda e: change_tab(0),
            ),
            ft.ElevatedButton(
                "📋 Todas",
                style=ft.ButtonStyle(
                    bgcolor=NBA_ORANGE if selected_tab["index"] == 1 else ft.Colors.TRANSPARENT,
                    color=NBA_WHITE if selected_tab["index"] == 1 else NBA_GRAY,
                    shape=ft.RoundedRectangleBorder(radius=20),
                ),
                on_click=lambda e: change_tab(1),
            ),
            ft.ElevatedButton(
                "🏥 Lesiones",
                style=ft.ButtonStyle(
                    bgcolor=NBA_ORANGE if selected_tab["index"] == 2 else ft.Colors.TRANSPARENT,
                    color=NBA_WHITE if selected_tab["index"] == 2 else NBA_GRAY,
                    shape=ft.RoundedRectangleBorder(radius=20),
                ),
                on_click=lambda e: change_tab(2),
            ),
            ft.ElevatedButton(
                "🔴 Live",
                style=ft.ButtonStyle(
                    bgcolor=NBA_ORANGE if selected_tab["index"] == 3 else ft.Colors.TRANSPARENT,
                    color=NBA_WHITE if selected_tab["index"] == 3 else NBA_GRAY,
                    shape=ft.RoundedRectangleBorder(radius=20),
                ),
                on_click=lambda e: change_tab(3),
            ),
        ]
        
        # Barra de tabs personalizada
        tabs_bar = ft.Container(
            content=ft.Row(
                tab_buttons,
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.symmetric(vertical=10, horizontal=5),
            bgcolor=CARD_BG,
        )
        
        return ft.Column(
            [
                # Header del partido
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK,
                                        icon_color=NBA_WHITE,
                                        on_click=lambda e: navigate_to_home(),
                                    ),
                                    ft.Text(
                                        f"{selected_game.get('away_team', '')} @ {selected_game.get('home_team', '')}",
                                        size=16,
                                        color=NBA_WHITE,
                                        weight=ft.FontWeight.BOLD,
                                        expand=True,
                                    ),
                                ],
                            ),
                            # Resumen rápido
                            ft.Row(
                                [
                                    create_stat_chip("Oportunidades", str(current_analysis.get('total_opportunities', 0))),
                                    create_stat_chip(
                                        "Avg Rating",
                                        f"{sum(b['final_rating'] for b in best_bets) / len(best_bets):.0f}" if best_bets else "0"
                                    ),
                                    create_stat_chip(
                                        "Alta Conf.",
                                        str(len([b for b in current_analysis['best_bets'] if b['final_rating'] >= 60]))
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=15,
                    bgcolor=CARD_BG,
                ),
                # Barra de tabs
                tabs_bar,
                # Contenido de tabs (stack)
                ft.Container(
                    content=ft.Stack(
                        [
                            top_bets_content,
                            all_bets_content,
                            injuries_content,
                            live_content,
                        ],
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    
    def build_live_tab_content():
        """Construye el contenido del tab de seguimiento en vivo."""
        live_stats = get_live_game_stats(selected_game.get('game_id', ''))
        
        if not live_stats:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SCHEDULE, color=NBA_GRAY, size=48),
                        ft.Text("El partido no ha comenzado", size=14, color=NBA_GRAY),
                        ft.Text("o no hay datos disponibles", size=12, color=NBA_GRAY),
                        ft.ElevatedButton(
                            "Actualizar",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: refresh_live_stats(),
                            bgcolor=NBA_ORANGE,
                            color=NBA_WHITE,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=15,
                expand=True,
                alignment=ft.Alignment(0, 0),
            )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("🔴 En Vivo", size=16, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                icon_color=NBA_ORANGE,
                                on_click=lambda e: refresh_live_stats(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, NBA_WHITE)),
                    *[build_live_tracker_item(bet, live_stats) for bet in current_analysis.get('best_bets', [])[:10]],
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=15,
        )
    
    # ========================================================================
    # HANDLERS DE EVENTOS
    # ========================================================================
    
    def load_games():
        """Carga los partidos del día seleccionado."""
        nonlocal current_games
        show_loading()
        
        if not check_backend_health():
            main_content.controls.clear()
            main_content.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CLOUD_OFF, color=ft.Colors.RED_400, size=64),
                            ft.Text("Sin conexión al servidor", size=18, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                            ft.Text("Asegúrate de que el backend esté corriendo", size=14, color=NBA_GRAY, text_align=ft.TextAlign.CENTER),
                            ft.Text("uvicorn main:app --reload", size=12, color=NBA_ORANGE, font_family="monospace"),
                            ft.ElevatedButton(
                                "Reintentar",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda e: load_games(),
                                bgcolor=NBA_ORANGE,
                                color=NBA_WHITE,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=15,
                    ),
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                )
            )
            page.update()
            return
        
        current_games = get_todays_games(date=selected_date)
        main_content.controls.clear()
        main_content.controls.append(build_home_screen())
        page.update()
        show_snackbar(f"✅ {len(current_games)} partidos cargados")
    
    def on_analyze_game(game: Dict):
        """Handler para analizar un partido."""
        nonlocal current_analysis, selected_game, current_tab_index
        selected_game = game
        current_tab_index = 0
        
        show_loading()
        show_snackbar(f"🔍 Analizando {game['away_team']} @ {game['home_team']}...")
        
        current_analysis = analyze_game(game['game_id'], date=selected_date)
        
        main_content.controls.clear()
        main_content.controls.append(build_analysis_screen())
        page.update()
        
        if current_analysis and current_analysis.get('best_bets'):
            show_snackbar(f"✅ {current_analysis['total_opportunities']} oportunidades encontradas", ft.Colors.GREEN_400)
        else:
            show_snackbar("⚠️ No se encontraron oportunidades", NBA_ORANGE)
    
    def navigate_to_home():
        """Navega a la pantalla principal."""
        main_content.controls.clear()
        main_content.controls.append(build_home_screen())
        page.update()
    
    def on_tab_change(index: int):
        """Handler para cambio de tab."""
        nonlocal current_tab_index
        current_tab_index = index
    
    def refresh_live_stats():
        """Refresca las estadísticas en vivo."""
        main_content.controls.clear()
        main_content.controls.append(build_analysis_screen())
        page.update()
        show_snackbar("🔄 Stats actualizadas")
    
    def show_date_picker():
        """Muestra el selector de fecha."""
        def on_date_selected(e):
            nonlocal selected_date
            if e.control.value:
                selected_date = e.control.value.strftime('%Y-%m-%d')
                load_games()
            date_picker.open = False
            page.update()
        
        def on_dismiss(e):
            date_picker.open = False
            page.update()
        
        date_picker = ft.DatePicker(
            first_date=datetime(2024, 1, 1),
            last_date=datetime(2027, 12, 31),
            on_change=on_date_selected,
            on_dismiss=on_dismiss,
        )
        page.overlay.append(date_picker)
        date_picker.open = True
        page.update()
    
    # ========================================================================
    # LAYOUT PRINCIPAL
    # ========================================================================
    
    # AppBar
    app_bar = ft.AppBar(
        leading=ft.Container(
            content=ft.Text("🏀", size=28),
            padding=ft.padding.only(left=10),
        ),
        title=ft.Text(
            "NBA Bet Analyzer",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=NBA_WHITE,
        ),
        center_title=False,
        bgcolor=NBA_BLACK,
        actions=[
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=NBA_ORANGE,
                tooltip="Actualizar",
                on_click=lambda e: load_games(),
            ),
        ],
    )
    
    # Agregar componentes a la página
    page.appbar = app_bar
    page.add(main_content)
    
    # Cargar datos iniciales
    load_games()


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    # Opciones de vista:
    # - ft.AppView.FLET_APP: Ventana nativa (por defecto)
    # - ft.AppView.WEB_BROWSER: Abre en navegador web
    ft.app(target=main)
