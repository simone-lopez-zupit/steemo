import json
import numpy as np
import faiss
import openai
import logging
import pandas as pd
from app.config import JSON_EMBED_FILE, OPENAI_KEY, MAX_PARALLEL_AI
from app.jira_utils import get_issue_text_async
from asyncio import Semaphore, gather
from app.prompts import STORY_POINT_PROMPT_WITH_TEXT, TASK_SIMILARITY_PROMPT_TEMPLATE

log = logging.getLogger(__name__)
aio_client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
semaphore = Semaphore(MAX_PARALLEL_AI)

with open(JSON_EMBED_FILE, "r", encoding="utf-8") as f:
    dataset = json.load(f)
tasks = dataset if isinstance(dataset, list) else list(dataset.values())
embeddings_train = np.array([t["embedding"] for t in tasks], dtype="float32")

faiss.normalize_L2(embeddings_train)
faiss_index_train = faiss.IndexFlatIP(embeddings_train.shape[1])
faiss_index_train.add(embeddings_train)


CSV_FILE = "data/english_stories_with_emb_no_estimated.csv"
no_estimated = pd.read_csv(CSV_FILE)
tasks_new = []
if not no_estimated.empty:
    for _, row in no_estimated.iterrows():
        emb = np.array(json.loads(row["embedding"]), dtype="float32").reshape(1, -1)
        tasks_new.append({
            "story_key": row["key"],
            "description": row["description"],
            "storypoints": row.get("story_points", None),
            "embedding": emb.tolist()
        })

embeddings_new = np.vstack([
    np.array(t["embedding"], dtype="float32").reshape(-1)
    for t in tasks_new
])
if len(embeddings_new) > 0:
    faiss.normalize_L2(embeddings_new)
    faiss_index_new = faiss.IndexFlatIP(embeddings_new.shape[1])
    faiss_index_new.add(embeddings_new)
else:
    faiss_index_new = None 



def update_new_faiss_index():
    """Ricarica solo l'indice FAISS delle nuove storie dal CSV."""
    global faiss_index_new, tasks_new

    no_estimated = pd.read_csv(CSV_FILE)
    tasks_new = []
    embeddings_list = []

    for _, row in no_estimated.iterrows():
        emb = np.array(json.loads(row["embedding"]), dtype="float32").reshape(1, -1)
        tasks_new.append({
            "story_key": row["key"],
            "description": row["description"],
            "storypoints": row.get("story_points", None),
            "embedding": emb.tolist()
        })
        embeddings_list.append(emb)

    if embeddings_list:
        embeddings = np.vstack(embeddings_list)
        faiss.normalize_L2(embeddings)
        faiss_index_new = faiss.IndexFlatIP(embeddings.shape[1])
        faiss_index_new.add(embeddings)
    else:
        faiss_index_new = None




def get_embedding(text: str) -> np.ndarray:
    sync_client = openai.OpenAI(api_key=OPENAI_KEY)
    resp = sync_client.embeddings.create(
        input=text.strip(), model="text-embedding-3-small"
    )
    emb = np.array(resp.data[0].embedding, dtype="float32")
    faiss.normalize_L2(emb.reshape(1, -1))
    return emb

async def check_similarity(target_text: str, candidate_key: str,) -> bool:
    return candidate_key


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
    
async def openai_description_with_factors(full_input, sp) -> str:
    response = await aio_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": STORY_POINT_PROMPT_WITH_TEXT},
            {"role": "user", "content": f"story point: {sp}\n\nstoria:\n\n {full_input}"}
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()