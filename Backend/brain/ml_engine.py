import os
import joblib
import logging
import hashlib
import shutil
import tempfile
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

class MLEngine:
    def __init__(self, symbol, outcome_path, sl_path, config):
        self.symbol = symbol
        self.config = config
        self.outcome_path = outcome_path
        self.sl_path = sl_path
        
        self.model_outcome = self._load_with_integrity(outcome_path)
        self.model_sl = self._load_with_integrity(sl_path)

    def _generate_checksum(self, file_path):
        """Genera un hash SHA-256 de un archivo."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _verify_integrity(self, file_path):
        """Verifica que el archivo coincida con su checksum almacenado."""
        checksum_path = file_path + ".sha256"
        if not os.path.exists(checksum_path):
            return False
        
        try:
            with open(checksum_path, "r") as f:
                stored_checksum = f.read().strip()
            actual_checksum = self._generate_checksum(file_path)
            return actual_checksum == stored_checksum
        except Exception:
            return False

    def _load_with_integrity(self, path):
        """Carga el modelo verificando integridad, o intenta recuperar desde backup."""
        if os.path.exists(path):
            if self._verify_integrity(path):
                try:
                    return joblib.load(path)
                except Exception as e:
                    logger.error(f"Error cargando modelo {path}: {e}")
            else:
                logger.error(f"🚨 Corrupción detectada en {path}. Intentando restaurar backup...")
                backup_path = os.path.join(self.config.BACKUP_DIR, os.path.basename(path) + ".bak")
                if os.path.exists(backup_path) and self._verify_integrity(backup_path):
                    logger.info(f"Restaurando backup para {os.path.basename(path)}")
                    shutil.copy2(backup_path, path)
                    shutil.copy2(backup_path + ".sha256", path + ".sha256")
                    return joblib.load(path)
                else:
                    logger.critical(f"Backup no disponible o corrupto para {path}")

        # Si nada funciona, crear uno nuevo
        logger.info(f"Creando nuevo modelo para {path}")
        return RandomForestClassifier(
            n_estimators=self.config.AI_BASE_ESTIMATORS,
            max_depth=6,
            min_samples_leaf=5,
            class_weight='balanced_subsample',
            random_state=self.config.RANDOM_STATE,
            warm_start=False,
            n_jobs=-1
        )

    def predict_outcome(self, Xs, action_code):
        try:
            if not hasattr(self.model_outcome, 'classes_'):
                return 0.5
            proba = self.model_outcome.predict_proba(Xs)[0]
            return proba[1] if action_code == 1 else (1 - proba[1])
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            return 0.5

    def predict_use_sl(self, Xs, trades_seen):
        try:
            if not hasattr(self.model_sl, 'classes_') or trades_seen < self.config.MIN_TRADES_FOR_AI:
                return True
            return self.model_sl.predict_proba(Xs)[0][1] >= 0.5
        except Exception:
            return True

    def calculate_ai_weight(self, trades_seen):
        if trades_seen < self.config.MIN_TRADES_FOR_AI:
            return 0.0
        steps = getattr(self.config, 'AI_LEARNING_CURVE_STEPS', 45)
        ratio = min(1.0, (trades_seen - self.config.MIN_TRADES_FOR_AI) / steps)
        return ratio * self.config.AI_MAX_WEIGHT

    def save_models(self):
        """Guarda ambos modelos de forma atómica con checksum y backup."""
        self._safe_save(self.model_outcome, self.outcome_path)
        self._safe_save(self.model_sl, self.sl_path)

    def _safe_save(self, model, path):
        """Implementa escritura atómica y generación de checksum."""
        # 1. Crear backup del modelo actual funcional
        if os.path.exists(path) and self._verify_integrity(path):
            backup_path = os.path.join(self.config.BACKUP_DIR, os.path.basename(path) + ".bak")
            shutil.copy2(path, backup_path)
            if os.path.exists(path + ".sha256"):
                shutil.copy2(path + ".sha256", backup_path + ".sha256")

        # 2. Escritura atómica usando archivo temporal
        temp_path = path + ".tmp"
        try:
            joblib.dump(model, temp_path)
            # 3. Generar nuevo Checksum
            checksum = self._generate_checksum(temp_path)
            with open(path + ".sha256", "w") as f:
                f.write(checksum)
            # 4. Reemplazo atómico (Atomic Move)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Fallo en guardado atómico de {path}: {e}")