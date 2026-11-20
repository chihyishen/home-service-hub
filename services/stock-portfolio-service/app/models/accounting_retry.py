"""記帳同步失敗時留下的補送工作；每日 job 重送，成功即刪除。"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from ..database import Base


class AccountingRetry(Base):
    __tablename__ = "accounting_retries"

    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False)        # 'txn' / 'dividend'
    action = Column(String(16), nullable=False)      # 'create' / 'update' / 'delete'
    source_id = Column(Integer, nullable=True)       # 股票交易或股利 id；delete 時來源已刪
    accounting_id = Column(Integer, nullable=True)   # delete 要刪的記帳 id
    item = Column(String, nullable=True)             # create 用的記帳品名
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
