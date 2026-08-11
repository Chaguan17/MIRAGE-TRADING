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

# Buffer de slippage para órdenes STOP limit — 0.1% para maximizar fill en mercados rápidos
SL_LIMIT_BUFFER = 0.001


def is_paper_trading(client):
    if client is not None and hasattr(client, 'paper_trading'):
        return client.paper_trading
    return True


def _safe_create_order(client, symbol, order_type, side, amount, price=None, params=None, action='LONG'):
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
            price=price,
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
                price=price,
                params=hedge_params
            )
        raise e


def execute_trade(client, symbol, action, size, sl=None, tp=None, signal_price=None):
    """
    Envía una orden a Binance Futures.
    Soporta Órdenes Límite Post-Only (GTX Maker Fee = 0.020%) si config.USE_LIMIT_ORDERS es True,
    o Mercado (Taker Fee = 0.050%) si es False.
    Recalcula dinámicamente SL/TP si el precio real de llenado (actual_fill) difiere de la señal.
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
        return {
            'order': {"dry_run": True, "symbol": symbol, "side": side, "size": size},
            'id': 'PAPER',
            'fill_price': None,
            'sl_placed': True,
            'tp_placed': True,
            'sl_price': sl,
            'tp_price': tp,
        }

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
                    price=limit_price,
                    params={'timeInForce': 'GTX'},
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

        # Precisiones dinámicas por símbolo
        try:
            sl_prec = 4 if symbol in ['XRPUSDT', 'HBARUSDT', 'ADAUSDT'] else 2
        except Exception:
            sl_prec = 2

        # Recalcular SL y TP si el precio real de llenado difiere del precio de señal
        actual_fill = float(order.get('avgPrice', 0) or order.get('price', 0) or 0)
        if actual_fill > 0 and signal_price and signal_price > 0:
            diff = actual_fill - signal_price
            if abs(diff) > 0.0001:
                if sl is not None and sl > 0:
                    sl = sl + diff
                    logger.info(f"🔄 SL recalculado por precio de llenado real (${actual_fill:.4f}): {sl:.4f}")
                if tp is not None and tp > 0:
                    tp = tp + diff
                    logger.info(f"🔄 TP recalculado por precio de llenado real (${actual_fill:.4f}): {tp:.4f}")

        # Breve pausa para asegurar asentamiento del contrato en el motor de posiciones de Binance
        import time
        time.sleep(0.2)

        sl_success = False
        tp_success = False
        sl_final = None
        tp_final = None

        # Stop Loss LIMIT (Maker 0.020%) — Opción B: 3 intentos, si falla cierra posición
        if sl is not None and sl > 0:
            sl_side = 'sell' if action == 'LONG' else 'buy'
            sl_trigger = round(sl, sl_prec)
            if action == 'LONG':
                sl_limit = round(sl_trigger * (1 - SL_LIMIT_BUFFER), sl_prec)
            else:
                sl_limit = round(sl_trigger * (1 + SL_LIMIT_BUFFER), sl_prec)

            for attempt in range(3):
                try:
                    _safe_create_order(
                        client=client, symbol=symbol,
                        order_type='STOP', side=sl_side,
                        amount=size, price=sl_limit,
                        params={'stopPrice': sl_trigger},
                        action=action
                    )
                    sl_success = True
                    sl_final = sl_trigger
                    logger.info(f"🛡️ SL Limit colocado: trigger={sl_trigger}, limit={sl_limit}")
                    break
                except Exception as sl_err:
                    if attempt < 2:
                        logger.warning(f"⚠️ SL intento {attempt+1}/3 falló: {sl_err} — reintentando en 500ms...")
                        time.sleep(0.5)
                    else:
                        logger.error(f"🚨 SL FALLÓ tras 3 intentos para {symbol}: {sl_err}")

            if not sl_success:
                logger.error(f"🚨 SEGURIDAD: Cerrando posición {symbol} porque SL no se pudo colocar")
                nm.add_notification(
                    "ERROR",
                    f"🚨 SL FALLÓ — Posición cerrada por seguridad ({symbol})",
                    f"Se intentó colocar SL en {sl_trigger} pero falló 3 veces. Posición cerrada automáticamente.",
                    symbol
                )
                try:
                    close_position(client, symbol, action, size)
                except Exception as close_err:
                    logger.error(f"❌ Error cerrando posición de seguridad: {close_err}")
                return None

        # Take Profit LIMIT (Maker 0.020%)
        if tp is not None and tp > 0:
            try:
                tp_side = 'sell' if action == 'LONG' else 'buy'
                tp_trigger = round(tp, sl_prec)
                tp_limit = tp_trigger
                _safe_create_order(
                    client=client, symbol=symbol,
                    order_type='TAKE_PROFIT', side=tp_side,
                    amount=size, price=tp_limit,
                    params={'stopPrice': tp_trigger},
                    action=action
                )
                tp_success = True
                tp_final = tp_trigger
                logger.info(f"🎯 TP Limit colocado: trigger={tp_trigger}, limit={tp_limit}")
            except Exception as tp_err:
                logger.error(f"⚠️ Error al colocar TP Limit para {symbol}: {tp_err}")

        return {
            'order': order,
            'id': str(order.get('id') or order.get('orderId') or 'OK'),
            'fill_price': actual_fill if actual_fill > 0 else None,
            'sl_placed': sl_success,
            'tp_placed': tp_success,
            'sl_price': sl_final,
            'tp_price': tp_final,
        }

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


def update_position_stop_loss(client, symbol, new_sl_price, action, size, sl_prec=2):
    """
    Cancela el SL existente en Binance y coloca uno nuevo STOP Limit (Maker 0.020%).
    Retorna True si exitoso, False si falló (SL anterior puede seguir vigente).
    """
    import time
    try:
        open_orders = client.client.fetch_open_orders(symbol)
        sl_side = 'sell' if action == 'LONG' else 'buy'

        # Buscar y cancelar órdenes SL existentes (STOP o STOP_MARKET)
        for o in open_orders:
            o_info = o.get('info', {})
            orig_type = str(o_info.get('origType', '') or o_info.get('type', '') or o.get('type', '') or '').upper()
            if 'STOP' in orig_type and 'TAKE' not in orig_type:
                if str(o.get('side', '')).lower() == sl_side:
                    client.client.cancel_order(o['id'], symbol)
                    logger.info(f"🗑️ SL anterior cancelado: {o['id']}")

        # Colocar nuevo SL LIMIT con buffer de slippage
        sl_trigger = round(new_sl_price, sl_prec)
        if action == 'LONG':
            sl_limit = round(sl_trigger * (1 - SL_LIMIT_BUFFER), sl_prec)
        else:
            sl_limit = round(sl_trigger * (1 + SL_LIMIT_BUFFER), sl_prec)

        _safe_create_order(
            client=client, symbol=symbol,
            order_type='STOP', side=sl_side,
            amount=size, price=sl_limit,
            params={'stopPrice': sl_trigger},
            action=action
        )
        logger.info(f"🛡️ SL Limit actualizado en Binance: trigger={sl_trigger}, limit={sl_limit}")
        return True

    except Exception as e:
        logger.error(f"❌ Error actualizando SL en Binance para {symbol}: {e}")
        return False


def update_position_take_profit(client, symbol, new_tp_price, action, size, sl_prec=2):
    """
    Cancela el TP existente en Binance y coloca uno nuevo TAKE_PROFIT Limit (Maker 0.020%).
    Retorna True si exitoso, False si falló.
    """
    try:
        open_orders = client.client.fetch_open_orders(symbol)
        tp_side = 'sell' if action == 'LONG' else 'buy'

        # Buscar y cancelar órdenes TP existentes (TAKE_PROFIT o TAKE_PROFIT_MARKET)
        for o in open_orders:
            o_info = o.get('info', {})
            orig_type = str(o_info.get('origType', '') or o_info.get('type', '') or o.get('type', '') or '').upper()
            if 'TAKE_PROFIT' in orig_type:
                if str(o.get('side', '')).lower() == tp_side:
                    client.client.cancel_order(o['id'], symbol)
                    logger.info(f"🗑️ TP anterior cancelado: {o['id']}")

        # Colocar nuevo TP LIMIT
        tp_trigger = round(new_tp_price, sl_prec)
        tp_limit = tp_trigger

        _safe_create_order(
            client=client, symbol=symbol,
            order_type='TAKE_PROFIT', side=tp_side,
            amount=size, price=tp_limit,
            params={'stopPrice': tp_trigger},
            action=action
        )
        logger.info(f"🎯 TP Limit actualizado en Binance: trigger={tp_trigger}, limit={tp_limit}")
        return True

    except Exception as e:
        logger.error(f"❌ Error actualizando TP en Binance para {symbol}: {e}")
        return False