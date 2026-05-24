import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, recall_score
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
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

experiments = {
    'E1': ImbPipeline([('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))]),
    'E2': ImbPipeline([('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))]),
    'E3': ImbPipeline([('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42)),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))]),
    'E4': ImbPipeline([('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42)),
        ('clf', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42))]),
}

for target in ['valve', 'pump', 'accumulator']:
    y = labels[target].values
    classes = sorted(np.unique(y))
    print(f"\n=== {target.upper()} (classes: {classes}) ===")
    for name, pipe in experiments.items():
        yp = cross_val_predict(pipe, X, y, cv=cv)
        acc = accuracy_score(y, yp) * 100
        f1 = f1_score(y, yp, average='macro') * 100
        recalls = recall_score(y, yp, average=None, labels=classes)
        min_r = min(recalls) * 100
        print(f"  {name}: Acc={acc:.2f}%, F1={f1:.2f}%, MinR={min_r:.2f}%")
