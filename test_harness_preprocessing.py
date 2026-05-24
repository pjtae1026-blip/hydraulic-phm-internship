"""Preprocessing harness: validate resampling, normalization, and pipeline composition."""

import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from src.data_loader import SENSOR_SPECS
from src.preprocessing import (
    normalize_zscore,
    normalize_minmax,
    upsample_repeat,
    upsample_linear,
    resample_to,
    butterworth_filter,
    extract_steady_state,
)

N_CYCLES = 15
TARGET_LENGTH = 600  # 10Hz 기준으로 통일 (60->600 up, 6000->600 down)


def make_mock_sensors(n_cycles: int = N_CYCLES) -> dict:
    """data_loader 하네스와 동일한 규격의 mock 센서 데이터 생성"""
    sensors = {}
    for name, spec in SENSOR_SPECS.items():
        sensors[name] = np.random.randn(n_cycles, spec["cols"])
    return sensors


# ── Contract 1: Shape 통일 검증 ──────────────────────────────────

def test_resample_unifies_shape():
    """리샘플링 후 17개 센서 모두 (n_cycles, TARGET_LENGTH) shape이 되는가"""
    print("[Contract 1] Resampling shape unification test...")
    sensors = make_mock_sensors()

    resample_methods = {
        "upsample_repeat": upsample_repeat,
        "upsample_linear": upsample_linear,
        "resample_to (FFT)": resample_to,
    }

    for method_name, resample_fn in resample_methods.items():
        print(f"  Method: {method_name}")
        shapes = {}
        for name, data in sensors.items():
            result = resample_fn(data, TARGET_LENGTH)
            shapes[name] = result.shape

            assert result.shape == (N_CYCLES, TARGET_LENGTH), (
                f"  FAIL: {name} -> {result.shape}, expected ({N_CYCLES}, {TARGET_LENGTH})"
            )

        unique_shapes = set(shapes.values())
        assert len(unique_shapes) == 1, f"  FAIL: shapes not unified: {unique_shapes}"
        print(f"    PASSED: all 17 sensors -> {unique_shapes.pop()}")


# ── Contract 2: 정규화 값 범위 검증 ──────────────────────────────

def test_normalization_ranges():
    """정규화 결과가 기대 범위 안에 있고 NaN이 없는가"""
    print("\n[Contract 2] Normalization value range test...")
    X = np.random.randn(N_CYCLES, 600) * 100 + 50  # 큰 값 + 오프셋

    # Z-score: mean~0, std~1
    z, mean, std = normalize_zscore(X)
    assert not np.isnan(z).any(), "FAIL: z-score produced NaN"
    per_cycle_mean = np.abs(z.mean(axis=1))
    assert np.all(per_cycle_mean < 1e-10), f"FAIL: z-score mean not ~0: {per_cycle_mean.max()}"
    print("  Z-score: PASSED (mean~0, no NaN)")

    # Min-max: [0, 1]
    mm = normalize_minmax(X)
    assert not np.isnan(mm).any(), "FAIL: min-max produced NaN"
    assert mm.min() >= 0.0 and mm.max() <= 1.0, f"FAIL: min-max out of [0,1]: [{mm.min()}, {mm.max()}]"
    print("  Min-Max: PASSED (range [0, 1], no NaN)")

    # Edge case: constant signal (std=0)
    X_const = np.ones((5, 100)) * 42.0
    z_const, _, _ = normalize_zscore(X_const)
    assert not np.isnan(z_const).any(), "FAIL: z-score on constant signal produced NaN"
    mm_const = normalize_minmax(X_const)
    assert not np.isnan(mm_const).any(), "FAIL: min-max on constant signal produced NaN"
    print("  Constant signal edge case: PASSED (no division-by-zero crash)")


# ── Contract 3: 파이프라인 조합 안전성 ───────────────────────────

def test_pipeline_composition_safety():
    """실제 사용 시나리오: resample -> normalize -> filter 순서 조합 후 NaN/Inf 없는가"""
    print("\n[Contract 3] Pipeline composition safety test...")
    sensors = make_mock_sensors()

    fail_count = 0
    for name, data in sensors.items():
        original_hz = SENSOR_SPECS[name]["sampling_hz"]

        # Step 1: resample to unified length
        unified = resample_to(data, TARGET_LENGTH)

        # Step 2: normalize
        normed = normalize_minmax(unified)

        # Step 3: filter (effective Hz after resampling = TARGET_LENGTH / 60s = 10Hz)
        effective_hz = TARGET_LENGTH / 60.0
        cutoff = effective_hz * 0.4  # Nyquist의 80%
        filtered = butterworth_filter(normed, cutoff_hz=cutoff, fs=effective_hz)

        # Step 4: extract steady state
        steady = extract_steady_state(filtered)

        # Validate
        has_nan = np.isnan(steady).any()
        has_inf = np.isinf(steady).any()
        expected_steady_len = TARGET_LENGTH // 2

        if has_nan or has_inf:
            print(f"  FAIL: {name} -> NaN={has_nan}, Inf={has_inf}")
            fail_count += 1
        elif steady.shape != (N_CYCLES, expected_steady_len):
            print(f"  FAIL: {name} -> shape {steady.shape}, expected ({N_CYCLES}, {expected_steady_len})")
            fail_count += 1

    if fail_count == 0:
        print(f"  PASSED: all 17 sensors survived full pipeline")
        print(f"  Final shape per sensor: ({N_CYCLES}, {TARGET_LENGTH // 2})")
    else:
        raise AssertionError(f"{fail_count} sensors failed pipeline composition")


# ── Contract 4: 다운샘플링 경고 검증 ─────────────────────────────

def test_downsample_information_loss_awareness():
    """6000->600 다운샘플링 시 고주파 정보 손실을 정량적으로 확인"""
    print("\n[Contract 4] Downsample information loss check...")
    np.random.seed(42)
    t = np.linspace(0, 1, 6000)
    # 고주파(45Hz) 성분이 포함된 신호
    high_freq_signal = np.sin(2 * np.pi * 5 * t) + 0.5 * np.sin(2 * np.pi * 45 * t)
    X = high_freq_signal.reshape(1, -1)

    downsampled = resample_to(X, TARGET_LENGTH)
    reconstructed = resample_to(downsampled, 6000)

    mse = np.mean((X - reconstructed) ** 2)
    print(f"  Round-trip MSE (6000->600->6000): {mse:.6f}")
    if mse > 0.01:
        print(f"  WARNING: significant info loss (MSE={mse:.4f}). High-freq components lost in downsampling.")
    else:
        print(f"  Info loss within acceptable range.")
    print("  PASSED (loss quantified, no crash)")


def main():
    print("=" * 60)
    print(" PREPROCESSING HARNESS - Pipeline Contract Validation")
    print("=" * 60)

    test_resample_unifies_shape()
    test_normalization_ranges()
    test_pipeline_composition_safety()
    test_downsample_information_loss_awareness()

    print("\n" + "=" * 60)
    print(" ALL CONTRACTS PASSED")
    print(f" Unified pipeline: 17 sensors -> resample({TARGET_LENGTH})")
    print(f"   -> normalize -> filter -> steady_state({TARGET_LENGTH // 2})")
    print("=" * 60)


if __name__ == "__main__":
    main()
