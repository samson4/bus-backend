from typing import List
from sqlalchemy import (
    MetaData,
    Column,
    Table,
    String,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship

from .db.mixins import UniqueIDMixin, TimeStampMixin

Base = declarative_base()
meta = MetaData(schema="information_schema")
tablemeta = MetaData()


class TableInfo(Base):
    __table__ = Table(
        "tables",
        meta,
        Column("table_catalog", String, primary_key=True),
        Column("table_schema", String, primary_key=True),
        Column("table_name", String, primary_key=True),
        Column("table_type", String),
        Column("self_referencing_column_name", String),
        Column("reference_generation", String),
        Column("user_defined_type_catalog", String),
        Column("user_defined_type_schema", String),
        Column("user_defined_type_name", String),
        Column("is_insertable_into", String),
        Column("is_typed", String),
        Column("commit_action", String),
        extend_existing=True,
    )


class ColumnInfo(Base):
    __table__ = Table(
        "columns",
        meta,
        Column("table_catalog", String, primary_key=True),
        Column("table_schema", String, primary_key=True),
        Column("table_name", String, primary_key=True),
        Column("column_name", String, primary_key=True),
        Column("ordinal_position", Integer),
        Column("column_default", String),
        Column("is_nullable", String),
        Column("data_type", String),
        Column("character_maximum_length", Integer),
        Column("character_octet_length", Integer),
        Column("numeric_precision", Integer),
        Column("numeric_precision_radix", Integer),
        Column("numeric_scale", Integer),
        Column("datetime_precision", Integer),
        Column("interval_type", String),
        Column("interval_precision", Integer),
        Column("character_set_catalog", String),
        Column("character_set_schema", String),
        Column("character_set_name", String),
        Column("collation_catalog", String),
        Column("collation_schema", String),
        Column("collation_name", String),
        Column("domain_catalog", String),
        Column("domain_schema", String),
        Column("domain_name", String),
        Column("udt_catalog", String),
        Column("udt_schema", String),
        Column("udt_name", String),
        Column("scope_catalog", String),
        Column("scope_schema", String),
        Column("scope_name", String),
        Column("maximum_cardinality", Integer),
        Column("dtd_identifier", String),
        Column("is_self_referencing", String),
        Column("is_identity", String),
        Column("identity_generation", String),
        Column("identity_start", String),
        Column("identity_increment", String),
        Column("identity_maximum", String),
        Column("identity_minimum", String),
        Column("identity_cycle", String),
        Column("is_generated", String),
        Column("generation_expression", String),
        Column("is_updatable", String),
        extend_existing=True,
    )


class SchemaInfo(Base):
    __table__ = Table(
        "schemata",
        meta,
        Column("catalog_name", String, primary_key=True),
        Column("schema_name", String, primary_key=True),
        Column("schema_owner", String, primary_key=True),
        Column("default_character_set_catalog", String, primary_key=True),
        Column("default_character_set_schema", String),
        Column("default_character_set_name", String),
        extend_existing=True,
    )


# class SchemaMetadata(UniqueIDMixin, TimeStampMixin, Base):
#     __tablename__ = "bus_metadata"

#     schema_name = Column(String(255))
#     project_id = Column(String(255), nullable=False)
#     tables: Mapped[List["TableMetadata"]] = relationship(
#         back_populates="schema", cascade="all, delete-orphan"
#     )


# class TableMetadata(Base, UniqueIDMixin, TimeStampMixin):
#     __tablename__ = "table_metadata"
#     table_name = Column(String(255))
#     schema_name = Column(String(255))
#     schema_id = Column(String(255), ForeignKey("bus_metadata.id"), nullable=False)
#     schema: Mapped["SchemaMetadata"] = relationship(back_populates="tables")
    # UniqueConstraint(
    #     table_name, schema_name, name="table_name_schema_name_unique_constraint"
    # )


class ColumnMetadata(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "column_metadata"
    column_name = Column(String(255))
    table_name = Column(String(255))
    table_id = Column(String(255), ForeignKey("table_metadata.id"), nullable=False)
    schema_name = Column(String(255))
    schema_id = Column(String(255), ForeignKey("bus_metadata.id"), nullable=False)


class UserModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_users"
    user_name = Column(String(255))
    email = Column(String(255), unique=True)
    password = Column(String(255))
    disabled = Column(Boolean, default=False)


class ProjectModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_projects"
    project_name = Column(String(255), nullable=False)
    db_connection_string = Column(String(255), nullable=False)
    created_by = Column(
        String(255),
        ForeignKey("bus_users.id"),
        nullable=False,
    )
    user_projects = relationship("UserProjectsModel", back_populates="project")


class UserProjectsModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_user_projects"
    project_id = Column(
        String(255),
        ForeignKey("bus_projects.id"),
        nullable=False,
    )
    user_id = Column(String(255), ForeignKey("bus_users.id"), nullable=False)
    project = relationship("ProjectModel", back_populates="user_projects")
    user = relationship("UserModel")


# UserProjects response example
# [
#     {
#         "id": "ee5c83a-2a88-4b95-a3ea-f4e473768ec3\n",
#         "project_id": "bd2ce824-8331-4955-9647-175cb543d93c",
#         "user_id": "58beeae3-24e9-4f63-81a5-d57b7f1dde04"
#         "created_at": "2023-10-01T12:00:00Z",
#         "updated_at": "2023-10-01T12:00:00Z"
#         "project": {
#             "id": "bd2ce824-8331-4955-9647-175cb543d93c",
#             "project_name": "Sample Project",
#             "db_connection_string": "postgresql://user:password@localhost/dbname",
#             "created_by": "58beeae3-24e9-4f63-81a5-d57b7f1dde04",
#             "created_at": "2023-10-01T12:00:00Z",
#             "updated_at": "2023-10-01T12:00:00Z"
#         },
#     },
# ]
