from sqlalchemy import Column, String, Boolean, DateTime, BigInteger
from core.database import Base
from core.models.user import gen_uuid, utc_now

class AccountLinkingToken(Base):
    __tablename__ = "account_linking_tokens"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
