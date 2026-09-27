"""Fold-local, explicit feature engineering; invalid denominators become missing."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted


RATIOS = {
    "loss_ratio": ("LostPackets", "TxPackets"),
    "tx_efficiency": ("RxBytes", "TxBytes"),
    "throughput_per_hop": ("Throughput/Kbps", "AverageHopCount"),
}


class DerivedFeatures(TransformerMixin, BaseEstimator):
    """Preserve raw measurements; optionally clip PDR in a separate sensitivity run."""

    def __init__(self, features, derived=(), clip_packet_drop_rate=False):
        self.features = features
        self.derived = derived
        self.clip_packet_drop_rate = clip_packet_drop_rate

    def fit(self, X, y=None):
        if len(set(self.features)) != len(self.features):
            raise ValueError("Repeated primary features")
        if len(set(self.derived)) != len(self.derived) or set(self.derived) - RATIOS.keys():
            raise ValueError("Unknown or repeated derived features")
        self._raw(X)
        self.feature_names_in_ = np.asarray(self.features, dtype=object)
        self.n_features_in_ = len(self.features)
        return self

    def _raw(self, X):
        if not isinstance(X, pd.DataFrame) or list(X.columns) != list(self.features):
            raise ValueError("Input columns must match the frozen feature order")
        values = X.to_numpy(dtype=float, copy=True)
        if not np.isfinite(values).all():
            raise ValueError("Raw features must be finite; revise the data audit")
        return values

    def transform(self, X):
        check_is_fitted(self, "feature_names_in_")
        values = self._raw(X)
        if self.clip_packet_drop_rate:
            index = list(self.features).index("PacketDropRate")
            values[:, index] = np.clip(values[:, index], 0, 1)
        extra = []
        for name in self.derived:
            numerator, denominator = RATIOS[name]
            num = values[:, list(self.features).index(numerator)]
            den = values[:, list(self.features).index(denominator)]
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                ratio = np.divide(num, den, out=np.full(len(X), np.nan), where=den > 0)
            ratio[~np.isfinite(ratio)] = np.nan
            extra.append(ratio)
        return np.column_stack([values, *extra]) if extra else values

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_in_")
        return np.asarray([*self.features, *self.derived], dtype=object)
