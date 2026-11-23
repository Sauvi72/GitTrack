import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    scope_id = Column(Integer, ForeignKey("tracking_scopes.id", ondelete="SET NULL"), nullable=True, index=True)
    
    started_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, SUCCESS, FAILED, PARTIAL
    
    discovered_count = Column(Integer, default=0, nullable=False)
    new_pr_count = Column(Integer, default=0, nullable=False)
    updated_pr_count = Column(Integer, default=0, nullable=False)
    
    error_message = Column(Text, nullable=True)
    is_complete = Column(Boolean, default=True, nullable=False)  # False if GitHub search was capped or paginated out

    # Relationships
    student = relationship("Student", back_populates="sync_logs")
    scope = relationship("TrackingScope")

    __table_args__ = (
        Index("ix_sync_logs_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<SyncLog id={self.id} student={self.student_id} status={self.status}>"
