import os
from pathlib import Path
import numpy as np
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
_default_db = BASE_DIR / "data" / "embeddings.db"
_db_override = os.getenv("STEEMO_DB_PATH") or os.getenv("DB_PATH")
if _db_override:
    db_candidate = Path(_db_override)
    if not db_candidate.is_absolute():
        db_candidate = (BASE_DIR / db_candidate).resolve()
    DB_PATH = db_candidate
else:
    DB_PATH = _default_db

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()


def insert_task(table: str, story_key: str, description: str, storypoints: float, embedding: np.ndarray):
    """Inserisce o aggiorna una storia nel DB."""
    cursor.execute(
        f"""
        INSERT OR REPLACE INTO {table} (story_key, description, storypoints, embedding)
        VALUES (?, ?, ?, ?)
        """,
        (story_key, description, storypoints, embedding.tobytes()),
    )
    conn.commit()


def get_all_tasks(table: str):
    """Restituisce tutte le storie da una tabella."""
    cursor.execute(f"SELECT story_key, description, storypoints, embedding FROM {table}")
    rows = cursor.fetchall()
    tasks = []
    for story_key, description, storypoints, embedding in rows:
        tasks.append(
            {
                "story_key": story_key,
                "description": description,
                "storypoints": storypoints,
                "embedding": np.frombuffer(embedding, dtype="float32"),
            }
        )
    return tasks


def task_exists(issue_key: str, table: str = "new_tasks") -> bool:
    cursor.execute(f"SELECT 1 FROM {table} WHERE story_key = ?", (issue_key,))
    return cursor.fetchone() is not None


def insert_new_task(issue_key: str, description: str, storypoints: float, embedding: np.ndarray, table: str = "new_tasks"):
    cursor.execute(
        f"INSERT INTO {table} (story_key, description, storypoints, embedding) VALUES (?, ?, ?, ?)",
        (issue_key, description, storypoints, embedding.tobytes()),
    )
    conn.commit()


def get_task_description(issue_key: str, table: str = "new_tasks") -> str | None:
    """
    Restituisce la descrizione salvata nel DB per una determinata storia.
    Se non trovata, restituisce None.
    """
    cursor.execute(f"SELECT description FROM {table} WHERE story_key = ?", (issue_key,))
    row = cursor.fetchone()
    return row[0] if row else None


def update_feedback(issue_key: str, feedback: str, table: str = "new_tasks"):
    cursor.execute(
        f"UPDATE {table} SET feedback = ? WHERE story_key = ?",
        (feedback, issue_key),
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


def fetch_all_stories() -> list[dict]:
    """
    Restituisce tutte le storie salvate nella tabella story come lista di dizionari.
    """
    rows = conn.execute(
        """
        SELECT issue_key, true_points, stimated_points, created, month, year, week_of_month
        FROM story
        """
    ).fetchall()
    return [dict(row) for row in rows]


def story_exists(issue_key: str) -> bool:
    """
    Restituisce True se la storia e' presente nella tabella story.
    """
    row = conn.execute(
        "SELECT 1 FROM story WHERE issue_key = ?",
        (issue_key,),
    ).fetchone()
    return row is not None


def upsert_story(
    *,
    issue_key: str,
    true_points,
    stimated_points,
    created: str,
    month,
    year,
    week_of_month,
) -> None:
    """
    Inserisce o aggiorna una riga nella tabella story.
    """
    conn.execute(
        """
        INSERT INTO story (issue_key, true_points, stimated_points, created, month, year, week_of_month)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(issue_key) DO UPDATE SET
            true_points = excluded.true_points,
            stimated_points = excluded.stimated_points,
            created = excluded.created,
            month = excluded.month,
            year = excluded.year,
            week_of_month = excluded.week_of_month
        """,
        (issue_key, true_points, stimated_points, created, month, year, week_of_month),
    )
    conn.commit()
