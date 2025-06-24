# app/estimation.py

import re
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException
from app.models import StoryRequest
from app.jira_utils import generate_pdf_base64_from_jira, get_issue_text_async
from app.embedding_utils import get_embedding, check_similarity, faiss_index, tasks
from app.config import MODEL_NAME, NUM_SEMANTIC_DESCRIPTION, TOP_K_SIMILAR
from app.prompts import (
    ABSTRACT_SUMMARY_PROMPT,
    FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE,
    STORY_POINT_PROMPT
)

import openai
import os
from asyncio import gather, Semaphore, to_thread

aio_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))

async def estimate_with_similars(data: StoryRequest) -> dict:
    try:
        full_input = await get_issue_text_async(data.issue_key)
        if data.additional_comment:
            full_input += f"\n\nUlteriori aggiornamenti: {data.additional_comment}"

        sp_resp = await aio_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": STORY_POINT_PROMPT},
                {"role": "user", "content": full_input}
            ],
            temperature=0,
        )

        estimate_output = sp_resp.choices[0].message.content.strip()
        first_line = estimate_output.splitlines()[0]
        m = re.match(r"^\s*(\d+(\.\d+)?)", first_line)
        estimated_sp = float(m.group(1)) if m else -1
        estimate_output = estimate_output.strip().split("\n")[2:] if estimated_sp > 0 else estimate_output

        verified_similars: dict[str, list] = {}
        summary_comment = ""

        if data.search_files:
            query_pdf_b64 = await to_thread(generate_pdf_base64_from_jira, data.issue_key)
            candidate_keys_set = set()

            for _ in range(NUM_SEMANTIC_DESCRIPTION):
                summary_resp = await aio_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "file",
                                "file": {
                                    "filename": f"{data.issue_key}.pdf",
                                    "file_data": f"data:application/pdf;base64,{query_pdf_b64}"
                                }
                            },
                            {"type": "text", "text": ABSTRACT_SUMMARY_PROMPT},
                        ],
                    }],
                    temperature=1,
                )

                abstract = summary_resp.choices[0].message.content.strip()
                q_emb = get_embedding(abstract).reshape(1, -1)
                scores, idxs = faiss_index.search(q_emb, TOP_K_SIMILAR)

                for score, idx in zip(scores[0], idxs[0]):
                    if score < data.similarity_threshold:
                        continue
                    key = tasks[idx]["story_key"]
                    if key != data.issue_key:
                        candidate_keys_set.add(key)
                    if len(candidate_keys_set) >= TOP_K_SIMILAR:
                        break
                if len(candidate_keys_set) >= TOP_K_SIMILAR:
                    break

            candidates = [t for t in tasks if t["story_key"] in candidate_keys_set][:TOP_K_SIMILAR]
            coro_list = [check_similarity(full_input, t["story_key"]) for t in candidates]
            found_keys = [k for k in await gather(*coro_list) if k]

            grouped = defaultdict(list)
            for t in candidates:
                if t["story_key"] in found_keys:
                    grouped[t["storypoints"]].append({
                        "key": t["story_key"],
                        "description": t["description"],
                    })
            verified_similars = grouped

            similar_sps: list[float] = []
            for sp_str, lst in verified_similars.items():
                try:
                    similar_sps.extend([float(sp_str)] * len(lst))
                except ValueError:
                    continue

            if similar_sps:
                exp_prompt = {
                    "role": "user",
                    "content": FINAL_ESTIMATION_COMMENT_PROMPT_TEMPLATE(estimated_sp, similar_sps)
                }
                cmnt_resp = await aio_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[exp_prompt],
                    temperature=0.3
                )
                summary_comment = cmnt_resp.choices[0].message.content.strip()

        return {
            "issue_key": data.issue_key,
            "estimated_storypoints": estimated_sp,
            "raw_model_output": estimate_output,
            "verified_similar_tasks": verified_similars,
            "estimation_comment": summary_comment,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
