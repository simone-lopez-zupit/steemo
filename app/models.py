from pydantic import BaseModel
from typing import Optional

class StoryRequest(BaseModel):
    issue_key: str
    additional_comment: Optional[str] = ""
    search_files: bool = False
    similarity_threshold: float = 0.70