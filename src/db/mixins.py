from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_mixin
from datetime import datetime
import uuid

@declarative_mixin
class UniqueIDMixin:
    """
    Mixin to add a unique ID to a SQLAlchemy model.
    """
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


@declarative_mixin
class TimeStampMixin:
    """
    Mixin to add a timestamp to a SQLAlchemy model.
    """
    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow(), nullable=False,)    