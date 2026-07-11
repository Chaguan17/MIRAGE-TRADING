# 💻 Dashboard Frontend — Mirage Trading

Este es el frontend interactivo para el monitoreo y control en tiempo real del bot **Mirage Trading**, construido utilizando **React**, **Vite** y **TailwindCSS/Vanilla CSS**.

---

## 🚀 Características Principales

1. **Monitoreo en Tiempo Real (WebSockets):** Conexión viva al backend a través de WebSockets que recibe actualizaciones de ticks de Binance y sincroniza los precios sin recargar la página.
2. **Gráfico Financiero Interactivo (TradingView):** Dibuja velas en tiempo real utilizando la librería `@lightweight-charts` de TradingView, graficando de forma dinámica los niveles de entrada, Take Profit (TP) y Stop Loss (SL) de cada operación activa.
3. **Control Bidireccional:** Botón de "Panic Sell" para liquidar posiciones abiertas inmediatamente y frenar la operativa del bot.
4. **Configuración en Vivo (Glassmorphic Settings):** Interfaz limpia y moderna para encender/apagar estrategias, ajustar el riesgo por operación, apalancamiento, DCA y stops dinámicos sin tocar código en el servidor.

---

## 🛠️ Instalación y Configuración

### 1. Requisitos Previos
* Tener instalado **Node.js** (versión 18 o superior).

### 2. Instalación de Dependencias
Ejecuta el siguiente comando en este directorio (`frontend/`):
```bash
npm install
```

### 3. Variables de Entorno
Crea un archivo `.env` en la raíz del frontend (o renombra `.env.example`) y configura la URL del API del Backend:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🏃 Ejecución en Desarrollo

Para iniciar el servidor de desarrollo local con recarga rápida (HMR):
```bash
npm run dev
```
El panel estará disponible de forma predeterminada en `http://localhost:5173`.

---

## 🐳 Despliegue con Docker

El frontend viene preconfigurado con un `Dockerfile` que compila la aplicación en producción y la sirve a través de un servidor ligero **Nginx**.

Para compilar y correr de forma aislada:
```bash
docker build -t mirage-frontend .
docker run -p 5173:80 --name mirage-frontend mirage-frontend
```
*(Nota: Para el flujo completo de producción se recomienda utilizar el archivo `docker-compose.yml` en la raíz del proyecto).*
