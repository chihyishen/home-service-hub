from app import models


def test_category_lifecycle(db_session):
    category = models.Category(name="測試分類", color="#000")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    all_categories = db_session.query(models.Category).all()
    assert any(c.id == category.id for c in all_categories)

    category.name = "已修改分類"
    category.color = "#111"
    db_session.commit()
    db_session.refresh(category)
    assert category.name == "已修改分類"
    assert category.color == "#111"

    db_session.delete(category)
    db_session.commit()
    after = db_session.query(models.Category).all()
    assert all(c.id != category.id for c in after)
