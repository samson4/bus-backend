# sqlalchemy models
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from src.mixins import UniqueIDMixin, TimeStampMixin
from sqlalchemy.orm import Mapped, relationship
from typing import List
# reuse the project's shared Base so all models share the same MetaData
from src.models import Base

class TableMetadata(Base, UniqueIDMixin, TimeStampMixin):
    # from src.db.schemas.models import SchemaMetadata
    __tablename__ = "table_metadata"
    table_name = Column(String(255))
    schema_name = Column(String(255))
    schema_id = Column(String(255), ForeignKey("bus_metadata.id"), nullable=False)
    schema: Mapped["SchemaMetadata"] = relationship(
        "SchemaMetadata", back_populates="tables"
    )
    # __table_args__ = (
    #     UniqueConstraint(
    #         "table_name", "schema_name", name="table_name_schema_name_unique_constraint"
    #     ),
    # )

class SchemaMetadata(Base, UniqueIDMixin, TimeStampMixin):
    # from src.db.tables.models import TableMetadata
    __tablename__ = "bus_metadata"

    schema_name = Column(String(255))
    project_id = Column(String(255), nullable=False)
    tables: Mapped[List["TableMetadata"]] = relationship(
        back_populates="schema", cascade="all, delete-orphan"
    )    