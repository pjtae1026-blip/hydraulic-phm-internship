import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))
from src.data_loader import SENSOR_SPECS, LABEL_DESCRIPTIONS, load_all_sensors, load_labels

def create_mock_uci_dataset(base_dir: Path, n_cycles: int = 10):
    print("[Harness] Mock dataset generation...")

    for name, spec in SENSOR_SPECS.items():
        mock_data = np.random.randn(n_cycles, spec["cols"])
        np.savetxt(base_dir / f"{name}.txt", mock_data, delimiter="\t")

    mock_labels = np.array([[3, 100, 0, 130, 0] for _ in range(n_cycles)])
    np.savetxt(base_dir / "profile.txt", mock_labels, delimiter="\t")
    print(f"[Harness] {n_cycles} cycles mock data created.")

def run_data_loader_harness():
    print("\n[Harness] Data loader contract validation start...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        n_cycles = 15
        create_mock_uci_dataset(tmp_path, n_cycles=n_cycles)

        try:
            sensors = load_all_sensors(tmp_path)
            labels = load_labels(tmp_path)

            print("\n[Harness] Shape & integrity checks...")

            assert len(sensors) == 17, f"Sensor count != 17 (got {len(sensors)})"
            assert len(labels) == n_cycles, f"Label rows ({len(labels)}) != cycles ({n_cycles})"

            for name, data in sensors.items():
                expected_cols = SENSOR_SPECS[name]["cols"]

                if data.shape[0] != n_cycles:
                    raise ValueError(f"{name}: cycle count {data.shape[0]} != {n_cycles}")

                if data.shape[1] != expected_cols:
                    raise ValueError(f"{name}: timesteps {data.shape[1]} != spec {expected_cols}")

                if np.isnan(data).any():
                    raise ValueError(f"{name}: NaN detected!")

            print("\n[Harness] ALL PASSED. Pipeline contracts verified.")
            print(f"  17 sensors, all {n_cycles} cycles, shapes match specs, no NaN.")

        except Exception as e:
            print(f"\n[Harness] FAILED: {e}")
            raise e

if __name__ == "__main__":
    run_data_loader_harness()
