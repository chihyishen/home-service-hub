"""Durable marker for derived portfolio snapshot work."""

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..database import Base


class PortfolioRecalcState(Base):
    __tablename__ = "portfolio_recalc_state"

    id = Column(Integer, primary_key=True)
    generation = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="idle")
    mode = Column(String(16), nullable=False, default="snapshots")
    recalc_from = Column(Date, nullable=True)
    recalc_to = Column(Date, nullable=True)
    touched_symbols = Column(JSON, nullable=False, default=list)
    current_step = Column(String(64), nullable=True)
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
