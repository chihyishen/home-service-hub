"""定期定額設定。"""

from sqlalchemy import Boolean, CheckConstraint, Column, Date, Integer, Numeric, String
from sqlalchemy.sql import expression

from ..database import Base, TimestampMixin


class DcaPlan(Base, TimestampMixin):
    __tablename__ = "dca_plans"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_dca_plans_amount_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_dca_plans_day_range"),
        CheckConstraint("fee >= 0", name="ck_dca_plans_fee_nonnegative"),
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), nullable=False)
    amount = Column(Integer, nullable=False)  # 每期扣款金額 (含手續費)
    day_of_month = Column(Integer, nullable=False)  # 扣款日；遇非交易日順延
    fee = Column(Numeric(12, 2), nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True, server_default=expression.true())
    last_executed_on = Column(Date, nullable=True)  # 最近一次建立交易的成交日
