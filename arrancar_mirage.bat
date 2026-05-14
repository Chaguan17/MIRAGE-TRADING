@echo off
title Lanzador Mirage Terminal
echo 🚀 Iniciando el ecosistema Mirage Trading...

:: 1. Arrancar el cerebro del Bot
echo 🤖 Encendiendo el motor (main.py)...
start "Mirage: Motor Bot" cmd /k "cd Backend && call venv\Scripts\activate && python main.py"

:: 2. Arrancar la API de FastAPI
echo 🔌 Levantando la API en el puerto 8000...
start "Mirage: Servidor API" cmd /k "cd Backend && call venv\Scripts\activate && uvicorn api:app --port 8000 --reload"

:: 3. Arrancar la interfaz de React
echo 🎨 Abriendo el Dashboard web...
start "Mirage: Frontend React" cmd /k "cd mirage-dashboard && npm run dev"

echo.
echo ✅ ¡Todo listo! Las 3 terminales se han abierto de forma independiente.
echo Puedes cerrar esta ventana.
pause