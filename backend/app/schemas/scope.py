from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ScopeBase(BaseModel):
    scope_type: str = Field(..., description="'global', 'organization', or 'repository'")
    scope_value: str = Field(..., min_length=1, max_length=255, description="'*' for global, org name or owner/repo")
    display_name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=255)


class ScopeCreate(ScopeBase):
    pass


class ScopeUpdate(BaseModel):
    is_active: Optional[bool] = None
    display_name: Optional[str] = None


class ScopeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope_type: str
    scope_value: str
    display_name: Optional[str]
    url: Optional[str]
    is_active: bool
    created_at: datetime
