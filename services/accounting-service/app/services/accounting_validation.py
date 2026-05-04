from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


def ensure_category_exists(
    db: Session,
    category_id: int,
    *,
    invalid_detail_template: str = "Invalid category_id: {category_id}",
) -> None:
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=400,
            detail=invalid_detail_template.format(category_id=category_id),
        )


def ensure_payment_method_exists(
    db: Session,
    payment_method: str | None,
    *,
    invalid_detail_template: str = "Invalid payment_method: {payment_method}. Please add it to the system settings first.",
) -> None:
    if not payment_method:
        return

    payment_method_exists = (
        db.query(models.PaymentMethod)
        .filter(models.PaymentMethod.name == payment_method)
        .first()
    )
    if not payment_method_exists:
        raise HTTPException(
            status_code=400,
            detail=invalid_detail_template.format(payment_method=payment_method),
        )


def resolve_card_payment_defaults(
    db: Session,
    card_id: int | None,
    requested_payment_method: str | None,
    *,
    invalid_detail_template: str = "Invalid card_id: {card_id}",
) -> str | None:
    if not card_id:
        return requested_payment_method

    card = db.query(models.CreditCard).filter(models.CreditCard.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=400,
            detail=invalid_detail_template.format(card_id=card_id),
        )

    if not requested_payment_method or requested_payment_method == "信用卡":
        return card.default_payment_method or "Apple Pay"
    return requested_payment_method
