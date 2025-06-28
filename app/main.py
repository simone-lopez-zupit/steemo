from fastapi import FastAPI
from app.estimation import estimate_by_query, estimate_with_similars
from app.models import JQLRequest, StoryRequest
from app.jira_utils import get_all_queried_stories

app = FastAPI(title="STEEMO")

@app.post("/estimate_with_similars/")
async def estimate(data: StoryRequest):
    return await estimate_with_similars(data)

@app.post("/estimate_from_jql/")
async def estimate_jql(data: JQLRequest):
    return await estimate_by_query(data)