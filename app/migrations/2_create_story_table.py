import sqlite3
from pathlib import Path
import json

DB_PATH = Path("data/embeddings.db")
DB_PATH.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS story (
    issue_key TEXT PRIMARY KEY,
    true_points REAL,
    stimated_points REAL,
    created TEXT,
    month INTEGER,
    year INTEGER,
    week_of_month INTEGER
)
""")

conn.commit()
print("✅ Tabella 'story_estimates' creata o già esistente.")


with open("tutto.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    cursor.execute("""
        INSERT OR REPLACE INTO story
        (issue_key, true_points, stimated_points, created, month, year, week_of_month)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        item.get("issue_key"),
        item.get("true_points"),
        item.get("stimated_points"),
        item.get("created"),
        item.get("month"),
        item.get("year"),
        item.get("week_of_month")
    ))

conn.commit()

print(f"✅ Importati {len(data)} record in story.")