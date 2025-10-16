import os
import statistics
from collections import defaultdict
from typing import  Dict
import pandas as pd
from fastapi import HTTPException
from asyncio import gather

import openai
from collections import Counter
import json
from app.models import EstimationResponse, JQLRequest, StoryRequest
from app.jira_utils import add_comment, format_verified_similars, get_all_queried_stories, get_issue_text_async, update_comment
from app.embedding_utils import filter_similar_tasks, get_embedding, faiss_index_train,faiss_index_new,tasks_new,tasks_train, openai_description_with_factors
from app.config import MODEL_NAME, NUM_SEMANTIC_DESCRIPTION, TOP_K_SIMILAR
from app.prompts import (
    ABSTRACT_SUMMARY_PROMPT,
    STORY_POINT_PROMPT,
)
from app.estimation_utils import get_week_of_month
from datetime import datetime
from app.repository import get_task_description, insert_new_task, task_exists
from app.embedding_utils import refresh_new_index
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
        
        estimates=await openai_chat_completion_for_times(full_input,5)        

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
        new_verified_similars: Dict[str, list] = defaultdict(list)
        if should_search:
            query_text = await get_issue_text_async(data.issueKey)            

            if task_exists(data.issueKey):
                desc = get_task_description(data.issueKey)
                abstracts = [desc] if desc else []

            else:
                abstracts = [
                    (
                        await aio_client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "user", "content": f"{query_text}\n\n{ABSTRACT_SUMMARY_PROMPT}"}
                            ],
                            temperature=1,
                        )
                    ).choices[0].message.content.strip()
                    for _ in range(NUM_SEMANTIC_DESCRIPTION)
                ]

            cand_scores = {}
            for abstr in abstracts:
                q_emb = get_embedding(abstr).reshape(1, -1)
                scores, idxs = faiss_index_train.search(q_emb, TOP_K_SIMILAR)
                for s, idx in zip(scores[0], idxs[0]):
                    if s < data.similarityThreshold:
                        continue
                    key = tasks_train[idx]["story_key"]
                    if key != data.issueKey and key not in cand_scores:
                        cand_scores[key] = s
                    if len(cand_scores) >= TOP_K_SIMILAR:
                        break

            found_keys = await filter_similar_tasks(cand_scores.keys(), full_input)


            for t in tasks_train:
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
        


# ============ 🔹 FAISS SEARCH: NEW INDEX ============ #
               
            if faiss_index_new is not None and len(tasks_new) > 0:
                cand_scores_new = {}
                for abstr in abstracts:
                    q_emb = get_embedding(abstr).reshape(1, -1)
                    scores, idxs = faiss_index_new.search(q_emb, TOP_K_SIMILAR)
                    for s, idx in zip(scores[0], idxs[0]):
                        if s < data.similarityThreshold:
                            continue
                        key = tasks_new[idx]["story_key"]
                        if key != data.issueKey and key not in cand_scores_new:
                            cand_scores_new[key] = s
                        if len(cand_scores_new) >= TOP_K_SIMILAR:
                            break
                found_keys = await filter_similar_tasks(cand_scores_new.keys(), full_input)

                for t in tasks_new:
                    if t["story_key"] in found_keys:
                        sp_val = float(t["storypoints"]) if t["storypoints"] else 0.0
                        sim = cand_scores_new[t["story_key"]]
                        new_verified_similars[str(sp_val)].append({
                            "key": t["story_key"],
                            "description": t["description"],
                            "similarityScore": f"{sim:.4f}"
                        })



        best_description = abstracts[0] if abstracts else full_input
        best_score = -1.0
        if not task_exists(data.issueKey):
            for sp_group in verified_similars.values():
                for item in sp_group:
                    score = float(item["similarityScore"])
                    if score > best_score:
                        best_score = score
                        best_description = item["description"]
            
            embedding = get_embedding(best_description).reshape(1, -1)
            insert_new_task(
                issue_key=data.issueKey,
                description=best_description,
                storypoints=estimated_sp,
                embedding=embedding,
            )
            refresh_new_index()

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

        output_to_show= await openai_description_with_factors(full_input,estimated_sp)

        response={
            "issueKey":            data.issueKey,
            "estimatedStorypoints": estimated_sp,
            "rawModelOutputFull": output_to_show,
            "estimationMethod":     estimation_source,
            "verifiedSimilarTasks": verified_similars if data.searchFiles else {},
            "newSimilarTasks": new_verified_similars if data.searchFiles else {},
        }
        print(response)
        return response

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    
async def openai_chat_completion_for_times(full_input, times):
    estimate_task=[
        aio_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": STORY_POINT_PROMPT},
                      {"role": "user", "content": full_input}],
            temperature=0,
        )
        for _ in range(times)

    ]

    sp_response = await gather(*estimate_task, return_exceptions=True)
    estimates=[float(resp.choices[0].message.content.strip()) for resp in sp_response]
    return estimates

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
            sp = est.get("estimatedStorypoints", -1)
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



async def estimate_for_jira(data: dict):
    issue_key = data.get("key")
    
    fields = data.get("fields", {})

    comments = fields.get("comment", {}).get("comments", [])

    steemo_comment = next(
        (c for c in comments if "STEEMO" in c.get("body", "") and "ZupitBot" in c.get("author", {}).get("displayName", "")),
        None
    )
    
    story_request = StoryRequest(
        issueKey=issue_key,
        additionalComment="",
        searchFiles=True,
        similarityThreshold=0.60,
        maxFibDistance=1
    )
    estimation_result = await estimate_with_similars(story_request)
    verified=format_verified_similars(estimation_result.get("verifiedSimilarTasks", {}))
    new=format_verified_similars(estimation_result.get("newSimilarTasks", {}))
    new_comment_body = (
        f"Ciao sono STEEMO e penso che questa storia vada stimata: {estimation_result['estimatedStorypoints']}\n\n"
        f"Breve descrizione: {estimation_result['rawModelOutputFull']}\n\n"
        f"Riferimenti conosciuti:\n{verified}\n\n"
        f"Simili coerenti e non sbagliate:\n{new}"
    )

    if steemo_comment:
            comment_id = steemo_comment["id"]
            update_comment(issue_key, comment_id, new_comment_body)
    else:
        add_comment(issue_key, new_comment_body)

    return 