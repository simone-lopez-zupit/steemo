import json
from sklearn.metrics import confusion_matrix, f1_score, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

with open('data/fake_tutto.json', 'r') as f:
    data = json.load(f)

fib_seq = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]

filtered_data = [
    item for item in data
    if float(item["true_points"]) in fib_seq and float(item["stimated_points"]) in fib_seq
]

y_true_float = [float(item["true_points"]) for item in filtered_data]
y_pred_float = [float(item["stimated_points"]) for item in filtered_data]

def clean_label(v):
    return str(int(v)) if v.is_integer() else str(v)

labels = [clean_label(v) for v in fib_seq]
y_true_str = [clean_label(v) for v in y_true_float]
y_pred_str = [clean_label(v) for v in y_pred_float]


cm = confusion_matrix(y_true_str, y_pred_str, labels=labels)
plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels, cmap='Blues')
plt.xlabel('AI Points')
plt.ylabel('TEAM Points')
plt.title('Confusion Matrix')
plt.show()

f1 = f1_score(y_true_str, y_pred_str, average='weighted', zero_division=0)
print(f"\n🎯 F1-score (weighted): {f1:.2f}\n")

print("📊 Classification Report:")
print(classification_report(y_true_str, y_pred_str, labels=labels, zero_division=0))

# === Fibonacci-aware soft accuracy ===
def fib_distance(a, b):
    try:
        return abs(fib_seq.index(a) - fib_seq.index(b))
    except ValueError:
        return None

soft_matches = sum(
    1 for t, p in zip(y_true_float, y_pred_float)
    if fib_distance(t, p) is not None and fib_distance(t, p) <= 1
)
soft_accuracy = soft_matches / len(y_true_float)
print(f"\n🟡 Soft Accuracy (entro 1 passo Fibonacci): {soft_accuracy:.2f}")

weighted_cm = np.zeros_like(cm, dtype=float)

for i, true_label in enumerate(labels):
    for j, pred_label in enumerate(labels):
        t_val = float(true_label)
        p_val = float(pred_label)
        dist = fib_distance(t_val, p_val)
        count = cm[i][j]
        if dist is not None:
            weighted_cm[i][j] = count * dist

plt.figure(figsize=(10, 8))
sns.heatmap(weighted_cm, annot=True, fmt='.1f', xticklabels=labels, yticklabels=labels, cmap='Reds')
plt.xlabel('AI Points')
plt.ylabel('TEAM Points')
plt.title('Confusion Matrix (Pesata per Distanza Fibonacci)')
plt.show()


# === Errore medio pesato (Fibonacci distance) ===
total_penalty = weighted_cm.sum()
n_samples = len(y_true_float)
avg_fib_error = total_penalty / n_samples if n_samples > 0 else 0

max_possible_distance = len(fib_seq) - 1
normalized_error = avg_fib_error / max_possible_distance if max_possible_distance > 0 else 0

print(f"📏 Errore pesato sulle distanze di fibonacci (errore medio osservato/ errore massimo osservabile): {normalized_error:.2f}")
# === Absolute Fibonacci Error (AFE) ===
afe = np.sum(np.abs(np.array(y_true_float) - np.array(y_pred_float))) / np.sum(y_true_float)

# === Quadratic Fibonacci Error (QFE) ===
qfe = np.sum((np.array(y_true_float) - np.array(y_pred_float)) ** 2) / np.sum(np.array(y_true_float) ** 2)

print(f"\n🔴 Absolute Fibonacci Error (AFE): {afe:.2f}")
print(f"🔴 Quadratic Fibonacci Error (QFE): {qfe:.2f}")