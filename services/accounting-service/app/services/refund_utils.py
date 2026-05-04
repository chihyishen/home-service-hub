from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def get_refunded_amounts(db: Session, transaction_ids: list[int]) -> dict[int, int]:
    if not transaction_ids:
        return {}

    refunded_rows = (
        db.query(
            models.Transaction.related_transaction_id,
            func.coalesce(func.sum(models.Transaction.transaction_amount), 0),
        )
        .filter(
            models.Transaction.related_transaction_id.in_(transaction_ids),
            models.Transaction.transaction_type == "INCOME",
        )
        .group_by(models.Transaction.related_transaction_id)
        .all()
    )

    return {
        int(related_transaction_id): int(amount or 0)
        for related_transaction_id, amount in refunded_rows
        if related_transaction_id is not None
    }