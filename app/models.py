from pydantic import BaseModel
from typing import Optional

class StoryRequest(BaseModel):
    issue_key: str
    additional_comment: Optional[str] = ""
    search_files: bool = False
    similarity_threshold: float = 0.70
    max_fib_distance: Optional[int] = 1

class JQLRequest(BaseModel):
    project:str="all"
    date_jql:str="created >= -2w"