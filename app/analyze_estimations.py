import json
import re
from collections import defaultdict
from typing import Optional

from app.repository import fetch_all_stories

INPUT_FILE: Optional[str] = None

FIBONACCI_SCALE = [0.5, 1, 2, 3, 5, 8, 13, 21]


def extract_project(issue_key: str) -> str:
    match = re.match(r"^[A-Z]+[0-9]*", issue_key)
    return match.group(0) if match else "UNKNOWN"


def fib_distance(true_val, est_val) -> int:
    try:
        return abs(
            FIBONACCI_SCALE.index(true_val) - FIBONACCI_SCALE.index(est_val)
        )
    except ValueError:
        return 99


def _load_story_records(filepath: Optional[str] = None) -> list[dict]:
    """
    Carica i record dal DB (predefinito) oppure da un file JSON opzionale.
    """
    if filepath:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    return fetch_all_stories()


def analyze_estimations(
    filepath: Optional[str] = None,
    project_filter: Optional[list[str]] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    week: Optional[int] = None,
) -> None:
    data = _load_story_records(filepath)

    total_true = 0.0
    total_estimated = 0.0
    correct_count = 0
    total_count = 0
    per_project = defaultdict(lambda: {"true_sum": 0.0, "stimated_sum": 0.0})
    mismatches = []

    for entry in data:
        true_sp = entry.get("true_points")
        est_sp = entry.get("stimated_points")
        if true_sp is None or est_sp is None:
            continue

        project = extract_project(entry.get("issue_key", ""))

        entry_month = entry.get("month")
        entry_year = entry.get("year")
        entry_week = entry.get("week_of_month")
        if entry_week is None:
            day = entry.get("day", 1)
            entry_week = (day - 1) // 7 + 1

        if project_filter and project not in project_filter:
            continue
        if month and entry_month != month:
            continue
        if year and entry_year != year:
            continue
        if week and entry_week != week:
            continue

        total_true += true_sp
        total_estimated += est_sp
        total_count += 1
        if fib_distance(true_sp, est_sp) <= 1:
            correct_count += 1

        per_project[project]["true_sum"] += true_sp
        per_project[project]["stimated_sum"] += est_sp

        if fib_distance(true_sp, est_sp) > 1:
            mismatches.append(
                {
                    "issue_key": entry.get("issue_key"),
                    "true": true_sp,
                    "estimated": est_sp,
                    "fib_distance": fib_distance(true_sp, est_sp),
                }
            )

    accuracy = 100 * correct_count / total_count if total_count else 0

    print("\n== STATISTICHE GLOBALI ==")
    print(f"- Totale story point team: {total_true}")
    print(f"- Totale story point AI:   {total_estimated}")
    print(f"- Stime corrette (<=1 passo): {correct_count} su {total_count}")
    print(f"- Percentuale corrette: {accuracy:.2f}%")

    print("\n== STATISTICHE PER PROGETTO ==")
    for project, values in per_project.items():
        print(
            f"- {project}: team={values['true_sum']} | AI={values['stimated_sum']}"
        )

    if mismatches:
        print("\n== STORIE CON STIMA FUORI SCALA (>1 passo Fibonacci) ==")
        for mismatch in mismatches:
            print(
                f"- {mismatch['issue_key']}: team {mismatch['true']} vs AI {mismatch['estimated']} "
                f"(distanza={mismatch['fib_distance']})"
            )
    else:
        print("\nNessuna stima con distanza Fibonacci > 1")


if __name__ == "__main__":
    analyze_estimations(
        filepath=INPUT_FILE,
        project_filter=["APCUP", "APCPS", "APMI"],
        month=None,
        year=2025,
        week=None,
    )
