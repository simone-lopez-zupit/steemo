import os
import re
import statistics
from collections import defaultdict
from typing import Optional, Dict, Any

from fastapi import HTTPException
from asyncio import gather

import openai
from collections import Counter
import json
from app.models import EstimationResponse, JQLRequest, StoryRequest
from app.jira_utils import get_all_queried_stories, get_issue_text_async
from app.embedding_utils import filter_similar_tasks, get_embedding, check_similarity, faiss_index, ollama_check_similarity, ollama_response, tasks
from app.config import MODEL_NAME, NUM_SEMANTIC_DESCRIPTION, TOP_K_SIMILAR
from app.prompts import (
    ABSTRACT_SUMMARY_PROMPT,
    FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE,
    STORY_POINT_PROMPT,
    STORY_POINT_PROMPT_WITH_TEXT
)
from app.estimation_utils import analyze_results, get_week_of_month
from datetime import datetime

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

async def estimate_with_similars(data: StoryRequest) -> EstimationResponse:
    try:
        full_input = await get_issue_text_async(data.issueKey)
        if data.additionalComment:
            full_input += f"\n\n **Importanti aggiornamenti:**{data.additionalComment}"

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
        #estimates=[1]*5
    
        raw_outputs = [str(estimates[0])] * 5 
        

        consensus_estimate = next((v for v in set(estimates) if estimates.count(v) >= 4), None)
        estimation_source = "consenso" if consensus_estimate is not None else "mediato"
        estimated_sp = consensus_estimate if consensus_estimate is not None else -1

        min_est, max_est   = min(estimates, default=0), max(estimates, default=0)
        min_fib, max_fib   = closest_fibonacci(min_est), closest_fibonacci(max_est)
        min_idx            = max(FIBONACCI_STEPS.index(min_fib) - data.maxFibDistance, 0)
        max_idx            = min(FIBONACCI_STEPS.index(max_fib) + data.maxFibDistance, len(FIBONACCI_STEPS) - 1)
        allowed_idx        = set(range(min_idx, max_idx + 1))

        should_search = (consensus_estimate is None) or data.searchFiles
        verified_similars: Dict[str, list] = defaultdict(list)

        if should_search:
            query_text = await get_issue_text_async(data.issueKey)

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
                    if s < data.similarityThreshold:
                        continue
                    key = tasks[idx]["story_key"]
                    if key != data.issueKey and key not in cand_scores:
                        cand_scores[key] = s
                    if len(cand_scores) >= TOP_K_SIMILAR:
                        break

            found_keys = await filter_similar_tasks(cand_scores.keys(), full_input)


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
                        "similarityScore": f"{sim:.4f}"
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


        # output_to_show=""
        
        # for out in raw_outputs:
        #     m = re.match(r"^\s*(\d+(\.\d+)?)", out.splitlines()[0])
        #     if float(m.group(1))==float(estimated_sp):
        #         output_to_show=out.splitlines()[2:]
        # output = await aio_client.chat.completions.create(
        #     model=MODEL_NAME,
        #     messages=[
        #         {"role": "system", "content": STORY_POINT_PROMPT_WITH_TEXT},
        #         {"role": "user",   "content": f"sp:{estimated_sp}, storia:{full_input}"}
        #     ],
        #     temperature=0,
        # )

        # output_to_show = output.choices[0].message.content.strip()
        # output_to_show=output_to_show.splitlines()[2:]
        output_to_show= await ollama_response(estimated_sp,full_input)

        response={
            "issueKey":            data.issueKey,
            "estimatedStorypoints": estimated_sp,
            "rawModelOutputFull": output_to_show,
            "estimationMethod":     estimation_source,
            "verifiedSimilarTasks": verified_similars if data.searchFiles else {},
        }
        print(response)
        return response

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    

async def estimate_by_query(jqlRequest: JQLRequest):
    if os.path.exists(jqlRequest.file_to_save):
        with open(jqlRequest.file_to_save, "r") as f:
            existing_results = json.load(f)
        already_estimated_keys = {item["issue_key"] for item in existing_results}
    else:
        existing_results = []
        already_estimated_keys = set()

    issues = await get_all_queried_stories(jqlRequest)
    print("Issues da analizzare:", len(issues))
    total = len(issues)
    processed = 0
    skipped = 0

    for idx, issue in enumerate(issues, start=1):
        issue_key = issue[0]
        true_points = issue[1]
        created_at = issue[2]

        if issue_key in already_estimated_keys:
            skipped += 1
            continue

        date_obj = datetime.strptime(created_at[:10], "%Y-%m-%d")
        month = date_obj.month
        year = date_obj.year
        week = get_week_of_month(created_at)

        req = StoryRequest(
            issueKey=issue_key,
            additionalComment="",
            searchFiles=False,
            similarityThreshold=0.7
        )

        try:
            est = await estimate_with_similars(req)
            sp = est.get("estimated_storypoints", -1)
            err = None
        except Exception as e:
            sp = None
            err = str(e)

        new_entry = {
            "issue_key": issue_key,
            "true_points": true_points,
            "stimated_points": sp,
            "created": created_at,
            "month": month,
            "year": year,
            "week_of_month": week,
            **({"error": err} if err else {})
        }

        existing_results.append(new_entry)

        with open(jqlRequest.file_to_save, "w") as f:
            json.dump(existing_results, f, indent=4)

        processed += 1
        print(f"[{idx}/{total}] Elaborato: {issue_key} - Stimato: {sp}")

    return {"estimated": processed, "skipped": skipped}