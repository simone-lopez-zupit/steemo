import os
import re
import statistics
from collections import defaultdict
from typing import Optional, Dict, Any

from fastapi import HTTPException
from asyncio import gather

import openai
from collections import Counter

from app.models import JQLRequest, StoryRequest
from app.jira_utils import get_all_queried_stories, get_issue_text_async
from app.embedding_utils import get_embedding, check_similarity, faiss_index, tasks
from app.config import MODEL_NAME, NUM_SEMANTIC_DESCRIPTION, TOP_K_SIMILAR
from app.prompts import (
    ABSTRACT_SUMMARY_PROMPT,
    FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE,
    STORY_POINT_PROMPT
)
from app.estimation_utils import analyze_results
aio_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))


FIBONACCI_STEPS = [0.5, 1, 2, 3, 5, 8, 13, 21]
ALPHA = 0.3  
def closest_fibonacci(value: float) -> float:
    return min(FIBONACCI_STEPS, key=lambda v: (abs(v - value), v - value < 0))

def is_within_fib_steps(estimated: float, other: float, max_steps: int) -> bool:
    try:
        i_est = FIBONACCI_STEPS.index(estimated)
        i_other = FIBONACCI_STEPS.index(other)
        return abs(i_est - i_other) <= max_steps
    except ValueError:
        return False

async def estimate_with_similars(data: StoryRequest) -> Dict[str, Any]:
    try:
        full_input = await get_issue_text_async(data.issue_key)
        if data.additional_comment:
            full_input += f"\n\n*Importanti* aggiornamenti: {data.additional_comment}"

        estimate_tasks = [
            aio_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": STORY_POINT_PROMPT},
                          {"role": "user", "content": full_input}],
                temperature=0,
            )
            for _ in range(5)
        ]
        sp_responses = await gather(*estimate_tasks)

        raw_outputs, estimates = [], []
        for i, resp in enumerate(sp_responses, 1):
            out = resp.choices[0].message.content.strip()
            raw_outputs.append(out)
            m = re.match(r"^\s*(\d+(\.\d+)?)", out.splitlines()[0])
            if m:
                estimates.append(float(m.group(1)))

        consensus_estimate = next((v for v in set(estimates) if estimates.count(v) >= 4), None)
        estimation_source = "consenso" if consensus_estimate is not None else "mediato"
        estimated_sp = consensus_estimate if consensus_estimate is not None else -1

        min_est, max_est   = min(estimates, default=0), max(estimates, default=0)
        min_fib, max_fib   = closest_fibonacci(min_est), closest_fibonacci(max_est)
        min_idx            = max(FIBONACCI_STEPS.index(min_fib) - 1, 0)
        max_idx            = min(FIBONACCI_STEPS.index(max_fib) + 1, len(FIBONACCI_STEPS) - 1)
        allowed_idx        = set(range(min_idx, max_idx + 1))

        should_search = (consensus_estimate is None) or data.search_files
        verified_similars: Dict[str, list] = defaultdict(list)

        if should_search:
            query_text = await get_issue_text_async(data.issue_key)

            abstracts = [
                (await aio_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user",
                               "content": f"{query_text}\n\n{ABSTRACT_SUMMARY_PROMPT}"}],
                    temperature=1,      
                )).choices[0].message.content.strip()
                for _ in range(NUM_SEMANTIC_DESCRIPTION)
            ]

            # Candidati similari via FAISS
            cand_scores = {}
            for abstr in abstracts:
                q_emb = get_embedding(abstr).reshape(1, -1)
                scores, idxs = faiss_index.search(q_emb, TOP_K_SIMILAR)
                for s, idx in zip(scores[0], idxs[0]):
                    if s < data.similarity_threshold:
                        continue
                    key = tasks[idx]["story_key"]
                    if key != data.issue_key and key not in cand_scores:
                        cand_scores[key] = s
                    if len(cand_scores) >= TOP_K_SIMILAR:
                        break

            found_keys = {k for k in await gather(
                *[check_similarity(full_input, k) for k in cand_scores]
            ) if k}

            for t in tasks:
                if t["story_key"] in found_keys:
                    sp_val = float(t["storypoints"])
                    try:
                        sp_idx = FIBONACCI_STEPS.index(sp_val)
                    except ValueError:
                        continue
                    if sp_idx not in allowed_idx:
                        continue  # fuori fascia
                    sim = cand_scores[t["story_key"]]
                    verified_similars[str(sp_val)].append({
                        "key":            t["story_key"],
                        "description":    t["description"],
                        "similarity_score": f"{sim:.4f}"
                    })

        if consensus_estimate is None:
            if verified_similars:
                all_sp = [
                    closest_fibonacci(e) for e in estimates         
                ]
                all_sp.extend(
                    float(sp)                                        
                    for sp, lst in verified_similars.items()
                    for _ in lst
                )
                most_common_sp, _ = Counter(all_sp).most_common(1)[0]
                estimated_sp      = float(most_common_sp)
                estimation_source = "majority_similar"
            else:
                median_est     = statistics.median(estimates) if estimates else 0.0
                estimated_sp   = closest_fibonacci(round(median_est, 2))
                estimation_source = "fallback_median"


        output_to_show=""
        for out in raw_outputs:
            m = re.match(r"^\s*(\d+(\.\d+)?)", out.splitlines()[0])
            if float(m.group(1))==float(estimated_sp):
                output_to_show=out.splitlines()[2:]
        return {
            "issue_key":            data.issue_key,
            "estimated_storypoints": estimated_sp,
            "raw_model_output_full": output_to_show,
            "estimation_method":     estimation_source,
            "verified_similar_tasks": verified_similars if data.search_files else {},
        }

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    

async def estimate_by_query(jqlRequest:JQLRequest):
    issues=await get_all_queried_stories(jqlRequest)
    print("issue to analyze: ",len(issues))
    results=[]
    for issue in issues:
        req = StoryRequest(
                issue_key=issue[0],
                additional_comment="",
                search_files=False,
                similarity_threshold=0.7
            )
        try:
            est = await estimate_with_similars(req)
            sp   = est.get("estimated_storypoints", -1)
            err  = None
        except Exception as e:
            sp   = None
            err  = str(e)

        results.append({
            "issue_key": issue[0],
            "true_points": issue[1],
            "stimated_points": sp,
            **({"error": err} if err else {})
        })
    analyze_results(results)

