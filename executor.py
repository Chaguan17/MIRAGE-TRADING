# executor.py
def execute_trade(client, symbol, action, amount):
    side = 'buy' if action == 1 else 'sell'
    
    try:
        # Ejemplo de orden a mercado en futuros
        order = client.create_market_order(symbol, side, amount)
        print(f"🔥 Orden ejecutada: {side} en {symbol}")
        return order
    except Exception as e:
        print(f"❌ Error en ejecución: {e}")
        return None