from app.embedding_utils import refresh_new_index
from app.repository import task_exists, update_feedback


def give_feedback(story_key: str, feedback: str):
    if task_exists(story_key):
        update_feedback(story_key, feedback)
        refresh_new_index()
    