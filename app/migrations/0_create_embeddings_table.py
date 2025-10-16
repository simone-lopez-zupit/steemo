import pandas as pd
import json
import numpy as np
from jira_extractor.steemo.app.repository import insert_task
import sqlite3
from pathlib import Path

DB_PATH = Path("../data/embeddings.db")
DB_PATH.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS trained_tasks (
    story_key TEXT PRIMARY KEY,
    description TEXT,
    storypoints REAL,
    embedding BLOB
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS new_tasks (
    story_key TEXT PRIMARY KEY,
    description TEXT,
    storypoints REAL,
    embedding BLOB
)
""")

conn.commit() 

df = pd.read_csv("data/english_stories_with_emb_no_estimated.csv")

for _, row in df.iterrows():
    emb = np.array(json.loads(row["embedding"]), dtype="float32")
    insert_task(
        table="new_tasks",
        story_key=row["key"],
        description=row["description"],
        storypoints=row["story_points"],
        embedding=emb
    )

print("✅ Import completato")
def populate_from_json(file_path: str, table: str):
    """Legge un file JSON e inserisce i record nella tabella specificata."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📂 Importando {len(data)} record da {file_path} in tabella '{table}'...")

    for item in data:
        story_key = item.get("story_key")
        description = item.get("description", "")
        storypoints = item.get("storypoints")
        embedding = np.array(item.get("embedding", []), dtype="float32")

        insert_task(
            table=table,
            story_key=story_key,
            description=description,
            storypoints=storypoints,
            embedding=embedding,
        )

    print(f"✅ Completato import {file_path} → {table}\n")



TRAINED_FILE = "data/english_stories_with_emb.json"
populate_from_json(TRAINED_FILE, "trained_tasks")