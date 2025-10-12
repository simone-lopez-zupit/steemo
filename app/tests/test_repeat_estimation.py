import asyncio
import json
import sys
import os
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.estimation import estimate_with_similars
from app.models import StoryRequest

ISSUE_KEY = "PROV-182"
N_REPEATS = 100
OUTPUT_FILE = "data/repeat_PROV-182_2_results.json"

async def run_repeated_test():
    results = []
    estimation_counts = Counter()
    errors = 0

    for i in range(N_REPEATS):
        print(f"🔁 Iterazione {i+1}/{N_REPEATS}")

        req = StoryRequest(
            issueKey=ISSUE_KEY,
            additionalComment="",
            searchFiles=False,
            similarityThreshold=0.7
        )

        try:
            estimation = await estimate_with_similars(req)
            sp = estimation.get("estimated_storypoints", None)
            results.append(sp)
            estimation_counts[sp] += 1
        except Exception as e:
            print(f"⚠️ Errore: {e}")
            results.append(None)
            errors += 1

        # 🔄 Salva il file aggiornato dopo ogni stima
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    # 📊 Report finale
    print("\n📊 Risultato complessivo:")
    print(f"🔁 Totale esecuzioni: {N_REPEATS}")
    print(f"❌ Errori: {errors}")
    print(f"📐 Distribuzione stime:")
    for sp, count in estimation_counts.most_common():
        print(f"  → {sp}: {count} volte")

    most_common = estimation_counts.most_common(1)
    if most_common:
        print(f"\n🏆 Stima più frequente: {most_common[0][0]} ({most_common[0][1]} volte)")

    print(f"\n💾 Risultati salvati in {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_repeated_test())
