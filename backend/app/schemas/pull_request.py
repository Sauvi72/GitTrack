from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class PullRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_id: int
    github_node_id: str
    student_id: int
    repository_full_name: str
    repository_owner: str
    repository_name: str
    organization_name: Optional[str]
    pr_number: int
    title: str
    html_url: str
    state: str
    status: str
    is_draft: bool
    author_username: str
    created_at_github: datetime
    updated_at_github: Optional[datetime]
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    merged_by: Optional[str]
    base_branch: Optional[str]
    head_branch: Optional[str]
    commits: int
    additions: int
    deletions: int
    changed_files: int
    comments: int
    review_comments: int
    last_checked_at: datetime
