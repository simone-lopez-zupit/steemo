import os, sys, json, asyncio, difflib
from typing import List, Dict

# aggiungi il path al progetto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.estimation import estimate_with_similars
from app.models import StoryRequest

BASE_DIR = "../data/pdf_last2weeks"
RUNS     = 1                         
OUT_DIR  = "data"
FILE_TPL = "estimation_results_run{}.json"

# ────────────────────────────────────────────────────────────────
async def run_single_batch(output_path: str) -> List[Dict]:
    """Esegue UNA scansione del dataset e scrive il JSON in `output_path`."""
    results = []

    # se vuoi sovrascrivere sempre
    if os.path.exists(output_path):
        os.remove(output_path)

    for sp_dir in os.listdir(BASE_DIR):
        try:
            true_points = float(sp_dir)
        except ValueError:
            continue

        sp_path = os.path.join(BASE_DIR, sp_dir)
        if not os.path.isdir(sp_path):
            continue

        for filename in os.listdir(sp_path):
            if not filename.lower().endswith(".pdf"):
                continue

            issue_key = filename[:-4]          # rimuove ".pdf"
            print(f"📄 Estimating {issue_key} (truth: {true_points})...")

            req = StoryRequest(
                issueKey=issue_key,
                additionalComment="",
                searchFiles=False,
                similarityThreshold=0.7
            )

            try:
                est = await estimate_with_similars(req)
                sp   = est.get("estimated_storypoints", -1)
                err  = None
            except Exception as e:
                sp   = None
                err  = str(e)

            results.append({
                "issue_key": issue_key,
                "true_points": true_points,
                "stimated_points": sp,
                **({"error": err} if err else {})
            })

            # salva progressivamente
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

    return results

# ────────────────────────────────────────────────────────────────
def files_are_equal(file_a: str, file_b: str) -> bool:
    """Confronto testuale dei due JSON (ignora differenze di newline)."""
    with open(file_a, encoding="utf-8") as fa, open(file_b, encoding="utf-8") as fb:
        return fa.read().strip() == fb.read().strip()

def pretty_diff(file_a: str, file_b: str) -> None:
    """Stampa un diff umanamente leggibile tra due file JSON."""
    with open(file_a, encoding="utf-8") as fa, open(file_b, encoding="utf-8") as fb:
        diff = difflib.unified_diff(
            fa.readlines(), fb.readlines(),
            fromfile=file_a, tofile=file_b, lineterm=""
        )
        print("\n".join(diff))



# ────────────────────────────────────────────────────────────────
async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    first_file = None
    all_equal  = True

    for run in range(1, RUNS + 1):
        out_path = os.path.join(OUT_DIR, FILE_TPL.format(run))
        print(f"\n=== RUN {run}/{RUNS} → {out_path} ===")
        await run_single_batch(out_path)

        if first_file is None:
            first_file = out_path
        else:
            if not files_are_equal(first_file, out_path):
                all_equal = False
                print(f"\n❌ Differenze rilevate fra {first_file} e {out_path}")
                pretty_diff(first_file, out_path)
                break

    if all_equal:
        print("\n✅ Tutti i file sono identici!")

# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
