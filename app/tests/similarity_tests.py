import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import re
import statistics
from collections import defaultdict
from typing import Optional, Dict, Any

from fastapi import HTTPException
from asyncio import gather

import openai
from collections import Counter
import json
from app.models import JQLRequest, StoryRequest
from app.jira_utils import get_all_queried_stories, get_issue_text_async
from app.embedding_utils import get_embedding, check_similarity, faiss_index, ollama_check_similarity, ollama_stima, ollama_summary, tasks
from app.config import MODEL_NAME, NUM_SEMANTIC_DESCRIPTION, TOP_K_SIMILAR
from app.prompts import (
    ABSTRACT_SUMMARY_PROMPT,
    FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE,
    STORY_POINT_PROMPT,
    STORY_POINT_PROMPT_WITH_TEXT
)
from app.estimation_utils import analyze_results
import math


# Config votazione similarità
SIMILARITY_VOTES = 3
MAJORITY_THRESHOLD = (SIMILARITY_VOTES // 2) + 1

# Traccia stabilità similarità true/false
similarity_verdicts = defaultdict(lambda: {"candidates": 0, "confirmed_true": 0})

aio_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))


async def search_similar_tasks(issue_key: str, similarity_threshold: float = 0.7) -> Dict[str, list]:
    try:
        full_input = await get_issue_text_async(issue_key)

        abstracts = [
            await ollama_summary(full_input)
            for _ in range(3)
        ]

        cand_scores = {}
        for abstr in abstracts:
            q_emb = get_embedding(abstr).reshape(1, -1)
            scores, idxs = faiss_index.search(q_emb, TOP_K_SIMILAR)
            for s, idx in zip(scores[0], idxs[0]):
                if s < similarity_threshold:
                    continue
                key = tasks[idx]["story_key"]
                if key != issue_key and key not in cand_scores:
                    cand_scores[key] = s
                if len(cand_scores) >= TOP_K_SIMILAR:
                    break

        tasks_by_key = {t["story_key"]: t for t in tasks}

        async def check_similar(k):
            t = tasks_by_key.get(k, {})
            candidate_text = t.get("full_text") or t.get("description") or ""
            if not candidate_text.strip():
                return None

            similarity_verdicts[k]["candidates"] += 1

            # Majority voting con SIMILARITY_VOTES
            results = await gather(*[
                ollama_check_similarity(full_input, candidate_text)
                for _ in range(SIMILARITY_VOTES)
            ])
            num_true = sum(1 for r in results if r)
            is_similar = num_true >= MAJORITY_THRESHOLD

            if is_similar:
                similarity_verdicts[k]["confirmed_true"] += 1

            return k if is_similar else None

        print("Candidati:", len(cand_scores))
        print("Lista candidati:", cand_scores)

        found_results = await gather(*[check_similar(k) for k in cand_scores])
        found_keys = {k for k in found_results if k}

        print("Trovati similari:", len(found_keys))
        print("Lista trovati:", found_keys)

        verified_similars: Dict[str, list] = defaultdict(list)

        for t in tasks:
            if t["story_key"] in found_keys:
                try:
                    sp_val = float(t["storypoints"])
                except (ValueError, TypeError):
                    continue

                sim = cand_scores[t["story_key"]]
                verified_similars[str(sp_val)].append({
                    "key": t["story_key"],
                    "description": t["description"],
                    "similarity_score": f"{sim:.4f}"
                })

        return verified_similars

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


async def main():
    issue_key = "APMI-7"
    iterations = 10
    similarity_threshold = 0.4

    all_runs = []

    print(f"🔍 Testando la stabilità dei task similari per: {issue_key}")
    for i in range(iterations):
        print(f"\n=== Iterazione {i + 1} ===")
        result = await search_similar_tasks(issue_key, similarity_threshold=similarity_threshold)
        all_runs.append(result)

    def extract_keys(run_result):
        return {task["key"] for lst in run_result.values() for task in lst}

    sets_of_keys = [extract_keys(run) for run in all_runs]

    base = sets_of_keys[0]
    for idx, current in enumerate(sets_of_keys[1:], 2):
        added = current - base
        removed = base - current
        print(f"\n🧾 Differenze con iterazione {idx}:")
        if added:
            print("  ➕ Aggiunti:", added)
        if removed:
            print("  ➖ Rimossi:", removed)
        if not added and not removed:
            print("  ✅ Nessuna differenza.")

    jaccard_scores = []
    for other in sets_of_keys[1:]:
        inter = len(base & other)
        union = len(base | other)
        score = inter / union if union > 0 else 1.0
        jaccard_scores.append(score)

    mean_jaccard = round(statistics.mean(jaccard_scores), 4)
    print(f"\n📊 Similarità media Jaccard con la prima iterazione: {mean_jaccard}")

    from itertools import combinations
    all_pairs = list(combinations(sets_of_keys, 2))
    pairwise_jaccard = []
    for a, b in all_pairs:
        inter = len(a & b)
        union = len(a | b)
        score = inter / union if union > 0 else 1.0
        pairwise_jaccard.append(score)

    mean_pairwise_jaccard = round(statistics.mean(pairwise_jaccard), 4)
    print(f"📌 Similarità Jaccard media su tutte le coppie: {mean_pairwise_jaccard}")

    freq_counter = defaultdict(int)
    for s in sets_of_keys:
        for k in s:
            freq_counter[k] += 1

    print("\n📈 Frequenza apparizione task:")
    for key, count in sorted(freq_counter.items(), key=lambda x: -x[1]):
        print(f"  {key}: {count}/{iterations}")

    total = sum(freq_counter.values())
    entropy = -sum((v / total) * math.log2(v / total) for v in freq_counter.values())
    max_entropy = math.log2(len(freq_counter)) if freq_counter else 1
    normalized_entropy = round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0
    print(f"\n📉 Entropia normalizzata della distribuzione: {normalized_entropy}")

    common_keys = set.intersection(*sets_of_keys)
    print(f"\n🔒 Task presenti in tutte le {iterations} iterazioni: {len(common_keys)}")
    if common_keys:
        print("  ✔️", common_keys)

    # 🔁 Stampa stabilità dei giudizi di similarità
    print("\n🔁 Stabilità della similarità per ciascun task candidato:")
    sorted_verdicts = sorted(similarity_verdicts.items(), key=lambda x: -x[1]["candidates"])
    for key, data in sorted_verdicts:
        total = data["candidates"]
        confirmed = data["confirmed_true"]
        ratio = confirmed / total if total > 0 else 0.0
        print(f"  {key}: {confirmed}/{total} → stabilità = {ratio:.2f}")

    # 💾 Salvataggi
    with open("similari_risultati.json", "w") as f:
        json.dump(all_runs, f, indent=2)

    with open("frequenze_similari.json", "w") as f:
        json.dump(freq_counter, f, indent=2)

    with open("stabilita_similarita.json", "w") as f:
        json.dump(similarity_verdicts, f, indent=2)

    print("\n✅ Analisi completata.")


if __name__ == "__main__":
    asyncio.run(main())
