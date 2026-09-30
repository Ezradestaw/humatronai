import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.orm import relationship
from core.database import Base
from core.models.user import gen_uuid, utc_now

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    STUDENT = "student"
    PRO = "pro"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_tier = Column(String(50), default=SubscriptionTier.FREE.value, nullable=False)
    status = Column(String(50), default=SubscriptionStatus.ACTIVE.value, nullable=False)
    price_usd = Column(Numeric(10, 2), default=0.00, nullable=False)
    price_etb = Column(Numeric(10, 2), default=0.00, nullable=False)
    max_monthly_files = Column(Integer, default=10, nullable=False)
    start_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    renewal_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="subscriptions")
    payments = relationship("PaymentTransaction", back_populates="subscription", cascade="all, delete-orphan")

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False) # e.g. "telebirr", "binance_pay", "card"
    transaction_reference = Column(String(150), unique=True, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False) # "USD", "ETB", "USDT"
    status = Column(String(50), default="pending", nullable=False) # "pending", "success", "failed"
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    subscription = relationship("Subscription", back_populates="payments")
