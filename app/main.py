import os
import sys
from fastapi import FastAPI
from app.estimation import estimate_by_query, estimate_with_similars
from app.models import ChartDataRequest, ChartType, EstimationResponse, JQLRequest, StoryRequest
from app.jira_utils import get_all_queried_stories
from app.history import query_chart, query_outlier_tasks
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict

from app.estimation_utils import returnMockedES

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

app = FastAPI(
    title="STEEMO",
    openapi_version="3.0.2"  
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:4200'],
    allow_methods=['*'],
    allow_headers=['*'],
)
@app.post(
    "/estimate_with_similars/",
    tags=["estimation"],
    response_model=EstimationResponse
)
async def estimate(data: StoryRequest):
    #return returnMockedES()
    return await estimate_with_similars(data)

@app.post("/estimate_from_jql/", tags=["estimation"])
async def estimate_jql(data: JQLRequest):
    return await estimate_by_query(data)

@app.post("/get_time_series_chart", tags=["charts"])
def get_results_from_query(data: ChartDataRequest):
    return query_chart(data, ChartType.lineTimeSeries)

@app.post("/get_total_stacked_chart", tags=["charts"])
def get_total_stacked_query(data: ChartDataRequest):
    return query_chart(data, ChartType.totalStacked)

@app.post("/get_scatter_accurcy_chart",tags=["charts"])
def get_scatter_accuacy_query(data:ChartDataRequest):
    return query_chart(data,ChartType.scatterAccuracy)
@app.post("/get_outlier_tasks", tags=["tasks"])
def get_outlier_tasks(data: ChartDataRequest):
    return query_outlier_tasks(data)