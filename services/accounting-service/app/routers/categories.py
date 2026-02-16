from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])

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

@router.put("/{id}", response_model=schemas.Category, summary="修改分類")
def update_category(id: int, category: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cat, key, value)
    
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/{id}", summary="刪除分類")
def delete_category(id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.Category).filter(models.Category.id == id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(db_cat)
    db.commit()
    return {"message": "Category deleted"}
