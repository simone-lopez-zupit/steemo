from pathlib import Path
import numpy as np
import sqlite3

DB_PATH = Path("data/embeddings.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
def insert_task(table: str, story_key: str, description: str, storypoints: float, embedding: np.ndarray):
    """Inserisce o aggiorna una storia nel DB"""
    cursor.execute(f"""
    INSERT OR REPLACE INTO {table} (story_key, description, storypoints, embedding)
    VALUES (?, ?, ?, ?)
    """, (story_key, description, storypoints, embedding.tobytes()))
    conn.commit()


def get_all_tasks(table: str):
    """Restituisce tutte le storie da una tabella"""
    cursor.execute(f"SELECT story_key, description, storypoints, embedding FROM {table}")
    rows = cursor.fetchall()
    tasks = []
    for r in rows:
        tasks.append({
            "story_key": r[0],
            "description": r[1],
            "storypoints": r[2],
            "embedding": np.frombuffer(r[3], dtype="float32")
        })
    return tasks

def task_exists(issue_key: str, table="new_tasks") -> bool:
    cursor.execute(f"SELECT 1 FROM {table} WHERE story_key = ?", (issue_key,))
    return cursor.fetchone() is not None

def insert_new_task(issue_key: str, description: str, storypoints: float, embedding: np.ndarray, table="new_tasks"):
    cursor.execute(
        f"INSERT INTO {table} (story_key, description, storypoints, embedding) VALUES (?, ?, ?, ?)",
        (issue_key, description, storypoints, embedding.tobytes()),
    )
    conn.commit()

def get_task_description(issue_key: str, table="new_tasks") -> str | None:
    """
    Restituisce la descrizione salvata nel DB per una determinata storia.
    Se non trovata, restituisce None.
    """
    cursor.execute(f"SELECT description FROM {table} WHERE story_key = ?", (issue_key,))
    row = cursor.fetchone()
    return row[0] if row else None

def update_feedback(issue_key: str, feedback: str, table="new_tasks"):
    cursor.execute(
        f"UPDATE {table} SET feedback = ? WHERE story_key = ?",
        (feedback, issue_key)
    )
    conn.commit()

def load_embeddings(table: str):
    """
    Carica le storie e i loro embedding da una tabella del DB.
    Restituisce una lista di dizionari con le storie e un indice FAISS normalizzato.
    Se non ci sono embedding, restituisce None per l'indice FAISS.
    """
    cursor.execute(f"SELECT story_key, description, storypoints, embedding FROM {table}")
    return cursor.fetchall()

    