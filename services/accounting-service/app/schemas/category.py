
from pydantic import Field

from . import AuditSchema, BaseSchema


class CategoryBase(BaseSchema):
    name: str = Field(..., description="分類名稱", examples=["餐飲"])
    color: str | None = Field(None, description="顯示顏色 (HEX)", examples=["#FF5733"])


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseSchema):
    name: str | None = Field(None, description="分類名稱", examples=["餐飲"])
    color: str | None = Field(None, description="顯示顏色 (HEX)", examples=["#FF5733"])


class Category(CategoryBase, AuditSchema):
    id: int


class CategoryMergeRequest(BaseSchema):
    source_category_id: int = Field(..., description="來源分類 ID")
    target_category_id: int = Field(..., description="目標分類 ID")


class CategoryMergePreview(BaseSchema):
    source_category: Category
    target_category: Category
    affected_transactions: int = Field(..., description="受影響交易數量")
    affected_subscriptions: int = Field(..., description="受影響訂閱數量")


class CategoryMergeResult(CategoryMergePreview):
    deleted_source_category_id: int = Field(..., description="已刪除的來源分類 ID")
