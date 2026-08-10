"""
executor.py — Mirage Trading
Ejecución de órdenes en Binance Futures.
Determina automáticamente si ejecutar en Real o en Paper según client.paper_trading.
Soporta órdenes LÍMITE Post-Only (GTX Maker Fee = 0.020%) y MERCADO (Taker Fee = 0.050%).
Soporta automáticamente Modo Cobertura (Hedge Mode) y Modo Unilateral (One-Way Mode).
Conectado a notification_manager para registrar errores y confirmaciones.
"""
import logging
import config
import notification_manager as nm

logger = logging.getLogger(__name__)


def is_paper_trading(client):
    if client is not None and hasattr(client, 'paper_trading'):
        return client.paper_trading
    return True


def _safe_create_order(client, symbol, order_type, side, amount, params=None, action='LONG'):
    """
    Crea una orden en Binance. Si Binance devuelve el error -4061 (Hedge Mode setting),
    reintenta automáticamente adjuntando el parámetro positionSide ('LONG' o 'SHORT').
    """
    if params is None:
        params = {}

    pos_side = 'LONG' if action == 'LONG' else 'SHORT'

    try:
        return client.client.create_order(
            symbol=symbol,
            type=order_type,
            side=side.upper(),
            amount=amount,
            params=params
        )
    except Exception as e:
        err_str = str(e)
        if "-4061" in err_str or "position side" in err_str.lower():
            logger.info(f"🔄 Reintentando orden {symbol} con positionSide={pos_side} (Modo Cobertura detectado)...")
            hedge_params = {**params, 'positionSide': pos_side}
            return client.client.create_order(
                symbol=symbol,
                type=order_type,
                side=side.upper(),
                amount=amount,
                params=hedge_params
            )
        raise e


def execute_trade(client, symbol, action, size, sl=None, tp=None):
    """
    Envía una orden a Binance Futures.
    Soporta Órdenes Límite Post-Only (GTX Maker Fee = 0.020%) si config.USE_LIMIT_ORDERS es True,
    o Mercado (Taker Fee = 0.050%) si es False.
    """
    side = 'buy' if action == 'LONG' else 'sell'
    use_limit = getattr(config, 'USE_LIMIT_ORDERS', True)

    if is_paper_trading(client):
        order_type_str = "LIMIT (Post-Only GTX Maker 0.020%)" if use_limit else "MARKET (Taker 0.050%)"
        logger.info(
            f"[PAPER TRADING] Orden simulada ({order_type_str}): {side.upper()} {size} {symbol} | "
            f"SL={sl} | TP={tp}"
        )
        nm.add_notification(
            "INFO",
            f"Orden Paper Simulado ({action} {symbol})",
            f"Tipo: {order_type_str} | Tamaño: {size} | SL: {sl or 'Sin SL'} | TP: {tp or 'Sin TP'}",
            symbol
        )
        return {"dry_run": True, "symbol": symbol, "side": side, "size": size}

    try:
        order = None
        if use_limit:
            # Obtener ticker actual para colocar la orden en la punta del libro
            try:
                ticker = client.client.fetch_ticker(symbol)
                limit_price = ticker['bid'] if action == 'LONG' else ticker['ask']
                if not limit_price or limit_price <= 0:
                    limit_price = ticker['last']
                
                prec = 4 if symbol in ['XRPUSDT', 'HBARUSDT', 'ADAUSDT'] else 2
                limit_price = round(limit_price, prec)

                logger.info(f"🎯 Enviando orden LÍMITE Post-Only (GTX Maker 0.020%) {side.upper()} {size} {symbol} a {limit_price}")
                
                # timeInForce: GTX garantiza orden Post-Only Maker en Binance Futuros
                order = _safe_create_order(
                    client=client,
                    symbol=symbol,
                    order_type='LIMIT',
                    side=side,
                    amount=size,
                    params={'price': limit_price, 'timeInForce': 'GTX'},
                    action=action
                )
            except Exception as limit_err:
                logger.warning(f"⚠️ Orden Límite GTX rebotó ({limit_err}) — Aplicando fallback seguro a MARKET...")
                order = None

        # Fallback a MARKET si no se usó límite o si la orden GTX rebotó por movimiento del libro
        if order is None:
            order = _safe_create_order(
                client=client,
                symbol=symbol,
                order_type='MARKET',
                side=side,
                amount=size,
                action=action
            )

        order_id = order.get('orderId', 'OK')
        fee_type = "Maker (0.020%)" if use_limit and order.get('type') == 'LIMIT' else "Taker (0.050%)"
        logger.info(f"✅ REAL orden ejecutada en Binance ({fee_type}): {side.upper()} {size} {symbol} | ID: {order_id}")
        nm.add_notification(
            "SUCCESS",
            f"Orden REAL Ejecutada ({action} {symbol})",
            f"ID: {order_id} | Tipo: {fee_type} | Tamaño: {size}",
            symbol
        )

        # Stop Loss en Binance Futures Real
        if sl is not None and sl > 0:
            try:
                sl_side = 'sell' if action == 'LONG' else 'buy'
                sl_prec = 4 if symbol in ['XRPUSDT', 'HBARUSDT', 'ADAUSDT'] else 2
                _safe_create_order(
                    client=client,
                    symbol=symbol,
                    order_type='STOP_MARKET',
                    side=sl_side,
                    amount=size,
                    params={
                        'stopPrice': round(sl, sl_prec),
                        'closePosition': True
                    },
                    action=action
                )
                logger.info(f"🛡️ SL real colocado en Binance: {sl}")
            except Exception as sl_err:
                logger.error(f"⚠️ Error al colocar SL en Binance para {symbol}: {sl_err}")

        # Take Profit LÍMITE (Maker 0.020%) en Binance Futures Real
        if tp is not None and tp > 0:
            try:
                tp_side = 'sell' if action == 'LONG' else 'buy'
                tp_prec = 4 if symbol in ['XRPUSDT', 'HBARUSDT', 'ADAUSDT'] else 2
                tp_price = round(tp, tp_prec)

                if use_limit:
                    # TAKE_PROFIT tipo Límite descansa en el libro de Binance y cobra Maker Fee (0.020%)
                    _safe_create_order(
                        client=client,
                        symbol=symbol,
                        order_type='TAKE_PROFIT',
                        side=tp_side,
                        amount=size,
                        params={
                            'stopPrice': tp_price,
                            'price': tp_price,
                            'closePosition': True
                        },
                        action=action
                    )
                    logger.info(f"🎯 TP Límite Maker (0.020%) colocado en Binance: {tp_price}")
                else:
                    _safe_create_order(
                        client=client,
                        symbol=symbol,
                        order_type='TAKE_PROFIT_MARKET',
                        side=tp_side,
                        amount=size,
                        params={
                            'stopPrice': tp_price,
                            'closePosition': True
                        },
                        action=action
                    )
                    logger.info(f"🎯 TP Mercado colocado en Binance: {tp_price}")
            except Exception as tp_err:
                logger.error(f"⚠️ Error al colocar TP en Binance para {symbol}: {tp_err}")

        return order

    except Exception as e:
        logger.error(f"❌ Error ejecutando orden REAL {side.upper()} en {symbol}: {e}")
        nm.add_notification(
            "ERROR",
            f"Error al meter orden en Binance ({symbol})",
            f"Detalle del fallo API: {e}",
            symbol
        )
        return None


def close_position(client, symbol, action, size):
    """
    Cierra una posición existente en Binance Futures.
    Intenta cierre Límite GTX (Maker 0.020%) con fallback seguro a Mercado.
    """
    close_side = 'sell' if action == 'LONG' else 'buy'
    use_limit = getattr(config, 'USE_LIMIT_ORDERS', True)

    if is_paper_trading(client):
        logger.info(f"[PAPER TRADING] Cierre simulado: {close_side.upper()} {size} {symbol}")
        nm.add_notification("INFO", f"Cierre Paper Simulado ({symbol})", f"Tamaño: {size}", symbol)
        return {"dry_run": True, "closed": True}

    try:
        order = None
        if use_limit:
            try:
                ticker = client.client.fetch_ticker(symbol)
                limit_price = ticker['bid'] if close_side == 'sell' else ticker['ask']
                if not limit_price or limit_price <= 0:
                    limit_price = ticker['last']

                prec = 4 if symbol in ['XRPUSDT', 'HBARUSDT', 'ADAUSDT'] else 2
                limit_price = round(limit_price, prec)

                logger.info(f"🎯 Intentando cierre LÍMITE GTX (Maker 0.020%) {symbol} a {limit_price}")
                order = _safe_create_order(
                    client=client,
                    symbol=symbol,
                    order_type='LIMIT',
                    side=close_side,
                    amount=size,
                    params={
                        'price': limit_price,
                        'reduceOnly': True,
                        'timeInForce': 'GTX'
                    },
                    action=action
                )
            except Exception as limit_err:
                logger.warning(f"⚠️ Cierre Límite GTX rebotó ({limit_err}) — Aplicando fallback seguro a Mercado...")
                order = None

        if order is None:
            order = _safe_create_order(
                client=client,
                symbol=symbol,
                order_type='MARKET',
                side=close_side,
                amount=size,
                params={'reduceOnly': True},
                action=action
            )

        logger.info(f"✅ Posición REAL cerrada en Binance: {symbol} | ID: {order.get('orderId')}")
        nm.add_notification("SUCCESS", f"Posición REAL Cerrada ({symbol})", "Cierre ejecutado", symbol)
        return order

    except Exception as e:
        logger.error(f"❌ Error cerrando posición REAL en {symbol}: {e}")
        nm.add_notification("ERROR", f"Error al cerrar posición REAL ({symbol})", str(e), symbol)
        return None


def cancel_all_orders(client, symbol):
    """Cancela todas las órdenes abiertas de un símbolo en Binance."""
    if is_paper_trading(client):
        logger.info(f"[PAPER TRADING] Cancelación simulada de órdenes en {symbol}")
        return True

    try:
        client.client.cancel_all_orders(symbol=symbol)
        logger.info(f"🧹 Órdenes reales canceladas en Binance para {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Error cancelando órdenes reales en {symbol}: {e}")
        nm.add_notification("ERROR", f"Error cancelando órdenes en Binance ({symbol})", str(e), symbol)
        return False