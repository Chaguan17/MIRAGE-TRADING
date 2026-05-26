import os
import joblib
import pandas as pd
import sqlite3
import logging
import config as cfg

from .ml_engine import MLEngine
from .feature_engine import FeatureEngine
from .signal_engine import SignalEngine
from .trainer import Trainer
from .veto_engine import VetoEngine
from .consensus_engine import ConsensusEngine

logger = logging.getLogger(__name__)

class MirageBrain:
    def __init__(self, symbol="BTCUSDT", storage_dir=None):
        self.symbol = symbol
        self.cfg = cfg
        self.storage_dir = storage_dir or self.cfg.STORAGE_DIR
        
        # Rutas de persistencia
        outcome_p = os.path.join(self.storage_dir, f'model_outcome_{self.symbol}.pkl')
        sl_p = os.path.join(self.storage_dir, f'model_sl_{self.symbol}.pkl')
        scaler_p = os.path.join(self.storage_dir, f'scaler_{self.symbol}.pkl')

        from data_engine import DataEngine
        self._feat_cols = DataEngine().get_feature_columns()

        # Inicialización de motores especializados
        self.features = FeatureEngine(scaler_p, self._feat_cols)
        self.ml = MLEngine(self.symbol, outcome_p, sl_p, self.cfg)
        self.signals = SignalEngine(self.cfg.ACTIVE_STRATEGIES)
        self.consensus = ConsensusEngine(self.cfg.LAYER_WEIGHTS)
        self.vetos = VetoEngine(self.symbol, self.cfg)
        self.trainer = Trainer(self.ml, self.features, self.cfg, self._feat_cols)

        self.trades_seen = self._count_historical_trades()
        self._bootstrap_buffer = []
        self._max_buffer = cfg.MAX_BOOTSTRAP_BUFFER

    @property
    def model_outcome(self): return self.ml.model_outcome
    @property
    def model_sl(self): return self.ml.model_sl
    @property
    def scaler(self): return self.features.scaler

    def _count_historical_trades(self):
        try:
            if os.path.exists(self.cfg.DB_PATH):
                conn = sqlite3.connect(self.cfg.DB_PATH)
                query = "SELECT COUNT(*) FROM trades WHERE pair = ?"
                res = conn.execute(query, (self.symbol,)).fetchone()
                conn.close()
                return res[0] if res else 0
        except Exception as e:
            logger.error(f"Error counting historical trades for {self.symbol}: {e}")
        return 0

    def _get_session_weight(self):
        from datetime import datetime, timezone
        hour_utc = datetime.now(timezone.utc).hour
        if 0 <= hour_utc < 8:
            session = 'asia'
        elif 8 <= hour_utc < 16:
            session = 'europa'
        else:
            session = 'america'
        return self.cfg.SESSION_WEIGHTS.get(session, 1.0), session

    def get_consensus_prediction(self, features_dict, features_df=None, btc_features=None):
        X = self.features.build_X(features_dict)
        df = features_df if features_df is not None else pd.DataFrame([features_dict])
        
        # 1. Obtener Señales Técnicas
        basic, struct, ctx = self.signals.get_signals(df, btc_features)

        # 2. Consenso Técnico
        tech_action, tech_conf, method_name = self.consensus.calculate_consensus(basic, struct, ctx)

        if tech_action is None:
            return None, 0, 'None', True

        # 3. Vetos de Mercado
        btc_action, _ = ctx.get('btc_corr', (None, 0))
        btc_row = btc_features.iloc[-1].to_dict() if btc_features is not None else None
        market_veto = self.vetos.check_market_vetoes(tech_action, btc_action, btc_row)
        if market_veto: return None, 0, market_veto, True

        # 4. Integración IA
        Xs = self.features.scale(X)
        ai_weight = self.ml.calculate_ai_weight(self.trades_seen)
        tech_weight = 1.0 - ai_weight
        ai_conf = self.ml.predict_outcome(Xs, tech_action)
        
        if self.vetos.check_ai_veto(ai_weight, ai_conf):
            return None, 0, 'AI Veto', True
            
        confidence = (tech_conf * tech_weight) + (ai_conf * ai_weight)

        session_weight, _ = self._get_session_weight()
        confidence *= session_weight

        use_sl = self.ml.predict_use_sl(Xs, self.trades_seen)
        return tech_action, confidence, method_name, use_sl

    def online_update(self, features_dict, result_label, sl_was_used, sl_was_hit):
        self.trades_seen += 1
        self.ml.save_models()

    def nightly_retrain(self):
        self.trainer.perform_nightly_retrain(self.symbol, self.cfg.DB_PATH)