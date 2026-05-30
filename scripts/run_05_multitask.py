"""05_multitask — 로컬 실행 스크립트 (CPU)
Multi-task 1D-CNN with uncertainty-based loss weighting (Kendall et al., 2018)
"""

import sys, os, json
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
N_EPOCHS = 80
LR = 1e-3
BATCH_SIZE = 64

np.random.seed(SEED)
torch.manual_seed(SEED)

print(f"PyTorch {torch.__version__} | Device: {device}")

# ─── 1. Data ───
print("\n[1/7] Loading data...")
from src.data_loader import load_all_sensors, load_labels, SENSOR_SPECS

data_dir = Path("data/uci")
sensors = load_all_sensors(data_dir)
labels = load_labels(data_dir)

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
print(f"Input tensor: {X_all.shape}")

# ─── 2. Encode all targets ───
print("\n[2/7] Encoding labels...")
label_encoders = {}
n_classes_dict = {}
y_encoded = {}

for t in TARGETS:
    le = LabelEncoder()
    y_encoded[t] = le.fit_transform(labels[t].values)
    label_encoders[t] = le
    n_classes_dict[t] = len(le.classes_)
    print(f"  {t}: {n_classes_dict[t]} classes -> {list(le.classes_)}")

# Split indices (same for all targets)
indices = np.arange(len(X_all))
train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=SEED)
print(f"\nTrain: {len(train_idx)} | Test: {len(test_idx)}")

# ─── 3. Dataset ───
class MultiTaskDataset(Dataset):
    def __init__(self, X, y_dict, indices):
        self.X = torch.FloatTensor(X[indices])
        self.labels = {t: torch.LongTensor(y_dict[t][indices]) for t in y_dict}
    def __len__(self):
        return len(self.X)
    def __getitem__(self, idx):
        return self.X[idx], {t: self.labels[t][idx] for t in self.labels}

train_loader = DataLoader(MultiTaskDataset(X_all, y_encoded, train_idx),
                          batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(MultiTaskDataset(X_all, y_encoded, test_idx),
                         batch_size=BATCH_SIZE, shuffle=False)

# ─── 4. Model ───
class MultiTaskCNN(nn.Module):
    def __init__(self, n_channels=17, n_classes_dict=None):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv1d(n_channels, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(2), nn.Dropout(0.2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(2), nn.Dropout(0.2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128), nn.ReLU(),
        )
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.heads = nn.ModuleDict()
        for name, nc in n_classes_dict.items():
            self.heads[name] = nn.Sequential(
                nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3), nn.Linear(64, nc),
            )
    def forward(self, x):
        feat = self.backbone(x)
        feat = self.gap(feat).squeeze(-1)
        return {name: head(feat) for name, head in self.heads.items()}

# ─── 5. Multi-Task Loss ───
class MultiTaskLoss(nn.Module):
    def __init__(self, task_names):
        super().__init__()
        self.task_names = task_names
        self.criteria = {t: nn.CrossEntropyLoss() for t in task_names}
        self.log_vars = nn.ParameterDict({
            t: nn.Parameter(torch.zeros(1)) for t in task_names
        })
    def forward(self, outputs, targets):
        total_loss = 0
        losses = {}
        for t in self.task_names:
            ce = self.criteria[t](outputs[t], targets[t])
            precision = torch.exp(-self.log_vars[t])
            task_loss = precision * ce + self.log_vars[t]
            total_loss = total_loss + task_loss
            losses[t] = ce.item()
        return total_loss.squeeze(), losses

# ─── 6. Train / Eval ───
def train_one_epoch(model, loader, mt_loss, optimizer):
    model.train()
    total_loss = 0
    task_correct = {t: 0 for t in TARGETS}
    total = 0
    for X_batch, y_batch in loader:
        optimizer.zero_grad()
        outputs = model(X_batch)
        loss, _ = mt_loss(outputs, y_batch)
        loss.backward()
        optimizer.step()
        bs = X_batch.size(0)
        total_loss += loss.item() * bs
        total += bs
        for t in TARGETS:
            task_correct[t] += (outputs[t].argmax(1) == y_batch[t]).sum().item()
    return total_loss / total, {t: task_correct[t] / total for t in TARGETS}

@torch.no_grad()
def evaluate(model, loader, mt_loss):
    model.eval()
    total_loss = 0
    task_correct = {t: 0 for t in TARGETS}
    all_preds = {t: [] for t in TARGETS}
    all_labels = {t: [] for t in TARGETS}
    total = 0
    for X_batch, y_batch in loader:
        outputs = model(X_batch)
        loss, _ = mt_loss(outputs, y_batch)
        bs = X_batch.size(0)
        total_loss += loss.item() * bs
        total += bs
        for t in TARGETS:
            preds = outputs[t].argmax(1)
            task_correct[t] += (preds == y_batch[t]).sum().item()
            all_preds[t].extend(preds.numpy())
            all_labels[t].extend(y_batch[t].numpy())
    return (
        total_loss / total,
        {t: task_correct[t] / total for t in TARGETS},
        {t: np.array(all_preds[t]) for t in TARGETS},
        {t: np.array(all_labels[t]) for t in TARGETS},
    )

# ─── 7. Train ───
print("\n[3/7] Building Multi-Task model...")
model = MultiTaskCNN(n_channels=17, n_classes_dict=n_classes_dict)
mt_loss = MultiTaskLoss(TARGETS)

total_params = sum(p.numel() for p in model.parameters())
backbone_params = sum(p.numel() for p in model.backbone.parameters())
head_params = sum(p.numel() for p in model.heads.parameters())
print(f"  Total params: {total_params:,}")
print(f"  Backbone: {backbone_params:,} | Heads: {head_params:,}")

optimizer = optim.Adam(
    list(model.parameters()) + list(mt_loss.parameters()),
    lr=LR, weight_decay=1e-4
)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=N_EPOCHS)

print(f"\n[4/7] Training Multi-Task ({N_EPOCHS} epochs)...")
history = {
    "train_loss": [], "val_loss": [],
    **{f"train_acc_{t}": [] for t in TARGETS},
    **{f"val_acc_{t}": [] for t in TARGETS},
    "task_weights": [],
}
best_avg_acc = 0
best_state = None

for epoch in range(N_EPOCHS):
    train_loss, train_accs = train_one_epoch(model, train_loader, mt_loss, optimizer)
    val_loss, val_accs, _, _ = evaluate(model, test_loader, mt_loss)
    scheduler.step()

    history["train_loss"].append(train_loss)
    history["val_loss"].append(val_loss)
    for t in TARGETS:
        history[f"train_acc_{t}"].append(train_accs[t])
        history[f"val_acc_{t}"].append(val_accs[t])
    weights = {t: torch.exp(-mt_loss.log_vars[t]).item() for t in TARGETS}
    history["task_weights"].append(weights)

    avg_val_acc = np.mean([val_accs[t] for t in TARGETS])
    if avg_val_acc > best_avg_acc:
        best_avg_acc = avg_val_acc
        best_state = {k: v.clone() for k, v in model.state_dict().items()}

    if (epoch + 1) % 10 == 0:
        acc_str = " | ".join(f"{t}: {val_accs[t]:.3f}" for t in TARGETS)
        w_str = " | ".join(f"{t}: {weights[t]:.2f}" for t in TARGETS)
        print(f"  Epoch {epoch+1:3d}/{N_EPOCHS} | Avg val: {avg_val_acc:.4f}")
        print(f"    Acc:     [{acc_str}]")
        print(f"    Weights: [{w_str}]")

print(f"\n  Best avg val accuracy: {best_avg_acc:.4f}")

# ─── 8. Final Eval ───
print("\n[5/7] Final evaluation with best model...")
model.load_state_dict(best_state)
_, final_accs, final_preds, final_labels = evaluate(model, test_loader, mt_loss)

for t in TARGETS:
    print(f"\n{'='*50}")
    print(f"  {t.upper()} | Test Acc: {final_accs[t]:.4f}")
    print(f"{'='*50}")
    target_names = [str(c) for c in label_encoders[t].classes_]
    print(classification_report(final_labels[t], final_preds[t], target_names=target_names))

# ─── 9. Plots ───
print("\n[6/7] Generating plots...")

# 9.1 Per-task accuracy curves
fig, axes = plt.subplots(1, 4, figsize=(20, 4))
epochs = range(1, N_EPOCHS + 1)
for i, t in enumerate(TARGETS):
    axes[i].plot(epochs, history[f"train_acc_{t}"], label="Train", alpha=0.8)
    axes[i].plot(epochs, history[f"val_acc_{t}"], label="Val", alpha=0.8)
    axes[i].set_title(f"{t}")
    axes[i].set_xlabel("Epoch"); axes[i].set_ylabel("Accuracy")
    axes[i].set_ylim(0, 1.05); axes[i].legend(); axes[i].grid(True, alpha=0.3)
plt.suptitle("Multi-Task 1D-CNN - Per-Task Accuracy", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig("reports/05_multitask_accuracy.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: reports/05_multitask_accuracy.png")

# 9.2 Task weights evolution
fig, ax = plt.subplots(figsize=(10, 4))
for t in TARGETS:
    ws = [history["task_weights"][e][t] for e in range(N_EPOCHS)]
    ax.plot(epochs, ws, label=t, linewidth=2)
ax.set_xlabel("Epoch")
ax.set_ylabel("Task Weight (precision = 1/sigma^2)")
ax.set_title("Learned Task Weights over Training")
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("reports/05_task_weights.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: reports/05_task_weights.png")

# 9.3 Confusion matrices
fig, axes = plt.subplots(1, 4, figsize=(22, 5))
for i, t in enumerate(TARGETS):
    cm = confusion_matrix(final_labels[t], final_preds[t])
    class_names = [str(c) for c in label_encoders[t].classes_]
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=class_names, yticklabels=class_names, ax=axes[i])
    axes[i].set_title(f"{t} (acc: {final_accs[t]:.3f})")
    axes[i].set_xlabel("Predicted"); axes[i].set_ylabel("True")
plt.suptitle("Confusion Matrices - Multi-Task 1D-CNN", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig("reports/05_multitask_confusion.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: reports/05_multitask_confusion.png")

# ─── 10. Comparison with Single-Task (04) ───
print("\n[7/7] Comparison with 04_baseline...")
with open("reports/04_results.json") as f:
    single_task_acc = json.load(f)

multi_task_acc = {t: float(final_accs[t]) for t in TARGETS}

print("\n" + "=" * 65)
print(f"  {'Target':15s} | {'Single-Task':12s} | {'Multi-Task':12s} | {'Diff':10s}")
print("=" * 65)
for t in TARGETS:
    st = single_task_acc[t]
    mt = multi_task_acc[t]
    diff = mt - st
    print(f"  {t:15s} | {st:.4f}       | {mt:.4f}       | {diff:+.4f}")
print("=" * 65)
print(f"  {'Average':15s} | {np.mean(list(single_task_acc.values())):.4f}       | "
      f"{np.mean(list(multi_task_acc.values())):.4f}       | "
      f"{np.mean(list(multi_task_acc.values())) - np.mean(list(single_task_acc.values())):+.4f}")
print("=" * 65)

# Bar chart comparison
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(TARGETS))
w = 0.35
ax.bar(x - w/2, [single_task_acc[t] for t in TARGETS], w, label="Single-Task (04)", color="steelblue")
ax.bar(x + w/2, [multi_task_acc[t] for t in TARGETS], w, label="Multi-Task (05)", color="coral")
for i, t in enumerate(TARGETS):
    ax.text(i - w/2, single_task_acc[t] + 0.01, f"{single_task_acc[t]:.3f}",
            ha="center", fontsize=9)
    ax.text(i + w/2, multi_task_acc[t] + 0.01, f"{multi_task_acc[t]:.3f}",
            ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(TARGETS)
ax.set_ylabel("Test Accuracy"); ax.set_ylim(0, 1.10)
ax.set_title("Single-Task vs Multi-Task 1D-CNN")
ax.legend(); ax.grid(True, alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig("reports/05_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n  Saved: reports/05_comparison.png")

# Save results
with open("reports/05_results.json", "w") as f:
    json.dump({
        "multi_task": multi_task_acc,
        "single_task": single_task_acc,
        "improvement": {t: multi_task_acc[t] - single_task_acc[t] for t in TARGETS},
    }, f, indent=2)
print("  Saved: reports/05_results.json")

print("\n[DONE] 05_multitask completed!")
