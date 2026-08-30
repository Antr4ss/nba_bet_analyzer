# NBA Betting Analyzer Pro

**NBA Betting Analyzer Pro** es una herramienta avanzada de análisis deportivo diseñada para identificar oportunidades de valor en el mercado de apuestas de la NBA. Utilizando datos en tiempo real, algoritmos de proyección estadística e inteligencia artificial, el sistema ofrece recomendaciones fundamentadas para Puntos, Rebotes, Asistencias y Triples.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![NBA API](https://img.shields.io/badge/NBA_API-Live-orange)

---

## Funcionalidades Principales

### 1. Análisis Estadístico Avanzado
El núcleo del sistema es un motor de proyección que calcula el rendimiento esperado de cada jugador basándose en múltiples factores temporales y contextuales.

### 2. Live Tracker (Seguimiento en Vivo)
Nueva funcionalidad que permite monitorear en tiempo real el progreso de tus apuestas sugeridas mientras se juega el partido.
- **Actualización automática:** Se conecta al *live boxscore* de la NBA.
- **Visualización intuitiva:** Barras de progreso para cada apuesta (OVER/UNDER).
- **Soporte PRA:** Cálculo automático de Puntos + Rebotes + Asistencias en tiempo real.
- **Alertas visuales:** Indicadores claros cuando una línea se cubre o se pierde.

### 3. Reporte de Lesiones Integrado
Consulta automática de fuentes externas (ESPN) para filtrar jugadores lesionados o cuestionables, evitando recomendaciones sobre jugadores que no participarán.

### 4. Detección de Tendencias y Fatiga
- **Back-to-Back:** Identifica equipos que jugaron el día anterior y aplica penalizaciones por fatiga.
- **Hot Streaks:** Detecta jugadores con tendencia al alza en sus últimos 5 partidos.

---

## Cómo Funciona el Motor de Predicción

El sistema utiliza un enfoque ponderado para calcular las proyecciones, priorizando el rendimiento reciente sobre el promedio de la temporada.

### 1. Cálculo de Proyecciones
La proyección base se calcula mediante un promedio ponderado:
- **35%** - Promedio de los últimos **5 partidos** (Forma actual).
- **35%** - Promedio de los últimos **10 partidos** (Tendencia a medio plazo).
- **30%** - Promedio de la **temporada** (Consistencia a largo plazo).

*Ajustes adicionales:*
- **Factor de Fatiga:** Si el equipo está en *back-to-back* (jugó ayer), se aplica una penalización del **-8%** a la proyección.

### 2. Línea Sugerida
El sistema calcula una línea de seguridad para las apuestas *OVER*:
- **Línea Sugerida = Proyección × 0.95**
- Esto crea un margen de seguridad del 5% para aumentar la probabilidad de éxito.

### 3. Nivel de Confianza (%)
La confianza no es subjetiva, sino matemática. Se basa en la **Consistencia** del jugador:
- Se calcula el *Coeficiente de Variación* (Desviación Estándar / Media) de los últimos juegos.
- **Menor variación = Mayor consistencia = Mayor Confianza.**
- Escala de 0 a 100%. Una confianza >60% se considera alta.

### 4. Rating Final (0-100)
Es la métrica definitiva para ordenar las mejores apuestas. Combina el valor de la proyección con la seguridad de la confianza:
- **70% del peso:** Nivel de Confianza (Seguridad).
- **30% del peso:** Magnitud de la Proyección (Valor).

### 5. Calidad de la Apuesta
El sistema etiqueta las oportunidades automáticamente:
- **EXCELENTE:** Confianza alta (>60%) + Tendencia al alza (Últimos 5 > Temporada).
- **BUENA:** Confianza alta o Proyección muy superior a la línea.
- **ARRIESGADA:** Proyección positiva pero baja consistencia.

---

## Stack Tecnológico y APIs

El proyecto está construido con una arquitectura moderna de microservicios:

- **Backend:** `FastAPI` - Manejo de lógica de negocio y endpoints REST.
- **Frontend:** `Streamlit` - Interfaz de usuario interactiva y visualización de datos.
- **Datos:**
  - `nba_api`: Fuente oficial de estadísticas, calendarios y boxscores en vivo.
  - `requests`: Scraping de reportes de lesiones (ESPN).
- **Ciencia de Datos:** `pandas` y `numpy` para manipulación y cálculo vectorial.

---

## Autenticación Institucional Oficial (OIDC)

Para integraciones de identidad, evita automatizar formularios web de login. Usa el método oficial del proveedor de identidad (OIDC/SAML/API institucional).

Este repositorio incluye un cliente OIDC oficial por Device Flow:

```bash
python official_oidc_client.py \
   --well-known "https://TU_IDP/.well-known/openid-configuration" \
   --client-id "TU_CLIENT_ID" \
   --scope "openid profile email" \
   --output oidc_result.json
```

Requisitos para que funcione:

- `client_id` registrado oficialmente por el equipo de identidad.
- Endpoint de discovery OIDC habilitado en la institución.
- Device Authorization Grant habilitado por el IdP.

Si tu IdP no habilita Device Flow, solicita Authorization Code + PKCE o la API oficial de identidad disponible en tu institución.

---

## Instalación y Uso

1. **Clonar el repositorio**
2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configurar variables de entorno:**
   Crear un archivo `.env` con las variables necesarias para apuestas y datos externos.
4. **Iniciar el Backend:**
   ```bash
   uvicorn main:app --reload
   ```
5. **Iniciar el Frontend (en otra terminal):**
   ```bash
   streamlit run interface.py
   ```

---

## Disclaimer
*Esta herramienta es solo para fines educativos y de entretenimiento. Las apuestas deportivas conllevan riesgos financieros. El autor no se hace responsable de pérdidas económicas derivadas del uso de este software. Apuesta siempre con responsabilidad.*
