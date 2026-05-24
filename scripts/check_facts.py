import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.data_loader import load_all_sensors, load_labels, get_data_dir, SENSOR_SPECS
import numpy as np
from scipy import signal as sig

data_dir = get_data_dir()
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)

# 1) Sensor shapes and actual sampling rates
print("=== Sensor shapes (cols = samples per cycle) ===")
for name in ['PS1','FS1','FS2','TS1','TS2','TS3','TS4','VS1','CE','CP','SE','EPS1']:
    shape = sensors[name].shape
    spec_hz = SENSOR_SPECS[name]['sampling_hz']
    print(f"  {name:5s}: shape={shape}, spec_hz={spec_hz}, cols={shape[1]}")

# 2) Group by actual sample count
print("\n=== Grouping by sample count ===")
groups = {}
for name, spec in SENSOR_SPECS.items():
    cols = sensors[name].shape[1]
    groups.setdefault(cols, []).append(f"{name}({spec['sampling_hz']}Hz)")
for cols, names in sorted(groups.items(), reverse=True):
    hz = 60 / (60 / (cols / 60))  # cycle=60s
    print(f"  {cols} samples -> {cols/60:.0f} Hz: {', '.join(names)}")

# 3) PSD characteristics for PS1 vs PS4
print("\n=== PSD peak frequencies ===")
for ps in ['PS1','PS2','PS4']:
    freqs, psd = sig.welch(sensors[ps], fs=100, axis=1)
    mean_psd = psd.mean(axis=0)
    # Find top 3 peaks
    from scipy.signal import find_peaks
    peaks, props = find_peaks(np.log10(mean_psd), height=-5, prominence=0.3)
    if len(peaks) > 0:
        sorted_idx = np.argsort(mean_psd[peaks])[::-1][:5]
        top_peaks = peaks[sorted_idx]
        print(f"  {ps} top peak freqs: {freqs[top_peaks].round(1)} Hz")
        print(f"     PSD shape: max at {freqs[np.argmax(mean_psd)]:.1f} Hz, "
              f"monotonic decay after: {'Yes' if np.all(np.diff(mean_psd[5:]) <= 0) else 'No'}")
    else:
        print(f"  {ps}: no prominent peaks found")
    # Check 10-15 Hz range
    mask = (freqs >= 10) & (freqs <= 15)
    local_max = freqs[mask][np.argmax(mean_psd[mask])]
    print(f"     10-15Hz local max at {local_max:.1f} Hz, PSD={mean_psd[mask].max():.2e}")

# 4) Confusion matrix check - what classes get confused for accumulator
print("\n=== Accumulator classes ===")
accu_classes = sorted(labels['accumulator'].unique())
print(f"  Classes: {accu_classes}")
for c in accu_classes:
    n = (labels['accumulator'] == c).sum()
    print(f"  class {c}: {n} samples")
