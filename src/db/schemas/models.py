# # sqlalchemy models
# from typing import List
# from sqlalchemy import Column, String
# from src.mixins import UniqueIDMixin, TimeStampMixin
# from sqlalchemy.orm import Mapped, relationship
# from sqlalchemy.ext.declarative import declarative_base


# Base = declarative_base()
# class SchemaMetadata(UniqueIDMixin, TimeStampMixin, Base):
#     from src.db.tables.models import TableMetadata
#     __tablename__ = "bus_metadata"

#     schema_name = Column(String(255))
#     project_id = Column(String(255), nullable=False)
#     tables: Mapped[List["TableMetadata"]] = relationship(
#         back_populates="schema", cascade="all, delete-orphan"
#     )