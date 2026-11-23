import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database.session import Base


class TrackingScope(Base):
    __tablename__ = "tracking_scopes"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(30), nullable=False, index=True)  # 'global', 'organization', 'repository'
    scope_value = Column(String(255), nullable=False, unique=True, index=True)  # '*', 'org-name', 'owner/repo'
    display_name = Column(String(255), nullable=True)
    url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<TrackingScope id={self.id} type={self.scope_type} value={self.scope_value} active={self.is_active}>"
