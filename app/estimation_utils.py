import os
import re
from collections import defaultdict
from asyncio import gather

import openai
openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))


FIBONACCI_STEPS = [0.5, 1, 2, 3, 5, 8, 13, 21]

def fib_distance(true_val, est_val) -> int:
    try:
        idx_true = FIBONACCI_STEPS.index(true_val)
        idx_est = FIBONACCI_STEPS.index(est_val)
        return abs(idx_true - idx_est)
    except ValueError:
        return 99


def extract_project(issue_key: str) -> str:
    match = re.match(r"^[A-Z]+[0-9]*", issue_key)
    return match.group(0) if match else "UNKNOWN"

def analyze_results(results):
    total_true = 0.0
    total_estimated = 0.0
    correct_count = 0
    total_count = 0

    per_project = defaultdict(lambda: {"true_sum": 0.0, "stimated_sum": 0.0})
    mismatches = []

    for entry in results:
        true_sp = entry.get("true_points")
        estimated_sp = entry.get("stimated_points")
        issue_key = entry.get("issue_key")

        if true_sp is None or estimated_sp is None:
            continue

        total_true += true_sp
        total_estimated += estimated_sp
        total_count += 1

        if fib_distance( true_sp,estimated_sp)<=1:
            correct_count += 1

        project = extract_project(issue_key)
        per_project[project]["true_sum"] += true_sp
        per_project[project]["stimated_sum"] += estimated_sp

        if fib_distance(true_sp, estimated_sp) > 1:
            mismatches.append({
                "issue_key": issue_key,
                "true": true_sp,
                "estimated": estimated_sp,
                "fib_distance": fib_distance(true_sp, estimated_sp)
            })

    accuracy = (correct_count / total_count * 100) if total_count else 0

    # OUTPUT
    print("\n📊 STATISTICHE GLOBALI")
    print(f"✔️ Totale story point da team:                           {total_true}")
    print(f"📐 Totale story point da AI:                            {total_estimated}")
    print(f"🎯 Stime corrette/o una distanza massima:               {correct_count} su {total_count}")
    print(f"✅ Percentuale corrette/o una distanza massima:         {accuracy:.2f}%")

    print("\n📂 STATISTICHE PER PROGETTO")
    for project, values in per_project.items():
        print(f"📁 {project}:")
        print(f"    - Somma da team:  {values['true_sum']}")
        print(f"    - Somma da AI:    {values['stimated_sum']}")

    if mismatches:
        print("\n❗ TASK CON STIMA FUORI SCALA (>1 passo Fibonacci)")
        for m in mismatches:
            print(f"🔻 {m['issue_key']} — Team: {m['true']}, AI: {m['estimated']} (Δ fib={m['fib_distance']})")
    else:
        print("\n✅ Nessuna stima gravemente sbagliata (fib distance > 1).")

