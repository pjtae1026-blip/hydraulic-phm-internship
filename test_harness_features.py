"""Features harness: validate feature extraction contracts on (n_cycles, 300) input."""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from src.data_loader import SENSOR_SPECS
from src.features import (
    time_domain_features,
    TIME_FEATURE_NAMES,
    compute_psd,
    psd_band_energy,
    pressure_cross_correlation,
    extract_all_features,
)

N_CYCLES = 15
T_UNIFIED = 300  # 전처리 하네스에서 확정된 최종 타임스텝


def make_unified_sensors() -> dict:
    """전처리 완료 후 규격: 모든 센서가 (N_CYCLES, T_UNIFIED)"""
    sensors = {}
    for name in SENSOR_SPECS:
        sensors[name] = np.random.randn(N_CYCLES, T_UNIFIED)
    return sensors


def make_labels() -> pd.DataFrame:
    return pd.DataFrame({
        "cooler": [3] * N_CYCLES,
        "valve": [100] * N_CYCLES,
        "pump": [0] * N_CYCLES,
        "accumulator": [130] * N_CYCLES,
        "stable": [0] * N_CYCLES,
    })


# ── Contract 1: time_domain_features shape & NaN ─────────────────

def test_time_domain_shape_and_values():
    """time_domain_features가 (n, 11)을 반환하고 NaN/Inf가 없는가"""
    print("[Contract 1] Time-domain features shape & value test...")

    X = np.random.randn(N_CYCLES, T_UNIFIED)
    feats = time_domain_features(X)

    assert feats.shape == (N_CYCLES, 11), f"FAIL: shape {feats.shape}, expected ({N_CYCLES}, 11)"
    assert not np.isnan(feats).any(), "FAIL: NaN in time-domain features"
    assert not np.isinf(feats).any(), "FAIL: Inf in time-domain features"
    print(f"  PASSED: shape {feats.shape}, no NaN/Inf")


# ── Contract 2: edge case - constant / zero / spike signal ───────

def test_time_domain_edge_cases():
    """위험 신호(상수, 전부 0, 스파이크)에서도 NaN/Inf 없이 생존하는가"""
    print("\n[Contract 2] Time-domain edge case test...")

    cases = {
        "all_zeros": np.zeros((5, T_UNIFIED)),
        "constant_42": np.ones((5, T_UNIFIED)) * 42.0,
        "single_spike": np.zeros((5, T_UNIFIED)),
        "tiny_values": np.ones((5, T_UNIFIED)) * 1e-15,
        "huge_values": np.ones((5, T_UNIFIED)) * 1e15,
    }
    cases["single_spike"][:, T_UNIFIED // 2] = 1000.0

    for case_name, X in cases.items():
        feats = time_domain_features(X)
        has_nan = np.isnan(feats).any()
        has_inf = np.isinf(feats).any()

        if has_nan or has_inf:
            print(f"  FAIL: {case_name} -> NaN={has_nan}, Inf={has_inf}")
            print(f"    Values: {feats[0]}")
            raise ValueError(f"Edge case '{case_name}' produced invalid values")
        else:
            print(f"  PASSED: {case_name} -> no NaN/Inf")


# ── Contract 3: extract_all_features 최종 DataFrame 규격 ─────────

def test_extract_all_features_contract():
    """extract_all_features가 (n_cycles, 192) DataFrame을 반환하는가"""
    print("\n[Contract 3] extract_all_features final shape test...")

    sensors = make_unified_sensors()
    labels = make_labels()
    df = extract_all_features(sensors, labels)

    expected_feat_cols = 17 * 11  # 187
    expected_total_cols = expected_feat_cols + 5  # 192

    assert isinstance(df, pd.DataFrame), f"FAIL: return type {type(df)}, expected DataFrame"
    assert df.shape == (N_CYCLES, expected_total_cols), (
        f"FAIL: shape {df.shape}, expected ({N_CYCLES}, {expected_total_cols})"
    )
    assert not df.isnull().any().any(), "FAIL: NaN found in final DataFrame"

    # 레이블 컬럼이 올바르게 붙었는가
    for col in ["cooler", "valve", "pump", "accumulator", "stable"]:
        assert col in df.columns, f"FAIL: label column '{col}' missing"

    print(f"  PASSED: DataFrame {df.shape}")
    print(f"    Feature columns: {expected_feat_cols}, Label columns: 5")
    print(f"    Column names sample: {list(df.columns[:5])} ... {list(df.columns[-5:])}")


# ── Contract 4: PSD fs 파라미터 일관성 ────────────────────────────

def test_psd_with_correct_effective_fs():
    """리샘플링 후 실효 fs(=T_UNIFIED/60=5Hz)로 PSD를 돌렸을 때 주파수 축이 정상인가"""
    print("\n[Contract 4] PSD effective sampling frequency test...")

    effective_fs = T_UNIFIED / 60.0  # 300 samples / 60 seconds = 5 Hz
    X = np.random.randn(N_CYCLES, T_UNIFIED)

    freqs, psd = compute_psd(X, fs=effective_fs)

    assert freqs.max() <= effective_fs / 2 + 0.01, (
        f"FAIL: max freq {freqs.max()} exceeds Nyquist {effective_fs/2}"
    )
    assert not np.isnan(psd).any(), "FAIL: NaN in PSD"
    assert (psd >= 0).all(), "FAIL: negative PSD values"

    # band energy test
    bands = [(0, 1), (1, 2)]
    energy = psd_band_energy(psd, freqs, bands)
    assert energy.shape == (N_CYCLES, 2), f"FAIL: band energy shape {energy.shape}"
    assert not np.isnan(energy).any(), "FAIL: NaN in band energy"
    print(f"  PASSED: Nyquist={effective_fs/2}Hz, freqs in [0, {freqs.max():.2f}]")
    print(f"  Band energy shape: {energy.shape}, all non-negative")


# ── Contract 5: cross-correlation on unified data ─────────────────

def test_cross_correlation_on_unified():
    """리샘플링 후 동일 길이 PS센서에 cross-correlation이 정상 동작하는가"""
    print("\n[Contract 5] Cross-correlation on unified sensors...")

    sensors = make_unified_sensors()
    result = pressure_cross_correlation(sensors)

    # PS1~PS6: C(6,2) = 15 pairs, 각 pair당 2값(max_corr, lag)
    expected_cols = 15 * 2
    assert result.shape == (N_CYCLES, expected_cols), (
        f"FAIL: shape {result.shape}, expected ({N_CYCLES}, {expected_cols})"
    )
    assert not np.isnan(result).any(), "FAIL: NaN in cross-correlation"
    assert not np.isinf(result).any(), "FAIL: Inf in cross-correlation"
    print(f"  PASSED: {result.shape}, 15 sensor pairs x 2 (max_corr + lag)")


def main():
    print("=" * 60)
    print(" FEATURES HARNESS - Feature Extraction Contract Validation")
    print("=" * 60)

    test_time_domain_shape_and_values()
    test_time_domain_edge_cases()
    test_extract_all_features_contract()
    test_psd_with_correct_effective_fs()
    test_cross_correlation_on_unified()

    print("\n" + "=" * 60)
    print(" ALL CONTRACTS PASSED")
    print(f" Pipeline: (n, {T_UNIFIED}) -> time_domain -> (n, 11) per sensor")
    print(f" Full extraction: (n, {T_UNIFIED}) x 17 sensors -> DataFrame (n, 192)")
    print("=" * 60)


if __name__ == "__main__":
    main()
