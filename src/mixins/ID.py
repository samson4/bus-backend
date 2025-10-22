from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_mixin
import uuid


@declarative_mixin
class UniqueIDMixin:
    """
    Mixin to add a unique ID to a SQLAlchemy model.
    """

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))

