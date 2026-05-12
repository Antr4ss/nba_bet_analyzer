
from datetime import datetime
from nba_api.stats.endpoints import scoreboardv3
from nba_api.stats.endpoints import boxscorev2


# ==========================================
# OBTENER PARTIDOS DE HOY
# ==========================================

today = datetime.now().strftime("%Y-%m-%d")

scoreboard = scoreboardv3.ScoreboardV3(
    game_date=today
).get_dict()

games = scoreboard["scoreboard"]["games"]

# ==========================================
# MOSTRAR PARTIDOS
# ==========================================

print("\nPARTIDOS NBA")
print("=" * 60)

for i, game in enumerate(games):

    away = game["awayTeam"]["teamTricode"]
    home = game["homeTeam"]["teamTricode"]

    status = game["gameStatusText"]

    print(f"{i} -> {away} vs {home} | {status}")

# ==========================================
# ELEGIR PARTIDO
# ==========================================

choice = int(input("\nSelecciona un partido: "))

selected_game = games[choice]

game_id = str(selected_game["gameId"])

# ==========================================
# LIVE TRACKER
# ==========================================

