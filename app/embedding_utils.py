import os
import json
import numpy as np
import faiss
import openai
import time
import logging
import httpx
import re

from collections import defaultdict
from app.config import JSON_EMBED_FILE, OPENAI_KEY, TOP_K_SIMILAR, MAX_PARALLEL_AI
from app.jira_utils import get_issue_text_async
from asyncio import Semaphore, gather
from app.prompts import ABSTRACT_SUMMARY_PROMPT, STORY_POINT_PROMPT, STORY_POINT_PROMPT_WITH_TEXT, TASK_SIMILARITY_PROMPT_TEMPLATE, STORY_POINT_PROMPT_few_shots

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

async def check_similarity(target_text: str, candidate_key: str, model: str = "gpt-4o") -> str | None:
    return candidate_key


async def ollama_check_similarity(text1: str, text2: str) -> bool:
    prompt = TASK_SIMILARITY_PROMPT_TEMPLATE(text1, text2)

    payload = {
        "model": "gemma3:latest",
        "prompt": prompt,
        "temperature": 0,
        "seed": 42,
        "stream": False
    }

    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()["response"].strip().lower()
        print("[similarity result]", result)
        return result.startswith("true")

async def filter_similar_tasks(keys, full_input):
    async def is_similar(k):
        try:
            candidate_text = await get_issue_text_async(k)
            return k if await ollama_check_similarity(full_input, candidate_text) else None
        except Exception as e:
            print(f"Errore su {k}: {e}")
            return None

    results = await gather(*[is_similar(k) for k in keys])
    return {k for k in results if k}

async def ollama_summary(text1: str) -> float:
    
    payload = {
        "model": "gemma3:latest",
        "prompt": f"""{ABSTRACT_SUMMARY_PROMPT}\n\nStory:\n{text1}""",
        "temperature": 0,
        "seed": 42,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()["response"].strip().lower()
        return result
    
async def ollama_response(sp, storia) -> str:
    payload = {
        "model": "gemma3:latest",
        "prompt": f"{STORY_POINT_PROMPT_WITH_TEXT}\nsp:{sp}, \n\nstoria:\n\n {storia}",
        "temperature": 0,
        "seed": 42,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()["response"].strip()

        # Rimuove eventuali markdown ```json``` o altri marker dal risultato
        clean_result = re.sub(r'^```json|```$', '', result, flags=re.MULTILINE).strip()

        # Parsing JSON automatico
        clean_result

        return clean_result