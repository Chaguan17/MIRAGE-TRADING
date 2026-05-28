import os
import joblib
import logging
import hashlib
import shutil
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

class MLEngine:
    def __init__(self, symbol, outcome_path, sl_path, config):
        self.symbol = symbol
        self.config = config
        self.outcome_path = outcome_path
        self.sl_path = sl_path

        self.model_outcome = self._load_with_integrity(outcome_path)
        self.model_sl      = self._load_with_integrity(sl_path)

    # ── Integridad ────────────────────────────────────────────────────────────

    def _generate_checksum(self, file_path):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def _verify_integrity(self, file_path):
        checksum_path = file_path + ".sha256"
        if not os.path.exists(checksum_path):
            return False
        try:
            with open(checksum_path, "r") as f:
                stored = f.read().strip()
            return self._generate_checksum(file_path) == stored
        except Exception:
            return False

    def _load_with_integrity(self, path):
        if os.path.exists(path):
            if self._verify_integrity(path):
                try:
                    return joblib.load(path)
                except Exception as e:
                    logger.error(f"Error cargando {path}: {e}")
            else:
                logger.error(f"🚨 Corrupción en {path}. Intentando backup...")
                backup = os.path.join(self.config.BACKUP_DIR, os.path.basename(path) + ".bak")
                if os.path.exists(backup) and self._verify_integrity(backup):
                    shutil.copy2(backup, path)
                    shutil.copy2(backup + ".sha256", path + ".sha256")
                    return joblib.load(path)
                logger.critical(f"Backup no disponible para {path}")

        logger.info(f"Creando nuevo modelo para {path}")
        return self._new_model()

    def _new_model(self):
        return RandomForestClassifier(
            n_estimators=self.config.AI_BASE_ESTIMATORS,
            max_depth=6,
            min_samples_leaf=5,
            class_weight='balanced_subsample',
            random_state=self.config.RANDOM_STATE,
            warm_start=False,
            n_jobs= 1
        )

    # ── Predicciones ─────────────────────────────────────────────────────────

    def _model_is_ready(self, model) -> bool:
        """Verifica que el modelo está entrenado Y conoce ambas clases."""
        if not hasattr(model, 'classes_'):
            return False
        if len(model.classes_) < 2:
            return False
        return True

    def predict_outcome(self, Xs, action_code):
        """
        Devuelve la probabilidad de éxito del trade.
        Retorna 0.5 (neutral) si el modelo no está listo o solo conoce una clase.
        """
        try:
            if not self._model_is_ready(self.model_outcome):
                return 0.5
            proba = self.model_outcome.predict_proba(Xs)[0]
            return float(proba[1]) if action_code == 1 else float(1.0 - proba[1])
        except Exception as e:
            logger.error(f"Error en predict_outcome ({self.symbol}): {e}")
            return 0.5

    def predict_use_sl(self, Xs, trades_seen):
        """
        Decide si usar stop-loss.
        Retorna True (usar SL) si el modelo no tiene info suficiente — decisión conservadora.
        """
        try:
            if not self._model_is_ready(self.model_sl):
                return True
            if trades_seen < self.config.MIN_TRADES_FOR_AI:
                return True
            return bool(self.model_sl.predict_proba(Xs)[0][1] >= 0.5)
        except Exception as e:
            logger.error(f"Error en predict_use_sl ({self.symbol}): {e}")
            return True  # siempre conservador ante error

    # ── Peso de la IA ─────────────────────────────────────────────────────────

    def calculate_ai_weight(self, trades_seen):
        if trades_seen < self.config.MIN_TRADES_FOR_AI:
            return 0.0
        steps = getattr(self.config, 'AI_LEARNING_CURVE_STEPS', 45)
        ratio = min(1.0, (trades_seen - self.config.MIN_TRADES_FOR_AI) / steps)
        return ratio * self.config.AI_MAX_WEIGHT

    # ── Persistencia ──────────────────────────────────────────────────────────

    def save_models(self):
        self._safe_save(self.model_outcome, self.outcome_path)
        self._safe_save(self.model_sl,      self.sl_path)

    def _safe_save(self, model, path):
        # Backup del modelo funcional actual
        if os.path.exists(path) and self._verify_integrity(path):
            backup = os.path.join(self.config.BACKUP_DIR, os.path.basename(path) + ".bak")
            shutil.copy2(path, backup)
            if os.path.exists(path + ".sha256"):
                shutil.copy2(path + ".sha256", backup + ".sha256")

        temp = path + ".tmp"
        try:
            joblib.dump(model, temp)
            checksum = self._generate_checksum(temp)
            with open(path + ".sha256", "w") as f:
                f.write(checksum)
            os.replace(temp, path)
        except Exception as e:
            if os.path.exists(temp):
                os.remove(temp)
            logger.error(f"Fallo guardando {path}: {e}")
