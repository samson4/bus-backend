from sqlalchemy import MetaData, Column, Table, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

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


class SchemaMetadata(UniqueIDMixin, TimeStampMixin, Base):
    __tablename__ = "bus_metadata"

    schema_name = Column(String(255))


class TableMetadata(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "table_metadata"
    table_name = Column(String)
    schema_name = Column(String)


class ColumnMetadata(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "column_metadata"
    column_name = Column(String)
    table_name = Column(String)


class UserModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_users"
    user_name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    disabled = Column(Boolean, default=False)
