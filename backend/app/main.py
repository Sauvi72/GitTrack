import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import engine, Base, SessionLocal
from app.models import Teacher, TrackingScope
from pwdlib import PasswordHash
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.students import router as students_router
from app.api.scopes import router as scopes_router
from app.api.sync import router as sync_router
from app.api.pull_requests import router as pull_requests_router
from app.api.dashboard import router as dashboard_router
from app.api.reports import router as reports_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("opentrack")

pwd_context = PasswordHash.recommended()


def seed_initial_data():
    """Seeds initial teacher and default global tracking scope if not present."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.critical("Failed to create tables or reach database: %s", e, exc_info=True)
        return

    db = SessionLocal()
    try:
        # Check teacher
        teacher = db.query(Teacher).filter(Teacher.email == settings.INITIAL_TEACHER_EMAIL).first()
        if not teacher:
            hashed_pwd = pwd_context.hash(settings.INITIAL_TEACHER_PASSWORD)
            new_teacher = Teacher(
                email=settings.INITIAL_TEACHER_EMAIL,
                hashed_password=hashed_pwd,
                full_name=settings.INITIAL_TEACHER_NAME,
                is_active=True
            )
            db.add(new_teacher)
            logger.info("Created initial teacher account: %s", settings.INITIAL_TEACHER_EMAIL)

        # Check default global scope
        global_scope = db.query(TrackingScope).filter(TrackingScope.scope_type == "global").first()
        if not global_scope:
            new_scope = TrackingScope(
                scope_type="global",
                scope_value="*",
                display_name="Global Public GitHub",
                is_active=True
            )
            db.add(new_scope)
            logger.info("Initialized default global tracking scope")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to seed initial data: %s", e, exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OpenTrack API...")
    seed_initial_data()
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down OpenTrack API...")


app = FastAPI(
    title=settings.APP_NAME,
    description="OpenTrack — GitHub Student Contribution Tracker REST API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base API routers
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(scopes_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(pull_requests_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(reports_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to OpenTrack API",
        "documentation": "/docs",
        "health": "/api/health"
    }
