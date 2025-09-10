import json
import re
from collections import defaultdict
from typing import Optional

INPUT_FILE = "tutto.json"

FIBONACCI_SCALE = [0.5, 1, 2, 3, 5, 8, 13, 21]

def extract_project(issue_key: str) -> str:
    match = re.match(r"^[A-Z]+[0-9]*", issue_key)
    return match.group(0) if match else "UNKNOWN"

def fib_distance(true_val, est_val) -> int:
    try:
        return abs(FIBONACCI_SCALE.index(true_val) -
                   FIBONACCI_SCALE.index(est_val))
    except ValueError:
        return 99

def analyze_estimations(
        filepath: str,
        project_filter: Optional[list[str]] = None,   # 👈 adesso lista
        month : Optional[int] = None,
        year  : Optional[int] = None,
        week  : Optional[int] = None   
):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    total_true = total_estimated = 0.0
    correct_count = total_count = 0
    per_project = defaultdict(lambda: {"true_sum": 0.0, "stimated_sum": 0.0})
    mismatches  = []

    for e in data:
        true_sp, est_sp = e.get("true_points"), e.get("stimated_points")
        if true_sp is None or est_sp is None:
            continue

        proj  = extract_project(e.get("issue_key", ""))

        emon  = e.get("month")
        eyear = e.get("year")
        ewom  = e.get("week_of_month")
        if ewom is None:
            day  = e.get("day", 1)            
            ewom = (day - 1) // 7 + 1        

        # --- FILTRI -----------------------------------------------------
        if project_filter and proj not in project_filter:   # 👈 qui il check sulla lista
            continue
        if month and emon != month:
            continue
        if year and eyear != year:
            continue
        if week and ewom != week:
            continue
        # ---------------------------------------------------------------

        total_true      += true_sp
        total_estimated += est_sp
        total_count     += 1
        if fib_distance(true_sp, est_sp) <= 1:
            correct_count += 1

        per_project[proj]["true_sum"]     += true_sp
        per_project[proj]["stimated_sum"] += est_sp

        if fib_distance(true_sp, est_sp) > 1:
            mismatches.append({
                "issue_key"   : e.get("issue_key"),
                "true"        : true_sp,
                "estimated"   : est_sp,
                "fib_distance": fib_distance(true_sp, est_sp)
            })

    accuracy = 100 * correct_count / total_count if total_count else 0

    # --- OUTPUT ----------------------------------------------------------
    print("\n📊 STATISTICHE GLOBALI")
    print(f"✔️  Totale story point da team: {total_true}")
    print(f"📐 Totale story point da AI:   {total_estimated}")
    print(f"🎯 Stime corrette (Δ≤1):        {correct_count} su {total_count}")
    print(f"✅ Percentuale corrette:       {accuracy:.2f}%")

    print("\n📂 STATISTICHE PER PROGETTO")
    for proj, vals in per_project.items():
        print(f" • {proj}: team={vals['true_sum']}  |  AI={vals['stimated_sum']}")

    if mismatches:
        print("\n❗ TASK CON STIMA FUORI SCALA (>1 passo Fibonacci)")
        for m in mismatches:
            print(f"   - {m['issue_key']}: team {m['true']}  vs  AI {m['estimated']}  (Δ={m['fib_distance']})")
    else:
        print("\n✅ Nessuna stima gravemente sbagliata (fib distance > 1)")
if __name__ == "__main__":

    # Solo gennaio 2023, settimana 1
    analyze_estimations(INPUT_FILE, month=None, project_filter=["APCUP", "APCPS", "APMI"], year=2025, week=None)
