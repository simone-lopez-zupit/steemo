import os
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
EMAIL = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
WKHTML_PATH = os.getenv("WKHTML_PATH")
JSON_EMBED_FILE = os.getenv("JSON_EMBED_FILE")
MODEL_NAME = os.getenv("MODEL_NAME")
STORY_POINTS_FLD = os.getenv("STORY_POINTS_FLD")
TOP_K_SIMILAR = int(os.getenv("TOP_K_SIMILAR", 20))
MAX_PARALLEL_AI = int(os.getenv("MAX_PARALLEL_AI", 5))
NUM_SEMANTIC_DESCRIPTION = int(os.getenv("NUM_SEMANTIC_DESCRIPTION", 5))