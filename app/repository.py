import numpy as np
import psycopg2
import psycopg2.extras
from app.config import DATABASE_URL


conn = psycopg2.connect(DATABASE_URL)



def insert_task(table: str, story_key: str, description: str, storypoints: float, embedding: np.ndarray):
    """Inserisce o aggiorna una storia nel DB."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {table} (story_key, description, storypoints, embedding)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (story_key)
            DO UPDATE SET 
                description = EXCLUDED.description,
                storypoints = EXCLUDED.storypoints,
                embedding = EXCLUDED.embedding;
            """,
            (story_key, description, storypoints, embedding.tobytes()),
        )
    conn.commit()


def get_all_tasks(table: str):
    """Restituisce tutte le storie da una tabella."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT story_key, description, storypoints, embedding FROM {table}")
        rows = cur.fetchall() or []
    tasks = []
    for row in rows:
        tasks.append(
            {
                "story_key": row["story_key"],
                "description": row["description"],
                "storypoints": row["storypoints"],
                "embedding": np.frombuffer(row["embedding"], dtype="float32"),
            }
        )
    return tasks


def task_exists(issue_key: str, table: str = "new_tasks") -> bool:
    with conn.cursor() as cur:
        cur.execute(f"SELECT 1 FROM {table} WHERE story_key = %s", (issue_key,))
        return cur.fetchone() is not None


def insert_new_task(issue_key: str, description: str, storypoints: float, embedding: np.ndarray, table: str = "new_tasks"):
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {table} (story_key, description, storypoints, embedding) VALUES (%s, %s, %s, %s)",
            (issue_key, description, storypoints, embedding.tobytes()),
        )
    conn.commit()


def get_task_description(issue_key: str, table: str = "new_tasks") -> str | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT description FROM {table} WHERE story_key = %s", (issue_key,))
        row = cur.fetchone()
        return row["description"] if row else None


def update_feedback(issue_key: str, feedback: str, table: str = "new_tasks"):
    normalized_feedback = feedback.strip() if isinstance(feedback, str) else feedback
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {table} SET feedback = %s WHERE story_key = %s",
            (normalized_feedback, issue_key),
        )
    conn.commit()
    if table == "new_tasks":
        from app.embedding_utils import refresh_new_index

        refresh_new_index()


def load_embeddings(table: str):
    """Carica le storie e i loro embedding da una tabella del DB."""
    base_query = f"SELECT story_key, description, storypoints, embedding FROM {table}"
    if table == "new_tasks":
        filtered_query = base_query + " WHERE UPPER(TRIM(feedback)) IN ('GIUSTA', 'SPOSTA')"
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            try:
                cur.execute(filtered_query)
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                cur.execute(base_query)
            return cur.fetchall() or []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(base_query)
        return cur.fetchall() or []



def fetch_all_stories() -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT issue_key, true_points, stimated_points, created, month, year, week_of_month
            FROM story
            """
        )
        return cur.fetchall() or []


def story_exists(issue_key: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM story WHERE issue_key = %s", (issue_key,))
        return cur.fetchone() is not None


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
    """Inserisce o aggiorna una riga nella tabella story."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO story (issue_key, true_points, stimated_points, created, month, year, week_of_month)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (issue_key) DO UPDATE SET
                true_points = EXCLUDED.true_points,
                stimated_points = EXCLUDED.stimated_points,
                created = EXCLUDED.created,
                month = EXCLUDED.month,
                year = EXCLUDED.year,
                week_of_month = EXCLUDED.week_of_month;
            """,
            (issue_key, true_points, stimated_points, created, month, year, week_of_month),
        )
    conn.commit()
