import json
import numpy as np
import faiss
import openai
import logging
import pandas as pd
from app.config import OPENAI_KEY
from app.jira_utils import get_issue_text_async
from asyncio import gather
from app.prompts import STORY_POINT_PROMPT_WITH_TEXT, TASK_SIMILARITY_PROMPT_TEMPLATE
import re
import json

from app.repository import load_embeddings
log = logging.getLogger(__name__)
aio_client = openai.AsyncOpenAI(api_key=OPENAI_KEY)

def load_embeddings_from_db(table: str):
    rows = load_embeddings(table)

    tasks = []
    embeddings = []

    for row in rows:
        if isinstance(row, dict):
            story_key = row.get("story_key")
            description = row.get("description")
            storypoints = row.get("storypoints")
            emb_blob = row.get("embedding")
        else:
            story_key, description, storypoints, emb_blob = row

        if emb_blob is None:
            continue

        if isinstance(emb_blob, memoryview):
            emb_blob = emb_blob.tobytes()

        emb = np.frombuffer(emb_blob, dtype="float32")
        tasks.append({
            "story_key": story_key,
            "description": description,
            "storypoints": storypoints,
            "embedding": emb
        })
        embeddings.append(emb)

    if not embeddings:
        return tasks, None

    embeddings = np.vstack(embeddings).astype("float32")
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return tasks, index


tasks_train, faiss_index_train = load_embeddings_from_db("trained_tasks")
tasks_new, faiss_index_new = load_embeddings_from_db("new_tasks")



def refresh_new_index():
    """
    Ricarica tasks_new e faiss_index_new dal DB 'new_tasks'.
    Chiamala dopo ogni inserimento nel DB per mantenere FAISS aggiornato.
    """
    global tasks_new, faiss_index_new

    tasks_new, faiss_index_new = load_embeddings_from_db("new_tasks")



def get_embedding(text: str) -> np.ndarray:
    sync_client = openai.OpenAI(api_key=OPENAI_KEY)
    resp = sync_client.embeddings.create(
        input=text.strip(), model="text-embedding-3-small"
    )
    emb = np.array(resp.data[0].embedding, dtype="float32")
    faiss.normalize_L2(emb.reshape(1, -1))
    return emb

async def check_similarity(target_text: str, candidate_key: str,) -> bool:
    return True


# async def ollama_check_similarity(text1: str, text2: str) -> bool:
#     prompt = TASK_SIMILARITY_PROMPT_TEMPLATE(text1, text2)

#     payload = {
#         "model": "gemma3:latest",
#         "prompt": prompt,
#         "temperature": 0,
#         "seed": 42,
#         "stream": False
#     }

#     async with httpx.AsyncClient() as client:
#         r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
#         r.raise_for_status()
#         result = r.json()["response"].strip().lower()
#         print("[similarity result]", result)
#         return result.startswith("true")

async def openai_check_similarity(text1: str, text2: str) -> bool:
    try:
        response = await aio_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": TASK_SIMILARITY_PROMPT_TEMPLATE(text1, text2)}
            ],
            temperature=0,
        )
        result = response.choices[0].message.content.strip().lower()
        print("[similarity result]", result)
        return result.startswith("true")
    except Exception as e:
        log.error(f"Error during similarity check: {e}")
        return False
       

async def filter_similar_tasks(keys, full_input):
    async def is_similar(k):
        try:
            candidate_text = await get_issue_text_async(k)
            return k if await openai_check_similarity(full_input, candidate_text) else None
        except Exception as e:
            print(f"Errore su {k}: {e}")
            return None

    results = await gather(*[is_similar(k) for k in keys])
    return {k for k in results if k}

# async def ollama_summary(text1: str) -> float:
    
#     payload = {
#         "model": "gemma3:latest",
#         "prompt": f"""{ABSTRACT_SUMMARY_PROMPT}\n\nStory:\n{text1}""",
#         "temperature": 0,
#         "seed": 42,
#         "stream": False
#     }
#     async with httpx.AsyncClient() as client:
#         r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
#         r.raise_for_status()
#         result = r.json()["response"].strip().lower()
#         return result
    
# async def ollama_response(sp, storia) -> str:
#     payload = {
#         "model": "gemma3:latest",
#         "prompt": f"{STORY_POINT_PROMPT_WITH_TEXT}\nsp:{sp}, \n\nstoria:\n\n {storia}",
#         "temperature": 0,
#         "seed": 42,
#         "stream": False
#     }
#     async with httpx.AsyncClient() as client:
#         r = await client.post("http://localhost:11434/api/generate", json=payload, timeout=30)
#         r.raise_for_status()
#         result = r.json()["response"].strip()
#         clean_result = re.sub(r'^```json|```$', '', result, flags=re.MULTILINE).strip()
#         return clean_result


def extract_description_from_json_block(text: str) -> str:
    """
    Estrae il valore del campo 'descrizione' o 'descrizione_tecnica'
    da un blocco ```json ... ``` nel testo.
    Restituisce solo la stringa della descrizione, pulita.
    """
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if not match:
        return text.strip() 

    try:
        json_content = json.loads(match.group(1))
        descrizione = (
            json_content.get("descrizione_tecnica")
            or json_content.get("descrizione")
            or ""
        ).strip()
        return descrizione
    except Exception as e:
        print(f"⚠️ Errore parsing JSON: {e}")
        return text.strip()
    
async def openai_description_with_factors(full_input, sp) -> str:
    response = await aio_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": STORY_POINT_PROMPT_WITH_TEXT},
            {"role": "user", "content": f"story point: {sp}\n\nstoria:\n\n {full_input}"}
        ],
        temperature=0,
    )
    return extract_description_from_json_block(response.choices[0].message.content.strip())

