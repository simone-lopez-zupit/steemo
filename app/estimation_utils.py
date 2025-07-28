from datetime import datetime
import os
import re
from collections import defaultdict
from asyncio import gather

import openai
openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))


FIBONACCI_STEPS = [0, 0.5, 1, 2, 3, 5, 8, 13, 21,34]

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

def get_week_of_month(date_str: str) -> int:
    date = datetime.strptime(date_str[:10], "%Y-%m-%d")
    first_day = date.replace(day=1)
    return (date.day + first_day.weekday()) // 7 + 1

def returnMockedES():
    return {
        'issueKey': 'APMI-53',
        'estimatedStorypoints': 3.0,
        'rawModelOutputFull': [
            "La visualizzazione dei dati di un'indagine in sola lettura richiede un'implementazione che permetta di mostrare tutte le informazioni relative all'indagine in modo chiaro e leggibile. Questo può comportare la creazione di una pagina o di un componente dedicato che mostri i dettagli dell'indagine in un formato facilmente comprensibile per l'utente. Inoltre, è necessario gestire correttamente la navigazione all'interno dell'applicazione per permettere all'utente di tornare indietro alla lista delle indagini."
        ],
        'estimationMethod': 'consenso',
        'verifiedSimilarTasks': defaultdict(
            list,
            {
                '2.0': [
                    {
                        'key': 'APMI-39',
                        'description': 'The task involves creating a user interface component that allows users to view detailed information from a list of entries. It requires implementing functionality to disable editing capabilities for certain users, ensuring only navigation options are available. Additionally, the task includes managing user roles and access permissions to maintain data integrity.',
                        'similarityScore': '0.7494'
                    },
                    {
                        'key': 'APPD-98',
                        'description': 'The task involves creating a user interface feature that allows users to view detailed information of an item in a read-only format. This requires implementing a mechanism to open a detailed view with all fields disabled, ensuring that specific additional information is still accessible.',
                        'similarityScore': '0.7338'
                    }
                ],
                '3.0': [
                    {
                        'key': 'APPD-69',
                        'description': 'The task involves creating a user interface component that displays detailed information from a selected item. This component should present specific attributes as a title and subtitle, allow users to view non-editable details, and include navigation functionality to return to a previous view.',
                        'similarityScore': '0.7738'
                    },
                    {
                        'key': 'DDSO-501',
                        'description': 'The task involves creating a new user interface component that displays a list of items with specific conditions. This component should be consistently visible across all instances and provide read-only information. If certain values are absent, a predefined message should be shown in place of the data.',
                        'similarityScore': '0.7226'
                    },
                    {
                        'key': 'PENT-4006',
                        'description': 'The task involves implementing a read-only feature that allows users to view detailed information and history from a list. It requires creating a user interface component to display these details, ensuring data fields are non-editable unless specific permissions are granted, and integrating a contextual menu for navigation.',
                        'similarityScore': '0.8153'
                    }
                ],
                '5.0': [
                    {
                        'key': 'APMC-415',
                        'description': 'The task involves creating a new user interface component that allows users to view a list of items. This component should include navigation between different sections and provide basic information for each item. Additionally, ensure that users can switch between tabs seamlessly without additional functionalities like export or detailed views.',
                        'similarityScore': '0.7497'
                    },
                    {
                        'key': 'APPI-10',
                        'description': 'The task involves creating a user interface component that allows administrative users to view detailed information from a list. This includes implementing navigation to a detailed view upon selection, integrating external APIs for data retrieval, and ensuring conditional display of specific sections based on data availability.',
                        'similarityScore': '0.7668'
                    },
                    {
                        'key': 'APPI-20',
                        'description': 'The task involves creating a user interface component that allows administrative users to view detailed information from a list. It requires integrating external APIs for data retrieval, displaying specific fields while omitting others, and ensuring conditional visibility of certain sections based on data availability.',
                        'similarityScore': '0.7448'
                    }
                ]
            }
        )
    }