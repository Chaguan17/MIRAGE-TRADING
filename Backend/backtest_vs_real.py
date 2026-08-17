"""
backtest_vs_real.py — Mirage Trading
Motor de Reconciliación y Análisis de Fidelidad Predictiva (Backtest vs REAL).

Permite comparar cuantitativamente el comportamiento simulado (Backtest)
contra la ejecución en dinero real en Binance Futures sobre el mismo marco temporal,
evaluando 11 métricas críticas y calculando el Índice de Fidelidad Predictiva.
"""
import os
import sqlite3
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import config as cfg
from backtester import SimpleBacktester
from data_engine import DataEngine
from binance_api import MirageBinance

logger = logging.getLogger(__name__)


class BacktestVsRealComparator:
    """
    Compara minuciosamente las operaciones en dinero real registradas en SQLite
    contra el backtest ejecutado sobre el mismo marco temporal exacto.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or cfg.DB_PATH

    def get_real_trades(self, symbol=None):
        """Extrae las operaciones reales guardadas en la base de datos."""
        if not os.path.exists(self.db_path):
            return pd.DataFrame()

        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            query = "SELECT * FROM trades WHERE (is_paper = 'REAL' OR is_paper = '0' OR is_paper = 'False')"
            params = []

            if symbol:
                query += " AND pair = ?"
                params.append(symbol.upper())

            query += " ORDER BY rowid ASC"
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error leyendo trades reales de SQLite: {e}")
            return pd.DataFrame()

    def compare(self, symbol="ETHUSDT", limit_candles=500):
        """
        Ejecuta la comparación entre el desempeño Real y el Backtest simulado.
        """
        df_real = self.get_real_trades(symbol)

        # 1. Calcular Métricas Reales
        metrics_real = self._compute_metrics(df_real, is_real=True)

        # 2. Obtener datos históricos para el Backtest
        engine = DataEngine()
        try:
            api = MirageBinance(
                api_key=getattr(cfg, 'BINANCE_API_KEY', ''),
                api_secret=getattr(cfg, 'BINANCE_SECRET_KEY', ''),
                paper_trading=getattr(cfg, 'PAPER_TRADING', True)
            )
            raw_df = api.get_historical_data(symbol, cfg.TIMEFRAME, limit=limit_candles)
        except Exception as e:
            logger.warning(f"No se pudieron descargar klines en vivo para {symbol}: {e}")
            raw_df = None

        if raw_df is None or raw_df.empty:
            raw_df = engine.load_local_data(symbol)

        if raw_df is None or raw_df.empty or len(raw_df) < 110:
            return {
                'status': 'error',
                'message': f'Datos históricos insuficientes para ejecutar el backtest comparativo de {symbol}.',
                'symbol': symbol,
                'metrics_real': metrics_real,
                'metrics_backtest': {},
                'comparison_matrix': [],
                'predictive_fidelity_score': 0.0
            }

        # 3. Ejecutar Backtest sobre los mismos datos
        tester = SimpleBacktester(symbol, raw_df, test_dir="storage/backtest_vs_real")
        tester.run()

        df_backtest = pd.DataFrame(tester.history)
        metrics_backtest = self._compute_metrics(df_backtest, is_real=False)

        # 4. Construir Matriz Comparativa (11 métricas)
        matrix = self._build_comparison_matrix(metrics_backtest, metrics_real)

        # 5. Calcular Índice de Fidelidad Predictiva (0 - 100%)
        fidelity_score = self._calculate_fidelity_score(metrics_backtest, metrics_real)

        # 6. Identificar Causas Principales de Divergencia
        divergence_reasons = self._identify_divergence_reasons(metrics_backtest, metrics_real)

        return {
            'status': 'success',
            'symbol': symbol,
            'predictive_fidelity_score': round(fidelity_score, 1),
            'divergence_reasons': divergence_reasons,
            'metrics_backtest': metrics_backtest,
            'metrics_real': metrics_real,
            'comparison_matrix': matrix,
            'markdown_report': self.generate_markdown_report(symbol, matrix, fidelity_score, divergence_reasons)
        }

    def _compute_metrics(self, df_trades, is_real=False):
        """Calcula las 11 métricas clave a partir de un DataFrame de operaciones."""
        if df_trades is None or df_trades.empty:
            return {
                'trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'expectancy': 0.0,
                'max_drawdown': 0.0,
                'total_fees': 0.0,
                'total_slippage': 0.0,
                'avg_mfe': 0.0,
                'avg_mae': 0.0,
                'total_pnl': 0.0
            }

        col_pnl = 'pnl_usdt' if 'pnl_usdt' in df_trades.columns else ('PNL' if 'PNL' in df_trades.columns else 'pnl')
        pnls = pd.to_numeric(df_trades[col_pnl], errors='coerce').fillna(0.0)

        total_trades = len(pnls)
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]

        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
        avg_win = float(wins.mean()) if not wins.empty else 0.0
        avg_loss = float(losses.mean()) if not losses.empty else 0.0

        profit_factor = (wins.sum() / abs(losses.sum())) if not losses.empty and losses.sum() != 0 else (float('inf') if not wins.empty else 0.0)
        expectancy = ( (win_rate / 100.0) * avg_win ) + ( (1 - (win_rate / 100.0)) * avg_loss )

        # Drawdown
        equity = cfg.PAPER_BALANCE + pnls.cumsum()
        peak = equity.cummax()
        dd = (peak - equity) / peak
        max_dd = float(dd.max() * 100.0) if not dd.empty else 0.0

        # Fees & Slippage
        if 'FEES' in df_trades.columns:
            total_fees = float(pd.to_numeric(df_trades['FEES'], errors='coerce').sum())
        else:
            total_fees = float(total_trades * 0.40) # Estimación básica si no está registrado

        if 'SLIPPAGE' in df_trades.columns:
            total_slippage = float(pd.to_numeric(df_trades['SLIPPAGE'], errors='coerce').sum())
        else:
            total_slippage = float(total_trades * 0.20)

        # MFE / MAE
        avg_mfe = float(pd.to_numeric(df_trades['MFE'], errors='coerce').mean()) if 'MFE' in df_trades.columns else 0.0
        avg_mae = float(pd.to_numeric(df_trades['MAE'], errors='coerce').mean()) if 'MAE' in df_trades.columns else 0.0

        return {
            'trades': total_trades,
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999.0,
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'expectancy': round(expectancy, 2),
            'max_drawdown': round(max_dd, 2),
            'total_fees': round(total_fees, 2),
            'total_slippage': round(total_slippage, 2),
            'avg_mfe': round(avg_mfe, 2),
            'avg_mae': round(avg_mae, 2),
            'total_pnl': round(float(pnls.sum()), 2)
        }

    def _build_comparison_matrix(self, backtest, real):
        """Construye la matriz comparativa lado a lado para las 11 métricas."""
        metric_labels = [
            ('Trades Totales', 'trades', ''),
            ('Win Rate', 'win_rate', '%'),
            ('Profit Factor', 'profit_factor', ''),
            ('Avg Win', 'avg_win', 'USDT'),
            ('Avg Loss', 'avg_loss', 'USDT'),
            ('Expectancy', 'expectancy', 'USDT/trade'),
            ('Max Drawdown', 'max_drawdown', '%'),
            ('Comisiones Totales', 'total_fees', 'USDT'),
            ('Slippage Est.', 'total_slippage', 'USDT'),
            ('MFE Promedio', 'avg_mfe', '%'),
            ('MAE Promedio', 'avg_mae', '%'),
        ]

        matrix = []
        for label, key, unit in metric_labels:
            val_bt = backtest.get(key, 0.0)
            val_rl = real.get(key, 0.0)

            if isinstance(val_bt, (int, float)) and isinstance(val_rl, (int, float)):
                diff = val_rl - val_bt
                diff_str = f"{diff:+.2f} {unit}".strip()
                # Evaluar alineación
                is_aligned = abs(diff) <= (abs(val_bt) * 0.25 + 0.1) if val_bt != 0 else (abs(val_rl) < 1.0)
                status = "🎯 ALINEADO" if is_aligned else "⚠️ DIVERGENTE"
            else:
                diff_str = "N/A"
                status = "ℹ️ INFO"

            matrix.append({
                'metric': label,
                'backtest': f"{val_bt} {unit}".strip(),
                'real': f"{val_rl} {unit}".strip(),
                'variance': diff_str,
                'status': status
            })

        return matrix

    def _calculate_fidelity_score(self, backtest, real):
        """Calcula una puntuación de fidelidad predictiva entre 0% y 100%."""
        if backtest.get('trades', 0) == 0 or real.get('trades', 0) == 0:
            return 50.0  # Muestra neutral si falta historial

        # Evaluar desviación en Win Rate, PnL y Expectancy
        wr_diff = abs(backtest.get('win_rate', 0) - real.get('win_rate', 0))
        exp_diff = abs(backtest.get('expectancy', 0) - real.get('expectancy', 0))

        score = 100.0 - (wr_diff * 1.5) - (exp_diff * 5.0)
        return max(0.0, min(100.0, score))

    def _identify_divergence_reasons(self, backtest, real):
        """Identifica los factores principales de discrepancia si existen."""
        reasons = []
        if real.get('trades', 0) == 0:
            reasons.append("Sin historial suficiente de ejecuciones en REAL para comparar.")
            return reasons

        if real.get('total_slippage', 0) > backtest.get('total_slippage', 0) * 1.5:
            reasons.append("Slippage / Fricción de mercado real fue significativamente mayor al esperado.")

        if real.get('total_fees', 0) > backtest.get('total_fees', 0) * 1.3:
            reasons.append("Mayor proporción de ejecuciones Taker a mercado que las órdenes Maker Límite.")

        if real.get('win_rate', 0) < backtest.get('win_rate', 0) - 15.0:
            reasons.append("Desviación de dirección en ejecuciones vivas debido a latencia o desincronización de velas.")

        if not reasons:
            reasons.append("El comportamiento en REAL se alinea razonablemente dentro de las tolerancias teóricas del Backtest.")

        return reasons

    def generate_markdown_report(self, symbol, matrix, fidelity_score, divergence_reasons):
        """Genera un reporte completo en GitHub Flavored Markdown."""
        lines = [
            f"# ⚖️ Informe de Reconciliación: Backtest vs REAL ({symbol})",
            f"**Índice de Fidelidad Predictiva:** `{fidelity_score:.1f}%`",
            "",
            "## 📊 Matriz Comparativa (11 Métricas)",
            "",
            "| Métrica | Backtest (Simulado) | REAL (Binance) | Varianza | Estado |",
            "|---------|---------------------|----------------|----------|--------|"
        ]

        for row in matrix:
            lines.append(f"| **{row['metric']}** | {row['backtest']} | {row['real']} | {row['variance']} | {row['status']} |")

        lines.extend([
            "",
            "## 🔍 Diagnóstico de Divergencia & Causa Raíz",
            ""
        ])

        for r in divergence_reasons:
            lines.append(f"- ⚠️ {r}")

        return "\n".join(lines)
