"""
Week 2 - Script 4: ML Baseline 비교 (RF, XGBoost, LightGBM, Extra Trees)
로드맵의 03_baseline_ml에 해당
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

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import make_scorer, f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from src.data_loader import load_all_sensors, load_labels, get_data_dir
from src.features import extract_all_features

# ─── 데이터 로드 ───
print("=" * 70)
print("ML Baseline 비교: LDA vs RF vs XGBoost vs LightGBM vs Extra Trees")
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
macro_f1 = make_scorer(f1_score, average='macro')

# ─── 모델 정의 ───
models = {
    'LDA': Pipeline([('scaler', StandardScaler()), ('clf', LinearDiscriminantAnalysis())]),
    'RF': Pipeline([('scaler', StandardScaler()),
                    ('clf', RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))]),
    'XGBoost': Pipeline([('scaler', StandardScaler()),
                         ('clf', XGBClassifier(n_estimators=200, random_state=42,
                                               use_label_encoder=False, eval_metric='mlogloss',
                                               verbosity=0))]),
    'LightGBM': Pipeline([('scaler', StandardScaler()),
                          ('clf', LGBMClassifier(n_estimators=200, random_state=42, verbose=-1))]),
    'ExtraTrees': Pipeline([('scaler', StandardScaler()),
                            ('clf', ExtraTreesClassifier(n_estimators=200, random_state=42, n_jobs=-1))]),
}

# ─── 실험 실행 ───
all_results = []

for target in label_cols:
    y_raw = labels[target].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    print(f"\n--- {target.upper()} (classes: {le.classes_}) ---")

    for name, model in models.items():
        acc_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
        f1_scores = cross_val_score(model, X, y, cv=cv, scoring=macro_f1)

        row = {
            'Component': target,
            'Model': name,
            'Accuracy': acc_scores.mean() * 100,
            'Acc_std': acc_scores.std() * 100,
            'Macro-F1': f1_scores.mean() * 100,
            'F1_std': f1_scores.std() * 100,
        }
        all_results.append(row)
        print(f"  {name:12s}: Acc={row['Accuracy']:.2f}% F1={row['Macro-F1']:.2f}%")

# ─── 결과 출력 ───
print("\n" + "=" * 70)
print("ML Baseline 종합 비교표")
print("=" * 70)

df_all = pd.DataFrame(all_results)

for target in label_cols:
    print(f"\n{'─'*60}")
    print(f"  {target.upper()}")
    print(f"{'─'*60}")
    subset = df_all[df_all['Component'] == target].copy()
    subset['Accuracy'] = subset.apply(lambda r: f"{r['Accuracy']:.2f} (±{r['Acc_std']:.2f})", axis=1)
    subset['Macro-F1'] = subset.apply(lambda r: f"{r['Macro-F1']:.2f} (±{r['F1_std']:.2f})", axis=1)
    print(subset[['Model', 'Accuracy', 'Macro-F1']].to_string(index=False))

# ─── 그래프: 모델별 Macro-F1 비교 ───
fig_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')
os.makedirs(fig_dir, exist_ok=True)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974']

for i, target in enumerate(label_cols):
    ax = axes[i // 2][i % 2]
    subset = df_all[df_all['Component'] == target]
    model_names = subset['Model'].values
    f1_vals = subset['Macro-F1'].values / 100  # original float values

    # 원래 float로 다시 계산
    f1_vals = []
    f1_stds = []
    for _, r in subset.iterrows():
        f1_vals.append(r['Macro-F1'] if isinstance(r['Macro-F1'], float) else float(str(r['Macro-F1']).split()[0]))
        f1_stds.append(r['F1_std'] if isinstance(r['F1_std'], float) else 0)

    bars = ax.bar(model_names, f1_vals, color=colors, yerr=f1_stds,
                  capsize=4, edgecolor='gray', linewidth=0.5)
    ax.set_title(target.upper(), fontweight='bold')
    ax.set_ylabel('Macro-F1 (%)')
    ax.set_ylim(min(f1_vals) - 3, 101)
    for bar, v in zip(bars, f1_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'{v:.1f}', ha='center', va='bottom', fontsize=8)

fig.suptitle('ML Baseline Comparison: 5-Fold CV Macro-F1', fontweight='bold', fontsize=14)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'ml_baseline_comparison.png'), dpi=150)
plt.close(fig)

print("\n" + "=" * 70)
print("결과 해석")
print("=" * 70)
print("""
1. 5개 모델(LDA, RF, XGBoost, LightGBM, ExtraTrees) 모두 매우 높은 성능을 보입니다.
2. 앙상블 모델(RF, XGBoost, LightGBM, ExtraTrees)이 LDA보다
   약간 높은 성능을 보이지만, 차이는 미미합니다.
3. 이는 187차원 시간도메인 특성이 이미 충분히 분리력이 좋다는 의미입니다.
4. Week 3에서는 원시 시계열을 직접 입력하는 딥러닝(MS-CNN, Multi-task)으로
   특성 추출 단계 없이 end-to-end 학습을 시도합니다.
5. 딥러닝의 가치는 '더 높은 정확도'보다 '수작업 특성 추출 불필요' +
   '원시 시계열에서 새로운 패턴 발견' 에 있습니다.

그래프: reports/figures/ml_baseline_comparison.png
""")
