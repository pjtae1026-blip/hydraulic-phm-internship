"""
Week 2 - Script 3: PS4 센서 독자적 거동의 물리적 원인 가설 검증
- PS4 vs 각 라벨 간 mutual information
- PS4 vs PS1/PS2/PS3, PS5/PS6 피어슨 상관계수
- PS4 PSD 분석
"""
import sys, os, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import signal as sig
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import StandardScaler

from src.data_loader import load_all_sensors, load_labels, get_data_dir, SENSOR_SPECS
from src.features import time_domain_features, TIME_FEATURE_NAMES

# ─── 데이터 로드 ───
print("=" * 60)
print("PS4 센서 독자적 거동 가설 검증")
print("=" * 60)
data_dir = get_data_dir()
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)

fig_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
os.makedirs(fig_dir, exist_ok=True)

# ─── 1. Mutual Information: PS4 특성 vs 각 라벨 ───
print("\n[1] PS4 특성 vs 각 라벨 Mutual Information")
print("-" * 50)

# 모든 압력센서의 특성 추출
pressure_sensors = ['PS1', 'PS2', 'PS3', 'PS4', 'PS5', 'PS6']
mi_results = []

for ps in pressure_sensors:
    feats = time_domain_features(sensors[ps])
    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
    scaler = StandardScaler()
    feats_scaled = scaler.fit_transform(feats)

    for target in ['cooler', 'valve', 'pump', 'accumulator']:
        y = labels[target].values
        mi = mutual_info_classif(feats_scaled, y, random_state=42)
        mi_mean = mi.mean()
        mi_results.append({
            'Sensor': ps,
            'Target': target,
            'Mean MI': f'{mi_mean:.4f}',
            'MI_val': mi_mean,
        })

df_mi = pd.DataFrame(mi_results)
print("\n센서별 라벨별 Mean Mutual Information:")
pivot = df_mi.pivot_table(values='MI_val', index='Sensor', columns='Target')
print(pivot.round(4).to_string())

# MI heatmap 저장
fig, ax = plt.subplots(figsize=(8, 5))
sns.heatmap(pivot, annot=True, fmt='.4f', cmap='YlOrRd', ax=ax)
ax.set_title('Mutual Information: Pressure Sensors vs Fault Labels')
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'ps4_mutual_information.png'), dpi=150)
plt.close(fig)

# ─── 2. 피어슨 상관계수: PS4 vs 나머지 ───
print("\n[2] 센서 간 피어슨 상관계수 (시간도메인 mean 기준)")
print("-" * 50)

# 각 센서의 사이클별 평균값으로 상관계수 계산
means = {}
for ps in pressure_sensors:
    means[ps] = sensors[ps].mean(axis=1)

mean_df = pd.DataFrame(means)
corr = mean_df.corr()

print("\n압력센서 간 상관계수 행렬:")
print(corr.round(4).to_string())

# PS4 행만 강조
print("\n\nPS4와의 상관계수:")
for ps in pressure_sensors:
    if ps != 'PS4':
        r = corr.loc['PS4', ps]
        group = '1차 회로' if ps in ['PS1','PS2','PS3'] else '2차/기타'
        print(f"  PS4 vs {ps} ({group}): r = {r:.4f}")

# 상관계수 heatmap
fig, ax = plt.subplots(figsize=(7, 6))
sns.heatmap(corr, annot=True, fmt='.3f', cmap='RdBu_r', center=0, ax=ax,
            vmin=-1, vmax=1)
ax.set_title('Pressure Sensor Cross-Correlation (cycle mean)')
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'ps4_correlation_matrix.png'), dpi=150)
plt.close(fig)

# ─── 3. PSD 비교: PS4 vs PS1/PS2/PS3 ───
print("\n[3] PSD 비교: PS4 vs PS1/PS2/PS3")
print("-" * 50)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for i, ps in enumerate(['PS1', 'PS2', 'PS3', 'PS4']):
    ax = axes[i // 2][i % 2]
    freqs, psd = sig.welch(sensors[ps], fs=100, axis=1)
    mean_psd = psd.mean(axis=0)

    ax.semilogy(freqs, mean_psd, linewidth=1.5,
                color='red' if ps == 'PS4' else 'steelblue')
    ax.set_title(f'{ps} (Mean PSD, all cycles)')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('PSD')
    ax.grid(True, alpha=0.3)

fig.suptitle('PSD Comparison: PS1-PS3 (1st circuit) vs PS4', fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'ps4_psd_comparison.png'), dpi=150)
plt.close(fig)

# Accumulator 조건별 PS4 PSD
fig, ax = plt.subplots(figsize=(10, 5))
accu_classes = sorted(labels['accumulator'].unique())
colors = sns.color_palette('tab10', len(accu_classes))
for cls, color in zip(accu_classes, colors):
    mask = labels['accumulator'].values == cls
    freqs, psd = sig.welch(sensors['PS4'][mask], fs=100, axis=1)
    ax.semilogy(freqs, psd.mean(axis=0), color=color, label=f'accu={cls}')
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('PSD')
ax.set_title('PS4 PSD by Accumulator Condition')
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'ps4_psd_by_accumulator.png'), dpi=150)
plt.close(fig)

# ─── 결과 해석 ───
print("\n" + "=" * 60)
print("가설 검증 결과 해석")
print("=" * 60)

# PS4-accumulator MI vs 다른 센서-accumulator MI 비교
ps4_accu_mi = float([r for r in mi_results
                     if r['Sensor'] == 'PS4' and r['Target'] == 'accumulator'][0]['MI_val'])
ps1_accu_mi = float([r for r in mi_results
                     if r['Sensor'] == 'PS1' and r['Target'] == 'accumulator'][0]['MI_val'])

ps4_ps1_corr = corr.loc['PS4', 'PS1']
ps4_ps5_corr = corr.loc['PS4', 'PS5']

print(f"""
[가설 1: 어큐뮬레이터 분기]
  PS4-accumulator MI = {ps4_accu_mi:.4f}
  PS1-accumulator MI = {ps1_accu_mi:.4f}
  → PS4가 accumulator 라벨과 {'더 높은' if ps4_accu_mi > ps1_accu_mi else '비슷하거나 낮은'} MI를 보임

[가설 2: 2차 냉각/여과 회로]
  PS4-PS5 상관: r = {ps4_ps5_corr:.4f}
  PS4-PS1 상관: r = {ps4_ps1_corr:.4f}
  → PS4가 PS5/PS6(2차 회로 추정)과 {'더 높은' if abs(ps4_ps5_corr) > abs(ps4_ps1_corr) else '더 낮은'} 상관

[가설 3: 밸브 하류]
  PS4-valve MI 확인 필요

[종합 판단]
  - PS4는 PS1-PS3과 상관이 {('높음' if abs(ps4_ps1_corr) > 0.5 else '낮음')} (r={ps4_ps1_corr:.4f})
  - 어큐뮬레이터의 가스 챔버가 저역통과 필터로 작용하여 PS4의 PSD 형태가 다를 수 있음
  - PSD 그래프에서 PS4의 고주파 감쇠 패턴을 PS1-PS3과 비교하면 판단 가능

그래프 저장 위치:
  - reports/figures/ps4_mutual_information.png
  - reports/figures/ps4_correlation_matrix.png
  - reports/figures/ps4_psd_comparison.png
  - reports/figures/ps4_psd_by_accumulator.png
""")
