from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..database import Base, TimestampMixin

class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    color = Column(String, nullable=True) # 前端顯示用
    is_deleted = Column(Boolean, default=False)

    # 關聯到交易紀錄
    transactions = relationship("Transaction", back_populates="category_info")
