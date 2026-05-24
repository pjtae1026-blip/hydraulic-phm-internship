"""Signal preprocessing: normalization, resampling, filtering, steady-state extraction."""

import numpy as np
from scipy import signal as sig


def normalize_zscore(X: np.ndarray, axis: int = 1):
    """Per-cycle z-score normalization. Returns (normalized, mean, std)."""
    mean = X.mean(axis=axis, keepdims=True)
    std = X.std(axis=axis, keepdims=True)
    std[std == 0] = 1.0
    return (X - mean) / std, mean.squeeze(), std.squeeze()


def normalize_minmax(X: np.ndarray, axis: int = 1) -> np.ndarray:
    """Per-cycle min-max normalization to [0, 1]."""
    xmin = X.min(axis=axis, keepdims=True)
    xmax = X.max(axis=axis, keepdims=True)
    denom = xmax - xmin
    denom[denom == 0] = 1.0
    return (X - xmin) / denom


def upsample_repeat(X: np.ndarray, target_length: int) -> np.ndarray:
    """Nearest-neighbor upsampling by repeating samples."""
    n_cycles, n_cols = X.shape
    indices = np.round(np.linspace(0, n_cols - 1, target_length)).astype(int)
    return X[:, indices]


def upsample_linear(X: np.ndarray, target_length: int) -> np.ndarray:
    """Linear interpolation upsampling."""
    n_cycles, n_cols = X.shape
    x_old = np.linspace(0, 1, n_cols)
    x_new = np.linspace(0, 1, target_length)
    result = np.zeros((n_cycles, target_length))
    for i in range(n_cycles):
        result[i] = np.interp(x_new, x_old, X[i])
    return result


def resample_to(X: np.ndarray, target_length: int) -> np.ndarray:
    """FFT-based resampling via scipy.signal.resample."""
    return sig.resample(X, target_length, axis=1)


def butterworth_filter(
    X: np.ndarray, cutoff_hz: float, fs: float, order: int = 4, btype: str = "low"
) -> np.ndarray:
    """Apply Butterworth filter per cycle."""
    sos = sig.butter(order, cutoff_hz, btype=btype, fs=fs, output="sos")
    result = np.zeros_like(X)
    for i in range(X.shape[0]):
        result[i] = sig.sosfiltfilt(sos, X[i])
    return result


def extract_steady_state(
    X: np.ndarray, start_frac: float = 0.5, end_frac: float = 1.0
) -> np.ndarray:
    """Extract steady-state portion of each cycle (default: last 50%)."""
    n_cols = X.shape[1]
    i_start = int(n_cols * start_frac)
    i_end = int(n_cols * end_frac)
    return X[:, i_start:i_end]
