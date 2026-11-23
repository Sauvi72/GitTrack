from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class StudentBase(BaseModel):
    github_username: str = Field(..., min_length=1, max_length=100, description="GitHub username")
    display_name: Optional[str] = Field(None, max_length=150)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_username: str
    github_user_id: Optional[int]
    display_name: Optional[str]
    profile_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_synced_at: Optional[datetime]

    # Computed metrics
    total_prs: int = 0
    merged_prs: int = 0
    open_prs: int = 0
    closed_unmerged_prs: int = 0
    merge_percentage: float = 0.0

    # Today's activity
    prs_today: int = 0
    merged_today: int = 0
    open_today: int = 0
    closed_unmerged_today: int = 0
