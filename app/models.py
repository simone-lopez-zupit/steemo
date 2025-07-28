from datetime import date, datetime
from pydantic import BaseModel
from typing import Dict, List, Literal, Optional
from enum import Enum

class StoryRequest(BaseModel):
    issueKey: str
    additionalComment: Optional[str] = ""
    searchFiles: bool = False
    similarityThreshold: float = 0.70
    maxFibDistance: Optional[int] = 1

class JQLRequest(BaseModel):
    project:str="all"
    date_jql:str="created >= -2w"
    file_to_save:str="temp.json"

class TimeGranularity(str, Enum):
    week = "week"
    month = "month"
    year = "year"

class ChartDataRequest(BaseModel):
    projects: Optional[List[str]] = None
    startDate: date
    endDate: date
    granularity: Literal["week", "month", "year"]


class ChartType(str, Enum):
    lineTimeSeries = "lineTimeSeries"
    totalStacked = "totalStacked"
    proportionalDonut="proportionalDonut"
    scatterAccuracy = "scatterAccuracy"
    
class SimilarTask(BaseModel):
    key: str
    description: str
    similarityScore: str            

class EstimationResponse(BaseModel):
    issueKey: str
    estimatedStorypoints: float
    rawModelOutputFull: str
    estimationMethod: str
    verifiedSimilarTasks: Dict[str, List[SimilarTask]] = {}