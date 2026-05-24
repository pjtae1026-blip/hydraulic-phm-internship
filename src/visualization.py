"""Reusable plotting functions for EDA and reporting."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import signal as sig

from .data_loader import LABEL_DESCRIPTIONS, SENSOR_SPECS


def plot_label_distribution(labels: pd.DataFrame) -> plt.Figure:
    """Bar charts for all 5 target variables showing class balance."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()

    for i, col in enumerate(labels.columns):
        ax = axes[i]
        counts = labels[col].value_counts().sort_index()
        desc = LABEL_DESCRIPTIONS[col]["values"]
        tick_labels = [f"{v}\n({desc.get(v, '?')})" for v in counts.index]
        ax.bar(range(len(counts)), counts.values, color=sns.color_palette("Set2", len(counts)))
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(tick_labels, fontsize=8)
        ax.set_title(f"{col} (n_classes={len(counts)})")
        ax.set_ylabel("Count")

    axes[-1].axis("off")
    fig.suptitle("Label Distribution", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_cycle_examples(
    sensor_data: np.ndarray, sensor_name: str, labels: pd.Series, n_per_class: int = 2
) -> plt.Figure:
    """Overlay time-series from different classes for one sensor."""
    spec = SENSOR_SPECS[sensor_name]
    classes = sorted(labels.unique())
    colors = sns.color_palette("tab10", len(classes))
    time = np.arange(sensor_data.shape[1]) / spec["sampling_hz"]

    fig, ax = plt.subplots(figsize=(12, 4))
    for cls, color in zip(classes, colors):
        idx = np.where(labels.values == cls)[0][:n_per_class]
        for j, i in enumerate(idx):
            label = f"{cls}" if j == 0 else None
            ax.plot(time, sensor_data[i], color=color, alpha=0.7, label=label)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel(f"{sensor_name} ({spec['unit']})")
    ax.set_title(f"{sensor_name}: Cycle Examples by {labels.name}")
    ax.legend(title=labels.name, fontsize=8)
    fig.tight_layout()
    return fig


def plot_class_mean_std(
    sensor_data: np.ndarray, sensor_name: str, labels: pd.Series
) -> plt.Figure:
    """Mean signal with shaded +/- 1 sigma band per class."""
    spec = SENSOR_SPECS[sensor_name]
    classes = sorted(labels.unique())
    colors = sns.color_palette("tab10", len(classes))
    time = np.arange(sensor_data.shape[1]) / spec["sampling_hz"]

    fig, ax = plt.subplots(figsize=(12, 4))
    for cls, color in zip(classes, colors):
        mask = labels.values == cls
        X_cls = sensor_data[mask]
        mean = X_cls.mean(axis=0)
        std = X_cls.std(axis=0)
        ax.plot(time, mean, color=color, label=f"{cls} (n={mask.sum()})")
        ax.fill_between(time, mean - std, mean + std, color=color, alpha=0.15)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel(f"{sensor_name} ({spec['unit']})")
    ax.set_title(f"{sensor_name}: Mean ± 1σ by {labels.name}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def plot_psd_by_class(
    sensor_data: np.ndarray, sensor_name: str, labels: pd.Series, fs: float
) -> plt.Figure:
    """PSD curves colored by class."""
    classes = sorted(labels.unique())
    colors = sns.color_palette("tab10", len(classes))

    fig, ax = plt.subplots(figsize=(10, 4))
    for cls, color in zip(classes, colors):
        mask = labels.values == cls
        X_cls = sensor_data[mask]
        freqs, psd = sig.welch(X_cls, fs=fs, axis=1)
        mean_psd = psd.mean(axis=0)
        ax.semilogy(freqs, mean_psd, color=color, label=f"{cls}")

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD")
    ax.set_title(f"{sensor_name}: Power Spectral Density by {labels.name}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def plot_multifault_heatmap(labels: pd.DataFrame) -> plt.Figure:
    """Crosstab heatmap showing co-occurrence of fault conditions."""
    targets = ["cooler", "valve", "pump", "accumulator"]
    n = len(targets)
    fig, axes = plt.subplots(n - 1, n - 1, figsize=(14, 12))

    for i in range(n - 1):
        for j in range(n - 1):
            ax = axes[i][j]
            if j <= i:
                ct = pd.crosstab(labels[targets[i + 1]], labels[targets[j]])
                sns.heatmap(ct, annot=True, fmt="d", cmap="YlOrRd", ax=ax, cbar=False)
                ax.set_xlabel(targets[j])
                ax.set_ylabel(targets[i + 1])
            else:
                ax.axis("off")

    fig.suptitle("Multi-Fault Co-occurrence", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_correlation_matrix(feature_df: pd.DataFrame, max_features: int = 50) -> plt.Figure:
    """Feature correlation heatmap (limited to first N features for readability)."""
    numeric_cols = feature_df.select_dtypes(include=[np.number]).columns
    cols = numeric_cols[:max_features]
    corr = feature_df[cols].corr()

    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(corr, cmap="RdBu_r", center=0, ax=ax, xticklabels=True, yticklabels=True)
    ax.set_title("Feature Correlation Matrix")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    return fig


def plot_confusion_matrix(
    y_true, y_pred, class_names: list, title: str = ""
) -> plt.Figure:
    """Confusion matrix with counts and percentages."""
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred)
    cm_pct = cm.astype(float) / cm.sum(axis=1, keepdims=True) * 100

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=class_names, yticklabels=class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title or "Confusion Matrix")
    fig.tight_layout()
    return fig
