import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import confusion_matrix, f1_score, accuracy_score
from src.data_loader import load_all_sensors, load_labels, get_data_dir
from src.features import extract_all_features

data_dir = get_data_dir()
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)
feature_df = extract_all_features(sensors, labels)
feature_cols = [c for c in feature_df.columns if c not in labels.columns]
X = feature_df[feature_cols].values
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
pipeline = Pipeline([('scaler', StandardScaler()), ('lda', LinearDiscriminantAnalysis())])

# 1) Accumulator confusion matrix
print("=== Accumulator LDA Confusion Matrix ===")
y = labels['accumulator'].values
y_pred = cross_val_predict(pipeline, X, y, cv=cv)
cm = confusion_matrix(y, y_pred)
classes = sorted(np.unique(y))
print(f"Classes: {classes}")
print(cm)
print("\nOff-diagonal errors:")
for i, c1 in enumerate(classes):
    for j, c2 in enumerate(classes):
        if i != j and cm[i,j] > 0:
            print(f"  True {c1} -> Pred {c2}: {cm[i,j]} samples")

# 2) Imbalance experiment actual values (to check graph vs table)
print("\n=== Imbalance Experiment: Valve ===")
from sklearn.ensemble import RandomForestClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

y_valve = labels['valve'].values
experiments = {
    'E1 Baseline': ImbPipeline([('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))]),
    'E2 class_weight': ImbPipeline([('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))]),
}
for name, pipe in experiments.items():
    yp = cross_val_predict(pipe, X, y_valve, cv=cv)
    f1 = f1_score(y_valve, yp, average='macro') * 100
    acc = accuracy_score(y_valve, yp) * 100
    print(f"  {name}: Acc={acc:.2f}%, Macro-F1={f1:.2f}%")
