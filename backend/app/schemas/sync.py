from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SyncTriggerResponse(BaseModel):
    message: str
    student_id: Optional[int] = None
    status: str
    details: Optional[dict] = None


class SyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: Optional[int]
    scope_id: Optional[int]
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    discovered_count: int
    new_pr_count: int
    updated_pr_count: int
    error_message: Optional[str]
    is_complete: bool
