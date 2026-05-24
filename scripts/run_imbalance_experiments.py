"""
Week 2 - Script 2: 불균형 데이터 처리 4종 실험 비교
E1: baseline (아무 처리 없음)
E2: class_weight='balanced'
E3: SMOTE
E4: SMOTE + class_weight='balanced'
"""
import sys, os, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, f1_score, matthews_corrcoef,
                             recall_score, classification_report)
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from src.data_loader import load_all_sensors, load_labels, get_data_dir, LABEL_DESCRIPTIONS
from src.features import extract_all_features

# ─── 데이터 로드 ───
print("=" * 70)
print("불균형 데이터 처리 4종 실험")
print("=" * 70)
data_dir = get_data_dir()
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)

feature_df = extract_all_features(sensors, labels)
label_cols = ['cooler', 'valve', 'pump', 'accumulator']
feature_cols = [c for c in feature_df.columns if c not in labels.columns]
X = feature_df[feature_cols].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# ─── 4종 실험 정의 ───
# RF를 기본 분류기로 사용 (class_weight 지원)
experiments = {
    'E1: Baseline': ImbPipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ]),
    'E2: class_weight': ImbPipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))
    ]),
    'E3: SMOTE': ImbPipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42)),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ]),
    'E4: SMOTE+weight': ImbPipeline([
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42)),
        ('clf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))
    ]),
}

# ─── 실험 실행 ───
all_results = []

for target in label_cols:
    y = labels[target].values
    classes = sorted(np.unique(y))

    print(f"\n--- {target.upper()} ---")
    desc = LABEL_DESCRIPTIONS[target]['values']
    for c in classes:
        n = (y == c).sum()
        print(f"  class {c} ({desc.get(c, '?')[:20]}): {n} samples")

    for exp_name, pipe in experiments.items():
        y_pred = cross_val_predict(pipe, X, y, cv=cv)

        acc = accuracy_score(y, y_pred) * 100
        macro_f1 = f1_score(y, y_pred, average='macro') * 100
        mcc = matthews_corrcoef(y, y_pred)

        # 소수 클래스별 recall
        recalls = recall_score(y, y_pred, average=None, labels=classes)
        minority_recall = min(recalls) * 100  # 가장 낮은 클래스의 recall

        row = {
            'Component': target,
            'Experiment': exp_name,
            'Accuracy': f'{acc:.2f}',
            'Macro-F1': f'{macro_f1:.2f}',
            'MCC': f'{mcc:.4f}',
            'Min Recall': f'{minority_recall:.2f}',
        }
        # 클래스별 recall 추가
        for c, r in zip(classes, recalls):
            row[f'R({c})'] = f'{r*100:.1f}'

        all_results.append(row)

# ─── 결과 출력 ───
print("\n" + "=" * 70)
print("불균형 실험 종합 결과")
print("=" * 70)

for target in label_cols:
    print(f"\n{'─'*50}")
    print(f"  {target.upper()}")
    print(f"{'─'*50}")
    subset = [r for r in all_results if r['Component'] == target]
    df = pd.DataFrame(subset)
    cols_to_show = ['Experiment', 'Accuracy', 'Macro-F1', 'MCC', 'Min Recall']
    # recall 컬럼 추가
    recall_cols = [c for c in df.columns if c.startswith('R(')]
    cols_to_show.extend(recall_cols)
    print(df[cols_to_show].to_string(index=False))

# ─── 그래프: Macro-F1 비교 ───
fig_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
os.makedirs(fig_dir, exist_ok=True)

fig, axes = plt.subplots(1, 4, figsize=(18, 5))
for i, target in enumerate(label_cols):
    ax = axes[i]
    subset = [r for r in all_results if r['Component'] == target]
    names = [r['Experiment'].split(': ')[1] for r in subset]
    f1s = [float(r['Macro-F1']) for r in subset]
    bars = ax.bar(names, f1s, color=['#4C72B0', '#55A868', '#C44E52', '#8172B2'])
    ax.set_title(target)
    ax.set_ylabel('Macro-F1 (%)')
    ax.set_ylim(min(f1s) - 2, 100.5)
    for bar, v in zip(bars, f1s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{v:.1f}', ha='center', va='bottom', fontsize=8)
fig.suptitle('Imbalance Handling: Macro-F1 Comparison', fontweight='bold')
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'imbalance_macro_f1.png'), dpi=150)
plt.close(fig)

print("\n" + "=" * 70)
print("결과 해석")
print("=" * 70)
print("""
1. Cooler: 3클래스 균형이라 4종 실험 간 차이가 미미합니다.
2. Valve: optimal(100) 클래스가 3.1배 많지만, RF의 앙상블 특성이
   불균형을 어느 정도 흡수합니다. class_weight가 소수 클래스 recall을
   개선하는지 R(73), R(80), R(90) 값을 확인하세요.
3. Pump: no_leakage(0)가 2.5배 많습니다. SMOTE가 weak/severe leakage
   클래스의 recall을 높이는지 R(1), R(2) 값으로 확인합니다.
4. Accumulator: 4클래스 중 90(고장)이 가장 많습니다.

결론: 이 데이터는 LDA/RF로도 매우 높은 성능을 보여
불균형 처리의 효과가 크지 않을 수 있습니다.
주요 발견은 '불균형이 있지만 특성 분리가 좋아 영향이 제한적'이라는 점입니다.
그래프가 reports/figures/imbalance_macro_f1.png에 저장되었습니다.
""")
