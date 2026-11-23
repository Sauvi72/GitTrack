import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.session import Base


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(BigInteger, unique=True, index=True, nullable=False)
    github_node_id = Column(String(100), unique=True, index=True, nullable=False)  # Primary deduplication key
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    
    repository_full_name = Column(String(255), index=True, nullable=False)
    repository_owner = Column(String(150), index=True, nullable=False)
    repository_name = Column(String(150), nullable=False)
    organization_name = Column(String(150), nullable=True, index=True)
    
    pr_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    html_url = Column(String(500), nullable=False)
    state = Column(String(20), nullable=False)  # "open" or "closed"
    status = Column(String(30), nullable=False, index=True)  # "OPEN", "MERGED", "CLOSED_UNMERGED"
    is_draft = Column(Boolean, default=False, nullable=False)
    
    # Author info on GitHub
    author_username = Column(String(100), nullable=False, index=True)
    author_github_id = Column(BigInteger, nullable=True)

    # GitHub timestamps
    created_at_github = Column(DateTime, nullable=False, index=True)
    updated_at_github = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    merged_at = Column(DateTime, nullable=True, index=True)
    merged_by = Column(String(100), nullable=True)
    
    # Git branches
    base_branch = Column(String(150), nullable=True)
    head_branch = Column(String(150), nullable=True)
    
    # Code metrics
    commits = Column(Integer, default=0, nullable=False)
    additions = Column(Integer, default=0, nullable=False)
    deletions = Column(Integer, default=0, nullable=False)
    changed_files = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    review_comments = Column(Integer, default=0, nullable=False)
    
    # Internal sync metadata
    last_checked_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationships
    student = relationship("Student", back_populates="pull_requests")

    __table_args__ = (
        UniqueConstraint("repository_full_name", "pr_number", name="uq_repo_pr_number"),
        Index("ix_pr_student_status", "student_id", "status"),
        Index("ix_pr_created_github", "created_at_github"),
    )

    def __repr__(self) -> str:
        return f"<PullRequest id={self.id} repo={self.repository_full_name} pr#{self.pr_number} status={self.status}>"
