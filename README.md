# 🏀 NBA Betting Analyzer Pro

Sistema completo de análisis y predicción de apuestas NBA en tiempo real. Utiliza datos oficiales de la NBA para generar proyecciones estadísticas avanzadas y detectar oportunidades de valor en el mercado de apuestas.

## 🎯 Características Principales

### ✅ Sincronización Automática de Datos
- Detección automática de partidos del día usando fecha actual
- Filtro en tiempo real de jugadores lesionados (OUT)
- Carga de estadísticas de temporada y tendencias recientes

### 📊 Motor de Predicción Avanzado
- **Cálculo de Mercados**: PRA, Puntos, Rebotes, Asistencias, Triples
- **Algoritmo de Ventaja (Edge)**: Compara proyecciones vs líneas de mercado
- **Ajuste por Rival**: Factoriza el Defensive Rating del oponente
- **Detección de Back-to-Back**: Penalización por fatiga (-8%)
- **Análisis de Tendencias**: Últimos 5 y 10 juegos con pesos específicos

### 🎨 Interfaz Interactiva
- Selector visual de partidos
- Ranking de mejores apuestas por confianza
- Tablas detalladas con estadísticas de jugadores
- Exportación de análisis a CSV
- Integración preparada para análisis con Gemini AI

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- pip (gestor de paquetes)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
```bash
cd nba-betting-analyzer
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv

# Activar en Windows
venv\Scripts\activate

# Activar en Mac/Linux
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

## 📖 Estructura del Proyecto

```
nba-betting-analyzer/
│
├── api_client.py       # Cliente para NBA API (obtención de datos)
├── engine.py           # Motor de cálculo y predicciones
├── main.py             # Backend FastAPI (REST API)
├── interface.py        # Frontend Streamlit (UI interactiva)
├── requirements.txt    # Dependencias del proyecto
└── README.md          # Este archivo
```

## 🎮 Uso del Sistema

### Paso 1: Iniciar el Backend (FastAPI)

Abrir una terminal y ejecutar:

```bash
python main.py
```

O alternativamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en:
- API: `http://localhost:8000`
- Documentación interactiva: `http://localhost:8000/docs`

### Paso 2: Iniciar el Frontend (Streamlit)

Abrir una **segunda terminal** y ejecutar:

```bash
streamlit run interface.py
```

La interfaz se abrirá automáticamente en tu navegador en:
- URL: `http://localhost:8501`

### Paso 3: Usar la Aplicación

1. **Ver partidos del día**: La aplicación carga automáticamente todos los partidos programados
2. **Seleccionar partido**: Usa el selector desplegable para elegir el encuentro a analizar
3. **Generar análisis**: Haz clic en "Analizar Partido"
4. **Explorar resultados**:
   - Pestaña "Mejores Apuestas": Top 5 oportunidades con mayor valor
   - Pestaña "Todas las Oportunidades": Tabla completa con filtros
   - Pestaña "Análisis Táctico": Insights del partido con IA

## 🧮 Cómo Funciona el Algoritmo

### 1. Recopilación de Datos
```python
# Para cada jugador activo (no lesionado):
- Estadísticas de temporada (promedio)
- Últimos 5 juegos (tendencia corto plazo)
- Últimos 10 juegos (tendencia medio plazo)
- Verificación de back-to-back
```

### 2. Cálculo de Proyección Base
```python
proyección = (temporada * 0.30) + (últimos_10 * 0.35) + (últimos_5 * 0.35)

# Si es back-to-back:
proyección *= 0.92  # Penalización del 8% por fatiga
```

### 3. Ajuste por Oponente
```python
factor_defensa = stats_permitidos_rival / promedio_liga

proyección_ajustada = proyección_base * factor_defensa
```

### 4. Cálculo de Ventaja (Edge)
```python
diferencia = nuestra_proyección - línea_mercado
edge_porcentaje = (diferencia / línea_mercado) * 100

# Si edge > 15%: Apuesta de VALOR
if edge > 15:
    recomendación = "OVER" o "UNDER"
else:
    recomendación = "NO BET"
```

### 5. Score de Confianza
```python
# Basado en consistencia (coeficiente de variación)
cv = desviación_estándar / media
confianza = 100 - cv

# Rating final combina edge y confianza:
rating_final = (edge * 0.6) + (confianza * 0.4)
```

## 📊 Endpoints de la API

### GET `/api/games/today`
Obtiene todos los partidos del día.

**Respuesta:**
```json
[
  {
    "game_id": "0022400123",
    "home_team": "Lakers",
    "away_team": "Celtics",
    "game_time": "2024-12-21T19:30:00",
    "home_team_id": 1610612747,
    "away_team_id": 1610612738
  }
]
```

### GET `/api/analysis/{game_id}`
Analiza un partido específico y genera sugerencias.

**Respuesta:**
```json
{
  "game_id": "0022400123",
  "home_team": "Lakers",
  "away_team": "Celtics",
  "best_bets": [
    {
      "player_name": "LeBron James",
      "stat_type": "PRA",
      "our_projection": 47.5,
      "betting_line": 42.5,
      "edge_percentage": 11.76,
      "recommended_bet": "OVER",
      "confidence": 78.3,
      "final_rating": 82.5
    }
  ],
  "total_opportunities": 8
}
```

### GET `/api/player/{player_id}`
Obtiene estadísticas de un jugador.

**Parámetros:**
- `player_id`: ID del jugador
- `stat_type`: `season`, `last5`, o `last10`

## 🔧 Configuración Avanzada

### Integración con Gemini AI (Opcional)

Para habilitar análisis táctico real con IA, editar `interface.py`:

```python
def generate_gemini_analysis(game_data: Dict) -> str:
    import google.generativeai as genai
    
    genai.configure(api_key="TU_API_KEY_AQUI")
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    Analiza tácticamente el partido {game_data['away_team']} vs {game_data['home_team']}.
    Considera matchups, ritmo de juego y tendencias recientes.
    """
    
    response = model.generate_content(prompt)
    return response.text
```

### Conectar con API de Odds Real

El sistema actualmente simula líneas de apuestas. Para datos reales:

```python
# En engine.py, método find_value_bets():
import requests

def get_real_betting_line(player_name: str, stat_type: str) -> float:
    # Ejemplo con The Odds API
    response = requests.get(
        "https://api.the-odds-api.com/v4/sports/basketball_nba/odds",
        params={"apiKey": "TU_API_KEY"}
    )
    # Parsear y retornar línea específica
    pass
```

## ⚠️ Limitaciones y Consideraciones

1. **Rate Limiting**: La NBA API tiene límites de requests (~600 por minuto)
2. **Datos en Vivo**: Algunos datos solo están disponibles cerca del juego
3. **Líneas Simuladas**: Las líneas de apuestas son estimaciones (conectar API real)
4. **Uso Responsable**: Este sistema es educativo. Apuesta con responsabilidad.

## 🐛 Solución de Problemas

### Error: "No se puede conectar con el backend"
```bash
# Verificar que FastAPI esté corriendo:
curl http://localhost:8000/health

# Si no responde, reiniciar:
python main.py
```

### Error: "ModuleNotFoundError"
```bash
# Reinstalar dependencias:
pip install -r requirements.txt --force-reinstall
```

### Error: "NBA API timeout"
```bash
# Aumentar timeout en api_client.py:
response = requests.get(url, timeout=60)  # De 30 a 60 segundos
```

## 📈 Próximas Mejoras

- [ ] Integración real con APIs de odds (The Odds API, Pinnacle)
- [ ] Soporte para más mercados (Dobles-Dobles, Triple-Dobles)
- [ ] Base de datos histórica para backtesting
- [ ] Sistema de notificaciones en tiempo real
- [ ] Dashboard con gráficos de rendimiento
- [ ] Machine Learning para mejorar proyecciones

## 📄 Licencia

Este proyecto es de código abierto bajo licencia MIT. Úsalo libremente para fines educativos.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork del proyecto
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📞 Soporte

Para preguntas o problemas, abrir un issue en el repositorio del proyecto.

---

**Desarrollado con ❤️ para la comunidad NBA**