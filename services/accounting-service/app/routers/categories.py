from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/", response_model=List[schemas.Category], summary="獲取所有分類")
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).filter(models.Category.is_deleted == False).all()

@router.post("/", response_model=schemas.Category, summary="新增分類")
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_cat = models.Category(**category.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/{id}", summary="軟刪除分類")
def delete_category(id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db_cat.is_deleted = True
    db.commit()
    return {"message": "Category deleted"}
