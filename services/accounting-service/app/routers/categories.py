from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..schemas.category import CategoryMergePreview, CategoryMergeRequest, CategoryMergeResult

router = APIRouter(prefix="/categories", tags=["Categories"])


def _get_category_or_404(db: Session, category_id: int, *, detail: str) -> models.Category:
    db_cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail=detail)
    return db_cat


def _sync_category_name_references(db: Session, *, category_id: int, category_name: str) -> None:
    db.query(models.Transaction).filter(models.Transaction.category_id == category_id).update(
        {models.Transaction.category: category_name},
        synchronize_session=False,
    )
    db.query(models.Subscription).filter(models.Subscription.category_id == category_id).update(
        {models.Subscription.category: category_name},
        synchronize_session=False,
    )


def _prepare_category_merge(
    db: Session,
    merge_request: CategoryMergeRequest,
) -> tuple[models.Category, models.Category, int, int]:
    if merge_request.source_category_id == merge_request.target_category_id:
        raise HTTPException(status_code=400, detail="Source and target categories must be different")

    source_category = _get_category_or_404(
        db,
        merge_request.source_category_id,
        detail="Source category not found",
    )
    target_category = _get_category_or_404(
        db,
        merge_request.target_category_id,
        detail="Target category not found",
    )
    affected_transactions = db.query(models.Transaction).filter(
        models.Transaction.category_id == source_category.id,
    ).count()
    affected_subscriptions = db.query(models.Subscription).filter(
        models.Subscription.category_id == source_category.id,
    ).count()
    return source_category, target_category, affected_transactions, affected_subscriptions


def _build_category_merge_preview(
    *,
    source_category: models.Category,
    target_category: models.Category,
    affected_transactions: int,
    affected_subscriptions: int,
) -> CategoryMergePreview:
    return CategoryMergePreview(
        source_category=source_category,
        target_category=target_category,
        affected_transactions=affected_transactions,
        affected_subscriptions=affected_subscriptions,
    )

@router.get("/", response_model=List[schemas.Category], summary="獲獲取所有分類")
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

@router.post("/", response_model=schemas.Category, summary="新增分類")
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_cat = models.Category(**category.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@router.post("/merge-preview", response_model=CategoryMergePreview, summary="預覽分類合併")
def preview_category_merge(merge_request: CategoryMergeRequest, db: Session = Depends(get_db)):
    source_category, target_category, affected_transactions, affected_subscriptions = _prepare_category_merge(
        db,
        merge_request,
    )
    return _build_category_merge_preview(
        source_category=source_category,
        target_category=target_category,
        affected_transactions=affected_transactions,
        affected_subscriptions=affected_subscriptions,
    )


@router.post("/merge", response_model=CategoryMergeResult, summary="套用分類合併")
def merge_categories(merge_request: CategoryMergeRequest, db: Session = Depends(get_db)):
    source_category, target_category, affected_transactions, affected_subscriptions = _prepare_category_merge(
        db,
        merge_request,
    )
    source_snapshot = schemas.Category.model_validate(source_category)
    target_snapshot = schemas.Category.model_validate(target_category)

    db.query(models.Transaction).filter(models.Transaction.category_id == source_category.id).update(
        {
            models.Transaction.category_id: target_category.id,
            models.Transaction.category: target_category.name,
        },
        synchronize_session=False,
    )
    db.query(models.Subscription).filter(models.Subscription.category_id == source_category.id).update(
        {
            models.Subscription.category_id: target_category.id,
            models.Subscription.category: target_category.name,
        },
        synchronize_session=False,
    )
    db.delete(source_category)
    db.commit()

    return CategoryMergeResult(
        source_category=source_snapshot,
        target_category=target_snapshot,
        affected_transactions=affected_transactions,
        affected_subscriptions=affected_subscriptions,
        deleted_source_category_id=source_snapshot.id,
    )

@router.put("/{id}", response_model=schemas.Category, summary="修改分類")
def update_category(id: int, category: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    db_cat = _get_category_or_404(db, id, detail="Category not found")

    update_data = category.model_dump(exclude_unset=True)
    name_changed = "name" in update_data and update_data["name"] != db_cat.name
    for key, value in update_data.items():
        setattr(db_cat, key, value)

    if name_changed:
        _sync_category_name_references(db, category_id=db_cat.id, category_name=db_cat.name)

    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/{id}", summary="刪除分類")
def delete_category(id: int, db: Session = Depends(get_db)):
    db_cat = _get_category_or_404(db, id, detail="Category not found")
    db.delete(db_cat)
    db.commit()
    return {"message": "Category deleted"}
