import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.teacher import Teacher
from app.schemas.auth import LoginRequest, TokenResponse, TeacherResponse, TeacherUpdateRequest
from app.core.security import verify_password, create_access_token, get_current_teacher
from app.core.config import settings

logger = logging.getLogger("opentrack.api.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Authenticate teacher credentials.
    Issues JWT bearer token and sets secure HTTP-only cookie.
    """
    clean_email = payload.email.lower().strip()
    teacher = db.query(Teacher).filter(Teacher.email == clean_email).first()

    if not teacher or not verify_password(payload.password, teacher.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    if not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact system administrator."
        )

    access_token = create_access_token(data={"sub": teacher.email, "id": teacher.id})

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False if settings.APP_ENV == "development" else True
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
def logout(response: Response):
    """Log out teacher and clear session cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=TeacherResponse)
def get_current_teacher_profile(current_teacher: Teacher = Depends(get_current_teacher)):
    """Retrieve currently authenticated teacher's profile."""
    return current_teacher


@router.patch("/me", response_model=TeacherResponse)
def update_current_teacher_profile(
    payload: TeacherUpdateRequest,
    db: Session = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    """Update authenticated teacher's profile (customizable full_name)."""
    if payload.full_name is not None and payload.full_name.strip():
        current_teacher.full_name = payload.full_name.strip()
        db.commit()
        db.refresh(current_teacher)
    return current_teacher
