from fastapi import FastAPI
from app.estimation import estimate_with_similars
from app.models import StoryRequest

app = FastAPI(title="STEEMO")

@app.post("/estimate_with_similars/")
async def estimate(data: StoryRequest):
    return await estimate_with_similars(data)