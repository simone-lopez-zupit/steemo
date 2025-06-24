import os
import json
import numpy as np
import faiss
import openai
import time
import logging
from collections import defaultdict
from app.config import JSON_EMBED_FILE, OPENAI_KEY, TOP_K_SIMILAR, MAX_PARALLEL_AI
from app.jira_utils import get_issue_text_async
from asyncio import Semaphore
from app.prompts import TASK_SIMILARITY_PROMPT_TEMPLATE

log = logging.getLogger(__name__)
aio_client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
semaphore = Semaphore(MAX_PARALLEL_AI)

with open(JSON_EMBED_FILE, "r", encoding="utf-8") as f:
    dataset = json.load(f)
tasks = dataset if isinstance(dataset, list) else list(dataset.values())
embeddings = np.array([t["embedding"] for t in tasks], dtype="float32")

faiss.normalize_L2(embeddings)
faiss_index = faiss.IndexFlatIP(embeddings.shape[1])
faiss_index.add(embeddings)

def get_embedding(text: str) -> np.ndarray:
    sync_client = openai.OpenAI(api_key=OPENAI_KEY)
    resp = sync_client.embeddings.create(
        input=text.strip(), model="text-embedding-3-small"
    )
    emb = np.array(resp.data[0].embedding, dtype="float32")
    faiss.normalize_L2(emb.reshape(1, -1))
    return emb

# async def check_similarity(target_text: str, candidate_key: str, model: str = "gpt-4o") -> str | None:
#     t_start = time.perf_counter()
#     log.info("→ start  %s  %.3fs", candidate_key, t_start)
#     try:
#         candidate_text = await get_issue_text_async(candidate_key)
#         prompt = {
#             "role": "user",
#                 "content": TASK_SIMILARITY_PROMPT_TEMPLATE(target_text, candidate_text),
#         }
#         async with semaphore:
#             resp = await aio_client.chat.completions.create(
#                 model=model,
#                 messages=[prompt],
#                 temperature=0,
#             )
#         if resp.choices[0].message.content.strip().lower() == "true":
#             return candidate_key
#         return None
#     except Exception as ex:
#         log.warning("Similarity check error for %s: %s", candidate_key, ex)
#         return None
#     finally:
#         t_end = time.perf_counter()
#         log.info("← end    %s  %.3fs (Δ%.2fs)", candidate_key, t_end, t_end - t_start)

async def check_similarity(target_text: str, candidate_key: str, model: str = "gpt-4o") -> str | None:
    return candidate_key
