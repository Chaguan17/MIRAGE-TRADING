"""
executor.py — Mirage Trading
Ejecución real de órdenes en Binance Futures.
Actualmente en modo DRY RUN — loggea las órdenes sin ejecutarlas.
Cambiar DRY_RUN = False para activar ejecución real.
"""
import logging
import config

logger = logging.getLogger(__name__)

DRY_RUN = True  # ← Cambiar a False para dinero real


def execute_trade(client, symbol, action, size, sl=None, tp=None):
    """
    Envía una orden a Binance Futures.
    
    Args:
        client: instancia de MirageBinance
        symbol: par de trading (ej: 'BTCUSDT')
        action: 'LONG' o 'SHORT'
        size: cantidad de contratos
        sl: precio de stop loss (opcional)
        tp: precio de take profit (opcional)
    
    Returns:
        dict con la respuesta de Binance, o None si falla
    """
    side = 'buy' if action == 'LONG' else 'sell'

    if DRY_RUN:
        logger.info(
            f"[DRY RUN] Orden simulada: {side.upper()} {size} {symbol} | "
            f"SL={sl} | TP={tp}"
        )
        return {"dry_run": True, "symbol": symbol, "side": side, "size": size}

    try:
        # Orden de mercado principal
        order = client.client.create_order(
            symbol=symbol,
            side=side.upper(),
            type='MARKET',
            quantity=size,
        )
        logger.info(f"✅ Orden ejecutada: {side.upper()} {size} {symbol} | ID: {order.get('orderId')}")

        # Stop Loss
        if sl is not None:
            sl_side = 'sell' if action == 'LONG' else 'buy'
            client.client.create_order(
                symbol=symbol,
                side=sl_side.upper(),
                type='STOP_MARKET',
                stopPrice=round(sl, 2),
                closePosition=True,
            )
            logger.info(f"🛡️  SL colocado en {sl}")

        # Take Profit
        if tp is not None:
            tp_side = 'sell' if action == 'LONG' else 'buy'
            client.client.create_order(
                symbol=symbol,
                side=tp_side.upper(),
                type='TAKE_PROFIT_MARKET',
                stopPrice=round(tp, 2),
                closePosition=True,
            )
            logger.info(f"🎯 TP colocado en {tp}")

        return order

    except Exception as e:
        logger.error(f"❌ Error ejecutando orden {side.upper()} en {symbol}: {e}")
        return None


def close_position(client, symbol, action, size):
    """
    Cierra una posición existente en Binance Futures.
    
    Args:
        client: instancia de MirageBinance
        symbol: par de trading
        action: acción original ('LONG' o 'SHORT')
        size: tamaño de la posición a cerrar
    """
    # Para cerrar un LONG se vende, para cerrar un SHORT se compra
    close_side = 'sell' if action == 'LONG' else 'buy'

    if DRY_RUN:
        logger.info(f"[DRY RUN] Cierre simulado: {close_side.upper()} {size} {symbol}")
        return {"dry_run": True, "closed": True}

    try:
        order = client.client.create_order(
            symbol=symbol,
            side=close_side.upper(),
            type='MARKET',
            quantity=size,
            reduceOnly=True,
        )
        logger.info(f"✅ Posición cerrada: {symbol} | ID: {order.get('orderId')}")
        return order

    except Exception as e:
        logger.error(f"❌ Error cerrando posición en {symbol}: {e}")
        return None


def cancel_all_orders(client, symbol):
    """Cancela todas las órdenes abiertas de un símbolo."""
    if DRY_RUN:
        logger.info(f"[DRY RUN] Cancelación simulada de órdenes en {symbol}")
        return True

    try:
        client.client.cancel_all_orders(symbol=symbol)
        logger.info(f"🧹 Órdenes canceladas para {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Error cancelando órdenes en {symbol}: {e}")
        return False