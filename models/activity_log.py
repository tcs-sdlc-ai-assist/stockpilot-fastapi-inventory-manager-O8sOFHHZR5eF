import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(32), nullable=False)
    item_name = Column(String(64), nullable=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_item.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=func.now())

    user = relationship("User", back_populates="activity_logs", lazy="selectin")
    item = relationship("InventoryItem", back_populates="activity_logs", lazy="selectin")