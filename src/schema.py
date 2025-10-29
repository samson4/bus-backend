# sqlalchemy models
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from src.mixins import UniqueIDMixin, TimeStampMixin
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List
Base = declarative_base()
class TableMetadata(Base, UniqueIDMixin, TimeStampMixin):
    # from src.db.schemas.models import SchemaMetadata
    __tablename__ = "table_metadata"
    table_name = Column(String(255))
    schema_name = Column(String(255))
    schema_id = Column(String(255), ForeignKey("bus_metadata.id"), nullable=False)
    schema: Mapped["SchemaMetadata"] = relationship(back_populates="tables")
    UniqueConstraint(
        table_name, schema_name, name="table_name_schema_name_unique_constraint"
    )

# # sqlalchemy models

# from sqlalchemy import Column, String
# from src.mixins import UniqueIDMixin, TimeStampMixin
# from sqlalchemy.orm import Mapped, relationship
# from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
class SchemaMetadata(UniqueIDMixin, TimeStampMixin, Base):
    # from src.db.tables.models import TableMetadata
    __tablename__ = "bus_metadata"

    schema_name = Column(String(255))
    project_id = Column(String(255), nullable=False)
    tables: Mapped[List["TableMetadata"]] = relationship(
        back_populates="schema", cascade="all, delete-orphan"
    )    