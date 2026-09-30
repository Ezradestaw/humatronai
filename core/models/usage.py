from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database import Base
from core.models.user import gen_uuid, utc_now

class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    month_year = Column(String(7), nullable=False) # e.g. "2026-09"
    files_processed = Column(Integer, default=0, nullable=False)
    last_processed_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "month_year", name="uq_user_month_usage"),
    )

    user = relationship("User", back_populates="usage_records")
