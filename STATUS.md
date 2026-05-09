🟢 SPRINT 1: Cimentación y Autonomía Base (COMPLETADO)
Objetivo: Establecer la infraestructura de red y el "Sistema Nervioso" básico.

Hitos:

Conexión blindada a la API de Binance Futures (Manejo de IP, RecvWindow, Autenticación).

Implementación de Paper Trading (Simulación de alta fidelidad con datos reales).

Creación del Motor de Datos (Data Engine) para extraer features iniciales (RSI, EMA, ATR).

Nacimiento del Cerebro (Brain): Implementación del modelo predictivo base (Random Forest).

🟡 SPRINT 2: Supervivencia y Bucle de Retroalimentación (EN PROCESO)
Objetivo: Enseñar al bot a no quebrar y a registrar sus propios resultados.

Hitos:

Gestión de Riesgo: Position Sizing dinámico basado en % de capital.

Scale-In (Promediado): Múltiples entradas basadas en volatilidad (ATR) para mejorar el Breakeven.

Hot-Reloading: Asimilación de nuevo código en caliente sin reiniciar el sistema.

Trade Tracker (Feedback Loop): Dashboard en vivo y registro de operaciones en CSV para tener datos etiquetados de éxito/fracaso.