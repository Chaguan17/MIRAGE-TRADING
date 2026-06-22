# Arquitectura de Mirage Trading

Mirage Trading es una plataforma de trading algorítmico automatizado, con un backend robusto en Python y un dashboard interactivo en React.

## Estructura del Proyecto

El proyecto sigue una arquitectura full-stack moderna:

```
MIRAGE-TRADING/
├── backend/          # Lógica de trading, IA y API REST
├── frontend/         # Dashboard interactivo (React/Vite)
└── docs/             # Documentación técnica
```

## Backend

El backend se encarga de analizar el mercado, tomar decisiones mediante estrategias y modelos de Machine Learning, y ejecutar órdenes en Binance.

- **`main.py`**: El bucle principal del bot. Mantiene la conexión viva y evalúa el mercado constantemente.
- **`api.py`**: API REST (FastAPI) que expone los datos y el estado del bot para ser consumidos por el dashboard, incluyendo un WebSocket.
- **`binance_api.py`**: Integración con Binance a través de `ccxt`.
- **`data_engine.py`**: Procesamiento de datos de mercado (indicadores técnicos con `pandas_ta`).
- **`strategies/`**: Estrategias de análisis técnico y de estructura de mercado.
- **`brain/`**: Motor de decisión que utiliza Machine Learning (RandomForest) y consenso entre las diferentes estrategias.
- **`risk_manager.py`**: Gestión de riesgo, control de apalancamiento y tamaño de posición (Position Sizing).

## Frontend

El frontend es un dashboard "Single Page Application" construido con React, Vite y Recharts.

- **`pages/DashboardView.jsx`**: Vista principal con KPIs, posiciones abiertas en tiempo real y últimas ejecuciones.
- **`pages/PerformanceView.jsx`**: Análisis histórico y métricas avanzadas (Sharpe, Drawdown).
- **`pages/SettingsView.jsx`**: Configuración remota del bot.
- **`hooks/useDashboardData.js`**: Hook centralizado para la gestión del estado, fetching de datos y reconexiones de WebSocket.

## Infraestructura (Docker)

El proyecto está dockerizado para garantizar su funcionamiento idéntico en cualquier entorno. Se compone de 3 servicios orquestados vía `docker-compose.yml`:

1. **`mirage-bot`**: El proceso principal que opera 24/7.
2. **`mirage-api`**: El servidor Uvicorn/FastAPI que sirve la información.
3. **`mirage-frontend`**: Servidor Nginx estático que sirve el build de React.

### Comunicación

- El **Bot** y la **API** comparten la misma base de datos SQLite y los logs mediante volúmenes de Docker (`/app/storage`).
- El **Frontend** se comunica con la API vía HTTP y WebSockets.
