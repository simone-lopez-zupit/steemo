import os
import json
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("🟢 Connected to PostgreSQL on Render")

cur.execute("""
CREATE TABLE IF NOT EXISTS trained_tasks (
    story_key TEXT PRIMARY KEY,
    description TEXT,
    storypoints REAL,
    embedding BYTEA
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS new_tasks (
    story_key TEXT PRIMARY KEY,
    description TEXT,
    storypoints REAL,
    embedding BYTEA,
    feedback TEXT
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS story (
    issue_key TEXT PRIMARY KEY,
    true_points REAL,
    stimated_points REAL,
    created TIMESTAMP,
    month INT,
    year INT,
    week_of_month INT
);
""")

conn.commit()
print("✅ Tables created successfully\n")


TRAINED_FILE = "data/english_stories_with_emb.json"
with open(TRAINED_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

trained_records = [
    (
        d.get("story_key"),
        d.get("description", ""),
        d.get("storypoints"),
        np.array(d.get("embedding", []), dtype="float32").tobytes(),
    )
    for d in data
]

execute_values(
    cur,
    """
    INSERT INTO trained_tasks (story_key, description, storypoints, embedding)
    VALUES %s
    ON CONFLICT (story_key) DO UPDATE
        SET description = EXCLUDED.description,
            storypoints = EXCLUDED.storypoints,
            embedding = EXCLUDED.embedding;
    """,
    trained_records,
)
conn.commit()
print(f"✅ Imported {len(trained_records)} trained_tasks\n")


CSV_FILE = "data/english_stories_with_emb_no_estimated.csv"
df = pd.read_csv(CSV_FILE)

new_records = []
for _, row in df.iterrows():
    emb = np.array(json.loads(row["embedding"]), dtype="float32")
    new_records.append((row["key"], row["description"], row["story_points"], emb.tobytes(), None))

execute_values(
    cur,
    """
    INSERT INTO new_tasks (story_key, description, storypoints, embedding, feedback)
    VALUES %s
    ON CONFLICT (story_key) DO NOTHING;
    """,
    new_records,
)
conn.commit()
print(f"✅ Imported {len(new_records)} new_tasks\n")


with open("tutto.json", "r", encoding="utf-8") as f:
    stories = json.load(f)

story_records = [
    (
        s.get("issue_key"),
        s.get("true_points"),
        s.get("stimated_points"),
        s.get("created"),
        s.get("month"),
        s.get("year"),
        s.get("week_of_month"),
    )
    for s in stories
]

execute_values(
    cur,
    """
    INSERT INTO story (issue_key, true_points, stimated_points, created, month, year, week_of_month)
    VALUES %s
    ON CONFLICT (issue_key) DO UPDATE
        SET true_points = EXCLUDED.true_points,
            stimated_points = EXCLUDED.stimated_points,
            created = EXCLUDED.created,
            month = EXCLUDED.month,
            year = EXCLUDED.year,
            week_of_month = EXCLUDED.week_of_month;
    """,
    story_records,
)
conn.commit()
print(f"✅ Imported {len(story_records)} stories\n")

cur.close()
conn.close()
print("🎉 PostgreSQL database fully initialized!")
