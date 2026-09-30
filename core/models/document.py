from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from core.models.user import gen_uuid, utc_now

class ProcessedFile(Base):
    __tablename__ = "processed_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_hash = Column(String(64), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    operation = Column(String(50), nullable=False) # e.g. "compress", "extract_text", "page_count"
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(String(50), default="completed", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="processed_files")
