from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_mixin
from datetime import datetime


@declarative_mixin
class TimeStampMixin:
    """
    Mixin to add a timestamp to a SQLAlchemy model.
    """

    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(),
        nullable=False,
    )
