from pydantic import Field
from typing import Optional
from . import BaseSchema, AuditSchema

class CategoryBase(BaseSchema):
    name: str = Field(..., description="分類名稱", examples=["餐飲"])
    color: Optional[str] = Field(None, description="顯示顏色 (HEX)", examples=["#FF5733"])

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase, AuditSchema):
    id: int
    is_deleted: bool
