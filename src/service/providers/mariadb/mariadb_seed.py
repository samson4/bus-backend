
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select, Table, MetaData, and_
from fastapi import (
    Depends,
)

exclude_schemas = [
    "information_schema",
    "pg_catalog",
    "pg_internal",
    "pg_temp_1",
    "pg_toast_temp_1",
    "pg_toast",
    "sys",
    "sys_temp_1",
]
exclude_tables = [
    "pg_statistic",
    "pg_type",
    "pg_attribute",
    "pg_constraint",
    "pg_index",
    "pg_class",
    "pg_namespace",
    "pg_proc",
    "pg_settings",
    "pg_tablespace",
]


class Seed:
    def __init__(self, project_id, adapter):
        from ....db.config import metadata_engine

        self.adapter = adapter
        # self.metadata_engine = session.connection
        self.project_id = project_id
        self.db = None
        self.source_db = None
        self.metadata_engine = metadata_engine
        print(" project_id, adapter", project_id, adapter.dialect.name)

    def get_db(self, metadata_engine):
        self.db = Session(metadata_engine)
        try:
            yield self.db
        finally:
            self.db.close()

    def get_source_db(self, engine):
        self.source_db = Session(engine)
        try:
            yield self.source_db
        finally:
            self.source_db.close()

    async def insert_columns(self,source_db, table, schema, db):
        from src.models import ColumnInfo, ColumnMetadata
        try:
            print("insert_columns", table, schema)
            columns_query = select(ColumnInfo.column_name, ColumnInfo.table_name).where(
                ColumnInfo.table_name == table.table_name,
            )
            print("columns_query", columns_query)
            columns_result = source_db.execute(columns_query).all()
            print("columns_result", columns_result)
            for column in columns_result:
                # Check if column already exists
                existing_column = (
                    db.query(ColumnMetadata)
                    .filter(
                        ColumnMetadata.column_name == column.column_name,
                        ColumnMetadata.table_name == column.table_name,
                        ColumnMetadata.schema_name == schema.schema_name,
                    )
                ).first()
                print("existing_column:", existing_column)
                if existing_column:
                    continue
                else:
                    print("Inserting column:")
                    column_data = ColumnMetadata(
                        column_name=column.column_name,
                        table_name=column.table_name,
                        schema_name=schema.schema_name,
                        table_id=table.id,
                        schema_id=schema.id,
                    )
                    db.add(column_data)
                    db.commit()
                    db.refresh(column_data)
        except Exception as e:
            print("Error in insert_columns:", e)
    async def insert_schema(self, source_db, db):
        from src.models import SchemaInfo
        from src.schema import SchemaMetadata
        # from src.db.schemas import Schemas
        try:
            print("insert_schema")
            # with Session(self.metadata_engine) as internalSession:
            schema_query = select(SchemaInfo.schema_name).where(
                SchemaInfo.schema_name.notin_(exclude_schemas)
            )
            schema_result = source_db.execute(schema_query).all()
            print("schema_result", schema_result)
            for schema in schema_result:
                
                # Check if schema already exists
                existing_schema = (
                    db.query(SchemaMetadata)
                    .filter(SchemaMetadata.schema_name == schema[0], SchemaMetadata.project_id == self.project_id)
                    .first()
                )
                print("existing_schema:",(existing_schema))
                if existing_schema:
                    print("Schema already exists:",schema[0])

                    continue

                schema_data = SchemaMetadata(schema_name=schema[0], project_id=self.project_id)
                print("schema_data", schema_data)
                db.add(schema_data)
                db.commit()
                db.refresh(schema_data)
                asyncio.create_task(self.insert_tables(source_db, schema_data, db))
        except Exception as e:
            print("Error in insert_schema:", e)
    async def insert_tables(self, source_db, schema_data, db):
        from src.models import TableInfo
        from src.schema import TableMetadata

        print("insert_tables", schema_data)
        tables_query = select(TableInfo.table_name, TableInfo.table_schema).where(
            TableInfo.table_schema == schema_data.schema_name,
        )

        tables_result = source_db.execute(tables_query).all()
        for table in tables_result:
            # Check if table already exists
            existing_table = (
                db.query(TableMetadata)
                .filter(
                    TableMetadata.table_name == table.table_name,
                    TableMetadata.schema_name == table.table_schema,
                    TableMetadata.schema_id == schema_data.id,
                )
                .first()
            )
            print("existing_table:", existing_table)
            # table_data = TableMetadata(
            #     table_name=existing_table.table_name, schema_name=existing_table.schema_name)
            if existing_table:
                asyncio.create_task(
                    self.insert_columns(source_db, existing_table, schema_data, db)
                )
                # Insert table if it does not exist
            else:
                table_data = TableMetadata(
                    table_name=table.table_name, 
                    schema_name=table.table_schema,
                    schema_id=schema_data.id
                )
                db.add(table_data)
                db.commit()
                db.refresh(table_data)
                
                await self.insert_columns(source_db, table_data, schema_data, db)
                

    def insert_metadata(self):
        print("Inserting metadata on startup")
        print("self.adapter", self.adapter.url.database)
        # db:Session = self.get_db(metadata_engine)
        # source_db:Session = self.get_source_db(self.adapter)
        with Session(self.metadata_engine) as db, Session(self.adapter) as source_db:
            
            from src.models import SchemaInfo
            from src.schema import SchemaMetadata

            schema_query = select(SchemaInfo.schema_name).where(
                SchemaInfo.schema_name == self.adapter.url.database
            )
            schema_result = source_db.execute(schema_query).all()
            for schema in schema_result:
                print("schema", schema[0])
                # Check if schema already exists in
                existing_schema = (
                    db.query(SchemaMetadata)
                    .filter(
                        and_(
                            SchemaMetadata.schema_name == schema[0],
                            SchemaMetadata.project_id == self.project_id,
                        )
                    )
                    .first()
                )
                if existing_schema:
                    print("Schema already exists:")
                    asyncio.create_task(
                        self.insert_tables(source_db, existing_schema, db)
                    )
                else:
                    schema_data = SchemaMetadata(
                        schema_name=schema[0],
                        project_id=self.project_id,
                    )  # type:ignore
                    db.add(schema_data)
                    db.commit()
                    db.refresh(schema_data)

                    asyncio.run(
                        self.insert_tables(source_db, schema_data, db)
                    )
            
