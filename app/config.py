import os
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
ZUPIT_BOT_TOKEN = os.getenv("ZUPIT_BOT_TOKEN")
ZUPIT_BOT_EMAIL = os.getenv("ZUPIT_BOT_EMAIL")
OPENAI_KEY = os.getenv("OPENAI_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
STORY_POINTS_FLD = os.getenv("STORY_POINTS_FLD")
TOP_K_SIMILAR = int(os.getenv("TOP_K_SIMILAR", 20))
NUM_SEMANTIC_DESCRIPTION = int(os.getenv("NUM_SEMANTIC_DESCRIPTION", 5))
