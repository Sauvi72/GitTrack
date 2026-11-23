import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    github_username = Column(String(100), unique=True, index=True, nullable=False)
    github_user_id = Column(BigInteger, unique=True, nullable=True, index=True)
    display_name = Column(String(150), nullable=True)
    profile_url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

    # Relationships
    pull_requests = relationship("PullRequest", back_populates="student", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Student id={self.id} username={self.github_username}>"
