import json
from sklearn.metrics import confusion_matrix, f1_score, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# === Carica i dati JSON ===
with open('data/tutto.json', 'r') as f:
    data = json.load(f)

# === Sequenza Fibonacci come float ===
fib_seq = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]

# === Filtra solo i dati validi ===
filtered_data = [
    item for item in data
    if float(item["true_points"]) in fib_seq and float(item["stimated_points"]) in fib_seq
]

# === Estrai versioni float e str ===
y_true_float = [float(item["true_points"]) for item in filtered_data]
y_pred_float = [float(item["stimated_points"]) for item in filtered_data]

# === Funzione per etichette leggibili ===
def clean_label(v):
    return str(int(v)) if v.is_integer() else str(v)

labels = [clean_label(v) for v in fib_seq]
y_true_str = [clean_label(v) for v in y_true_float]
y_pred_str = [clean_label(v) for v in y_pred_float]

# === Safety check ===
if not y_true_float:
    print("⚠️ Nessun dato valido dopo il filtro. Controlla i valori in temp.json.")
    exit()

# === Confusion Matrix classica ===
cm = confusion_matrix(y_true_str, y_pred_str, labels=labels)
plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels, cmap='Blues')
plt.xlabel('AI Points')
plt.ylabel('TEAM Points')
plt.title('Confusion Matrix')
plt.show()

# === F1-score standard ===
f1 = f1_score(y_true_str, y_pred_str, average='weighted', zero_division=0)
print(f"\n🎯 F1-score (weighted): {f1:.2f}\n")

# === Classification report ===
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

# === Confusion Matrix pesata (distanza Fibonacci) ===
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

# === Normalizzazione rispetto al massimo teorico ===
max_possible_distance = len(fib_seq) - 1
normalized_error = avg_fib_error / max_possible_distance if max_possible_distance > 0 else 0

print(f"📏 Errore pesato sulle distanze di fibonacci (errore medio osservato/ errore massimo osservabile): {normalized_error:.2f}")
