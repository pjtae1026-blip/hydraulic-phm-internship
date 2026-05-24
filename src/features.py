"""Feature extraction: time-domain, frequency-domain, wavelet, cross-correlation."""

import numpy as np
import pandas as pd
from scipy import signal as sig
from scipy.stats import skew, kurtosis

from .data_loader import SENSOR_SPECS


def time_domain_features(X: np.ndarray) -> np.ndarray:
    """Extract 11 time-domain features per cycle. Input shape (n_cycles, n_timesteps).
    Returns shape (n_cycles, 11).
    """
    mean = X.mean(axis=1)
    std = X.std(axis=1)
    rms = np.sqrt(np.mean(X ** 2, axis=1))
    peak = np.max(np.abs(X), axis=1)
    mean_abs = np.mean(np.abs(X), axis=1)
    mean_abs[mean_abs == 0] = 1e-10

    crest_factor = peak / (rms + 1e-10)
    sk = skew(X, axis=1, nan_policy="omit")
    sk = np.nan_to_num(sk, nan=0.0)
    kurt = kurtosis(X, axis=1, nan_policy="omit")
    kurt = np.nan_to_num(kurt, nan=0.0)
    peak_to_peak = X.max(axis=1) - X.min(axis=1)
    shape_factor = rms / mean_abs
    impulse_factor = peak / mean_abs
    mean_sqrt = np.mean(np.sqrt(np.abs(X)), axis=1) ** 2
    mean_sqrt[mean_sqrt == 0] = 1e-10
    clearance_factor = peak / mean_sqrt

    return np.column_stack([
        mean, std, rms, peak, crest_factor,
        sk, kurt, peak_to_peak, shape_factor,
        impulse_factor, clearance_factor,
    ])


TIME_FEATURE_NAMES = [
    "mean", "std", "rms", "peak", "crest_factor",
    "skewness", "kurtosis", "peak_to_peak", "shape_factor",
    "impulse_factor", "clearance_factor",
]


def compute_psd(X: np.ndarray, fs: float):
    """Power spectral density via Welch's method. Returns (freqs, psd) arrays."""
    freqs, psd = sig.welch(X, fs=fs, axis=1)
    return freqs, psd


def psd_band_energy(psd: np.ndarray, freqs: np.ndarray, bands: list) -> np.ndarray:
    """Energy in specified frequency bands. bands = [(low, high), ...]."""
    result = np.zeros((psd.shape[0], len(bands)))
    for i, (low, high) in enumerate(bands):
        mask = (freqs >= low) & (freqs <= high)
        result[:, i] = psd[:, mask].sum(axis=1)
    return result


def wavelet_energy(X: np.ndarray, wavelet: str = "db4", level: int = 4) -> np.ndarray:
    """Multi-level wavelet decomposition energy per level."""
    import pywt

    n_cycles = X.shape[0]
    result = np.zeros((n_cycles, level + 1))
    for i in range(n_cycles):
        coeffs = pywt.wavedec(X[i], wavelet, level=level)
        for j, c in enumerate(coeffs):
            result[i, j] = np.sum(c ** 2)
    return result


def pressure_cross_correlation(sensors: dict, pairs: list = None) -> np.ndarray:
    """Cross-correlation between pressure sensor pairs (H1 hypothesis).
    Returns (n_cycles, n_pairs * 2) with max_corr and lag for each pair.
    """
    pressure_names = [f"PS{i}" for i in range(1, 7)]
    if pairs is None:
        pairs = []
        for i in range(len(pressure_names)):
            for j in range(i + 1, len(pressure_names)):
                pairs.append((pressure_names[i], pressure_names[j]))

    n_cycles = sensors[pairs[0][0]].shape[0]
    result = np.zeros((n_cycles, len(pairs) * 2))

    for idx, (a, b) in enumerate(pairs):
        for c in range(n_cycles):
            xa = sensors[a][c]
            xb = sensors[b][c]
            xa = (xa - xa.mean()) / (xa.std() + 1e-10)
            xb = (xb - xb.mean()) / (xb.std() + 1e-10)
            corr = np.correlate(xa, xb, mode="full") / len(xa)
            max_corr = np.max(np.abs(corr))
            lag = np.argmax(np.abs(corr)) - (len(xa) - 1)
            result[c, idx * 2] = max_corr
            result[c, idx * 2 + 1] = lag

    return result


def extract_all_features(sensors: dict, labels: pd.DataFrame) -> pd.DataFrame:
    """Extract time-domain features from all sensors into a flat DataFrame."""
    all_features = []
    feature_names = []

    for name, spec in SENSOR_SPECS.items():
        X = sensors[name]
        feats = time_domain_features(X)
        all_features.append(feats)
        for fn in TIME_FEATURE_NAMES:
            feature_names.append(f"{name}_{fn}")

    feature_matrix = np.hstack(all_features)
    df = pd.DataFrame(feature_matrix, columns=feature_names)

    for col in labels.columns:
        df[col] = labels[col].values

    return df
