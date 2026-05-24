import os
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

class FeatureEngine:
    def __init__(self, scaler_path, feat_cols):
        self.path = scaler_path
        self.feat_cols = feat_cols
        self.scaler = self._load_scaler()

    def _load_scaler(self):
        if os.path.exists(self.path):
            return joblib.load(self.path)
        return StandardScaler()

    def build_X(self, features_dict):
        row = {col: features_dict.get(col, 0.0) for col in self.feat_cols}
        return pd.DataFrame([row])

    def scale(self, X):
        if hasattr(self.scaler, 'mean_'):
            return self.scaler.transform(X)
        return X.values

    def fit_scaler(self, X):
        Xs = self.scaler.fit_transform(X)
        joblib.dump(self.scaler, self.path)
        return Xs