import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.tracking_scope import TrackingScope
from app.schemas.scope import ScopeCreate, ScopeUpdate, ScopeResponse

logger = logging.getLogger("opentrack.api.scopes")
router = APIRouter(prefix="/scopes", tags=["Tracking Scopes"])


@router.get("", response_model=List[ScopeResponse])
def get_scopes(db: Session = Depends(get_db)):
    """Retrieve all configured tracking scopes."""
    return db.query(TrackingScope).order_by(TrackingScope.created_at.asc()).all()


@router.post("", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
def create_scope(payload: ScopeCreate, db: Session = Depends(get_db)):
    """
    Add a new tracking scope (organization or repository).
    Enforces format validation (e.g. repo must be owner/name).
    """
    scope_type = payload.scope_type.lower().strip()
    scope_value = payload.scope_value.strip()

    if scope_type not in ("global", "organization", "repository"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope_type must be 'global', 'organization', or 'repository'."
        )

    if scope_type == "repository" and "/" not in scope_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository scope_value must be in the format 'owner/repo'."
        )

    # Check for existing duplicate
    existing = db.query(TrackingScope).filter(
        func.lower(TrackingScope.scope_value) == scope_value.lower(),
        TrackingScope.scope_type == scope_type
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scope '{scope_value}' already configured."
        )

    url = payload.url
    if not url:
        if scope_type == "organization":
            url = f"https://github.com/{scope_value}"
        elif scope_type == "repository":
            url = f"https://github.com/{scope_value}"

    scope = TrackingScope(
        scope_type=scope_type,
        scope_value=scope_value,
        display_name=payload.display_name or scope_value,
        url=url,
        is_active=True
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


@router.patch("/{scope_id}", response_model=ScopeResponse)
def update_scope(scope_id: int, payload: ScopeUpdate, db: Session = Depends(get_db)):
    """Enable or disable a tracking scope or edit its label."""
    scope = db.query(TrackingScope).filter(TrackingScope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found.")

    if payload.is_active is not None:
        scope.is_active = payload.is_active
    if payload.display_name is not None:
        scope.display_name = payload.display_name

    db.commit()
    db.refresh(scope)
    return scope


@router.delete("/{scope_id}")
def delete_scope(scope_id: int, db: Session = Depends(get_db)):
    """Remove a tracking scope. The default global scope cannot be deleted, only deactivated."""
    scope = db.query(TrackingScope).filter(TrackingScope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found.")

    if scope.scope_type == "global":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The global public scope cannot be deleted. You may disable it instead."
        )

    db.delete(scope)
    db.commit()
    return {"message": f"Scope '{scope.scope_value}' deleted successfully."}
