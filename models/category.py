from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    items = relationship("InventoryItem", back_populates="category", lazy="selectin")