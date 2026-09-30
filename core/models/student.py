import enum
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from core.models.user import gen_uuid, utc_now

class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class StudentVerification(Base):
    __tablename__ = "student_verifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    educational_email = Column(String(255), nullable=False, index=True)
    institution_name = Column(String(255), nullable=False)
    status = Column(String(50), default=VerificationStatus.PENDING.value, nullable=False)
    verification_code = Column(String(64), nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="student_verifications")
