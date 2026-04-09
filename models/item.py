from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String(32), nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    reorder_level = Column(Integer, nullable=False, default=0)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="items", lazy="selectin")
    owner = relationship("User", back_populates="items", lazy="selectin")
    activity_logs = relationship("ActivityLog", back_populates="item", lazy="selectin")