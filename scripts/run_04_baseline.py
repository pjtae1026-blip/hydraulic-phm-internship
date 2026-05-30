"""04_pytorch_baseline — 로컬 실행 스크립트 (CPU)"""

import sys, os
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

# ─── Config ───
device = torch.device("cpu")
SEED = 42
TARGET_LEN = 60
TARGETS = ["cooler", "valve", "pump", "accumulator"]
N_EPOCHS = 50
LR = 1e-3
BATCH_SIZE = 64

np.random.seed(SEED)
torch.manual_seed(SEED)

print(f"PyTorch {torch.__version__} | Device: {device}")

# ─── 1. Data Loading ───
print("\n[1/6] Loading data...")
from src.data_loader import load_all_sensors, load_labels, SENSOR_SPECS

data_dir = Path("data/uci")
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)

print(f"Cycles: {labels.shape[0]}")
for col in TARGETS:
    print(f"  {col}: {dict(labels[col].value_counts().sort_index())}")

# ─── 2. Build Tensor ───
print("\n[2/6] Building input tensor...")

def build_tensor(sensors, target_len=TARGET_LEN):
    arrays = []
    for name in SENSOR_SPECS:
        X = sensors[name]
        n_cycles, n_cols = X.shape
        if n_cols > target_len:
            idx = np.linspace(0, n_cols - 1, target_len, dtype=int)
            X = X[:, idx]
        mu, std = X.mean(), X.std()
        if std > 0:
            X = (X - mu) / std
        arrays.append(X)
    return np.stack(arrays, axis=1)

X_all = build_tensor(sensors)
print(f"Input tensor: {X_all.shape}  ({X_all.nbytes / 1e6:.1f} MB)")

# ─── 3. Dataset ───
class HydraulicDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)
    def __len__(self):
        return len(self.y)
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def prepare_data(X_all, labels, target_col):
    le = LabelEncoder()
    y = le.fit_transform(labels[target_col].values)
    n_classes = len(le.classes_)
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y, test_size=0.2, random_state=SEED, stratify=y
    )
    train_loader = DataLoader(HydraulicDataset(X_train, y_train), batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(HydraulicDataset(X_test, y_test), batch_size=BATCH_SIZE, shuffle=False)
    return train_loader, test_loader, le, n_classes

# ─── 4. Model ───
class CNN1D(nn.Module):
    def __init__(self, n_channels=17, n_classes=3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(n_channels, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(2), nn.Dropout(0.2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(2), nn.Dropout(0.2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128), nn.ReLU(),
        )
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.classifier = nn.Sequential(
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3), nn.Linear(64, n_classes),
        )
    def forward(self, x):
        x = self.features(x)
        x = self.gap(x).squeeze(-1)
        return self.classifier(x)

# ─── 5. Train / Eval ───
def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss, correct, total = 0, 0, 0
    for X_batch, y_batch in loader:
        optimizer.zero_grad()
        logits = model(X_batch)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(y_batch)
        correct += (logits.argmax(1) == y_batch).sum().item()
        total += len(y_batch)
    return total_loss / total, correct / total

@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0, 0, 0
    all_preds, all_labels = [], []
    for X_batch, y_batch in loader:
        logits = model(X_batch)
        loss = criterion(logits, y_batch)
        total_loss += loss.item() * len(y_batch)
        preds = logits.argmax(1)
        correct += (preds == y_batch).sum().item()
        total += len(y_batch)
        all_preds.extend(preds.numpy())
        all_labels.extend(y_batch.numpy())
    return total_loss / total, correct / total, np.array(all_preds), np.array(all_labels)

# ─── 6. Train all targets ───
print("\n[3/6] Training 1D-CNN for each target...")
results = {}

for target in TARGETS:
    print(f"\n{'='*60}")
    print(f"  Target: {target}")
    print(f"{'='*60}")

    train_loader, test_loader, le, n_classes = prepare_data(X_all, labels, target)
    model = CNN1D(n_channels=17, n_classes=n_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=N_EPOCHS)

    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_val_acc = 0
    best_state = None

    for epoch in range(N_EPOCHS):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc, _, _ = evaluate(model, test_loader, criterion)
        scheduler.step()

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d}/{N_EPOCHS} | "
                  f"Train: {train_loss:.4f} / {train_acc:.4f} | "
                  f"Val: {val_loss:.4f} / {val_acc:.4f}")

    # Best model evaluation
    model.load_state_dict(best_state)
    _, final_acc, preds, true_labels = evaluate(model, test_loader, criterion)

    print(f"\n  Best Val Accuracy: {best_val_acc:.4f}")
    target_names = [str(c) for c in le.classes_]
    print(classification_report(true_labels, preds, target_names=target_names))

    results[target] = {
        "history": history,
        "label_encoder": le,
        "preds": preds,
        "true_labels": true_labels,
        "best_val_acc": best_val_acc,
    }

# ─── 7. Summary ───
print("\n[4/6] Results Summary")
print("=" * 50)
for t in TARGETS:
    r = results[t]
    acc = accuracy_score(r["true_labels"], r["preds"])
    print(f"  {t:15s} | Classes: {len(r['label_encoder'].classes_)} | Test Acc: {acc:.4f}")
print("=" * 50)

# ─── 8. Plots ───
print("\n[5/6] Generating training curves...")
fig, axes = plt.subplots(2, 4, figsize=(20, 8))
for i, target in enumerate(TARGETS):
    h = results[target]["history"]
    epochs = range(1, len(h["train_loss"]) + 1)
    axes[0, i].plot(epochs, h["train_loss"], label="Train")
    axes[0, i].plot(epochs, h["val_loss"], label="Val")
    axes[0, i].set_title(f"{target} — Loss")
    axes[0, i].set_xlabel("Epoch"); axes[0, i].legend(); axes[0, i].grid(True, alpha=0.3)
    axes[1, i].plot(epochs, h["train_acc"], label="Train")
    axes[1, i].plot(epochs, h["val_acc"], label="Val")
    axes[1, i].set_title(f"{target} — Accuracy")
    axes[1, i].set_xlabel("Epoch"); axes[1, i].set_ylim(0, 1.05)
    axes[1, i].legend(); axes[1, i].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("reports/04_training_curves.png", dpi=150, bbox_inches="tight")
print("  Saved: reports/04_training_curves.png")

print("\n[6/6] Generating confusion matrices...")
fig, axes = plt.subplots(1, 4, figsize=(22, 5))
for i, target in enumerate(TARGETS):
    r = results[target]
    cm = confusion_matrix(r["true_labels"], r["preds"])
    class_names = [str(c) for c in r["label_encoder"].classes_]
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=class_names, yticklabels=class_names, ax=axes[i])
    axes[i].set_title(f"{target}")
    axes[i].set_xlabel("Predicted"); axes[i].set_ylabel("True")
plt.suptitle("Confusion Matrices — 1D-CNN Baseline", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig("reports/04_confusion_matrices.png", dpi=150, bbox_inches="tight")
print("  Saved: reports/04_confusion_matrices.png")

# Save results for 05 comparison
import json
acc_results = {t: float(accuracy_score(results[t]["true_labels"], results[t]["preds"])) for t in TARGETS}
with open("reports/04_results.json", "w") as f:
    json.dump(acc_results, f, indent=2)
print(f"\n  Saved: reports/04_results.json → {acc_results}")

print("\n[DONE] 04_pytorch_baseline completed!")
