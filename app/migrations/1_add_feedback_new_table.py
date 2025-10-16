import sqlite3
from pathlib import Path

DB_PATH = Path("data/embeddings.db")
DB_PATH.parent.mkdir(exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_tasks'")
table_exists = cursor.fetchone()

if not table_exists:
    print("⚠️ Tabella 'new_tasks' non trovata. Crea prima il database con populate_db.py")
else:
    cursor.execute("PRAGMA table_info(new_tasks)")
    columns = [col[1] for col in cursor.fetchall()]

    if "feedback" not in columns:
        cursor.execute("ALTER TABLE new_tasks ADD COLUMN feedback TEXT DEFAULT NULL")
        conn.commit()
        print("✅ Colonna 'feedback' aggiunta con successo a 'new_tasks'")
    else:
        print("ℹ️ Colonna 'feedback' già presente in 'new_tasks'")

conn.close()