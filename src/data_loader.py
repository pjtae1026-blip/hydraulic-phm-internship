"""Load UCI Hydraulic Systems dataset (17 sensors + 5 labels)."""

import numpy as np
import pandas as pd
from pathlib import Path

SENSOR_SPECS = {
    "PS1": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 1", "cols": 6000},
    "PS2": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 2", "cols": 6000},
    "PS3": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 3", "cols": 6000},
    "PS4": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 4", "cols": 6000},
    "PS5": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 5", "cols": 6000},
    "PS6": {"unit": "bar", "sampling_hz": 100, "physical": "Pressure sensor 6", "cols": 6000},
    "EPS1": {"unit": "W", "sampling_hz": 100, "physical": "Motor power", "cols": 6000},
    "FS1": {"unit": "l/min", "sampling_hz": 10, "physical": "Volume flow sensor 1", "cols": 600},
    "FS2": {"unit": "l/min", "sampling_hz": 10, "physical": "Volume flow sensor 2", "cols": 600},
    "TS1": {"unit": "°C", "sampling_hz": 1, "physical": "Temperature sensor 1", "cols": 60},
    "TS2": {"unit": "°C", "sampling_hz": 1, "physical": "Temperature sensor 2", "cols": 60},
    "TS3": {"unit": "°C", "sampling_hz": 1, "physical": "Temperature sensor 3", "cols": 60},
    "TS4": {"unit": "°C", "sampling_hz": 1, "physical": "Temperature sensor 4", "cols": 60},
    "VS1": {"unit": "mm/s", "sampling_hz": 1, "physical": "Vibration sensor", "cols": 60},
    "CE": {"unit": "%", "sampling_hz": 1, "physical": "Cooling efficiency (virtual)", "cols": 60},
    "CP": {"unit": "kW", "sampling_hz": 1, "physical": "Cooling power (virtual)", "cols": 60},
    "SE": {"unit": "%", "sampling_hz": 1, "physical": "Efficiency factor (virtual)", "cols": 60},
}

LABEL_DESCRIPTIONS = {
    "cooler": {
        "column_index": 0,
        "values": {3: "close to total failure", 20: "reduced efficiency", 100: "full efficiency"},
    },
    "valve": {
        "column_index": 1,
        "values": {100: "optimal", 90: "small lag", 80: "severe lag", 73: "close to total failure"},
    },
    "pump": {
        "column_index": 2,
        "values": {0: "no leakage", 1: "weak leakage", 2: "severe leakage"},
    },
    "accumulator": {
        "column_index": 3,
        "values": {130: "optimal pressure", 115: "slightly reduced", 100: "severely reduced", 90: "close to total failure"},
    },
    "stable": {
        "column_index": 4,
        "values": {0: "conditions were stable", 1: "static conditions might not have been reached"},
    },
}


def get_data_dir() -> Path:
    """Auto-detect data/uci/ relative to project root."""
    candidates = [
        Path(__file__).resolve().parent.parent / "data" / "uci",
        Path.cwd() / "data" / "uci",
    ]
    for c in candidates:
        if c.exists() and (c / "PS1.txt").exists():
            return c
    raise FileNotFoundError(
        "Data directory not found. Run: python scripts/download_data.py"
    )


def load_sensor(name: str, data_dir: Path) -> np.ndarray:
    """Load one sensor file. Returns shape (n_cycles, n_timesteps)."""
    path = data_dir / f"{name}.txt"
    return np.loadtxt(path, delimiter="\t")


def load_all_sensors(data_dir: Path) -> dict:
    """Load all 17 sensors. Returns dict[name] -> ndarray."""
    sensors = {}
    for name in SENSOR_SPECS:
        print(f"  Loading {name} ...", end="")
        sensors[name] = load_sensor(name, data_dir)
        print(f" shape {sensors[name].shape}")
    return sensors


def load_labels(data_dir: Path) -> pd.DataFrame:
    """Load profile.txt as DataFrame with named columns."""
    path = data_dir / "profile.txt"
    data = np.loadtxt(path, delimiter="\t")
    columns = ["cooler", "valve", "pump", "accumulator", "stable"]
    df = pd.DataFrame(data, columns=columns).astype(int)
    return df
