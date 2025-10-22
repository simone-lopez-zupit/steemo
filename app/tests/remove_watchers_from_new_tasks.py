
from app.jira_utils import remove_watcher
from app.repository import conn


def fetch_story_keys() -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT story_key FROM new_tasks")
        rows = cur.fetchall() or []
    return [row[0] for row in rows]


def main() -> None:
    story_keys = fetch_story_keys()
    print(f"🔍 Trovate {len(story_keys)} storie nella tabella new_tasks")

    for story_key in story_keys:
        try:
            result = remove_watcher(story_key)
            if result.get("removed"):
                print(f"✅ Watcher rimosso da {story_key}")
            else:
                print(f"ℹ️ Nessuna rimozione necessaria per {story_key}")
        except Exception as exc:
            print(f"⚠️ Errore durante la rimozione per {story_key}: {exc}")


if __name__ == "__main__":
    main()

