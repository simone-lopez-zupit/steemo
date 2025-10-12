import os
import json
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import Optional

FIBONACCI_SCALE = [0, 0.5, 1, 2, 3, 5, 8, 13, 21]
INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "tutto.json")

def fib_distance(true_val, est_val) -> int:
    try:
        idx_true = FIBONACCI_SCALE.index(true_val)
        idx_est = FIBONACCI_SCALE.index(est_val)
        return abs(idx_true - idx_est)
    except ValueError:
        return 99

def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def filter_data(data, project: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None):
    return [
        e for e in data
        if (project is None or e["issue_key"].startswith(project + "-")) and
           (year is None or e["year"] == year) and
           (month is None or e["month"] == month)
    ]

def plot_data(data):
    weekly_totals = defaultdict(lambda: {"true": 0, "ai": 0})
    weekly_fib_deltas = defaultdict(int)

    for entry in data:
        key = (entry["year"], entry["month"], entry["week_of_month"])
        true = entry.get("true_points")
        ai = entry.get("stimated_points")
        if true is None or ai is None:
            continue

        weekly_totals[key]["true"] += true
        weekly_totals[key]["ai"] += ai
        weekly_fib_deltas[key] += fib_distance(true, ai)

    sorted_keys = sorted(weekly_totals.keys())
    labels = [f"W{w} {m:02d}/{y}" for y, m, w in sorted_keys]
    true_values = [weekly_totals[k]["true"] for k in sorted_keys]
    ai_values = [weekly_totals[k]["ai"] for k in sorted_keys]
    fib_deltas = [weekly_fib_deltas[k] for k in sorted_keys]

    accuracy = [round((ai / true) * 100, 1) if true > 0 else 0 for ai, true in zip(ai_values, true_values)]
    delta_values = [ai - true for ai, true in zip(ai_values, true_values)]

    plt.figure(figsize=(16, 10))

    plt.subplot(3, 1, 1)
    plt.plot(labels, true_values, marker='o', label="Team", linewidth=2)
    plt.plot(labels, ai_values, marker='s', label="AI", linewidth=2)
    plt.fill_between(labels, true_values, ai_values, color="gray", alpha=0.2, label="Differenza")
    plt.title("Story Points per settimana (Team vs AI)", fontsize=14)
    plt.ylabel("Totale Story Points", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)

    plt.subplot(3, 1, 2)
    bars2 = plt.bar(labels, fib_deltas, color="orange")
    for bar, val in zip(bars2, fib_deltas):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(val),
                 ha='center', va='bottom', fontsize=9)
    
    plt.ylabel("Δ scala Fibonacci", fontsize=12)
    plt.xlabel("Settimana", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)

    plt.subplot(3, 1, 3)
    bars3 = plt.bar(labels, accuracy, color="blue")
    for bar, val in zip(bars3, accuracy):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{val}%",
                 ha='center', va='bottom', fontsize=9)
    plt.axhline(y=100, color="green", linestyle="--", label="Perfetta (100%)")
    plt.ylabel("% Accuratezza AI", fontsize=12)
    plt.xlabel("Settimana", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    data = load_data(INPUT_FILE)

    
    project = None      # es. "NPMP" oppure None per tutti i progetti
    year = 2022         # oppure None per tutti gli anni
    month =None         # oppure None per tutti i mesi

    filtered = filter_data(data, project=project, year=year, month=month)
    plot_data(filtered)
