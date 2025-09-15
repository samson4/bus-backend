from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class Schemas(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    schema_name: str

    class Config:
        from_attributes = True


class Tables(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    table_name: str
    schema_name: str


class Columns(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    column_name: str
    table_name: str


# class SchemasResponse(BaseModel):
#     schemas: list[Schemas]
#     tables: list[Tables]
#     columns: list[Columns]


# Pydantic Models for API
# class JobBase(BaseModel):
#     title: str
#     description: str

# class JobCreate(JobBase):
#     pass

# class Job(JobBase):
#     id: int

#     class Config:
#         orm_mode = True


class TablesPaginatedResponse(BaseModel):
    data: List[Tables]
    total: int
    page: int
    limit: int


class SchemasPaginatedResponse(BaseModel):
    data: List[Schemas]
    total: int
    page: int
    limit: int

class ColumnCreate(BaseModel):
    column_name: str
    column_type: str
    length: int
    not_null: bool
    default_value: Optional[str] = None

class TableCreate(BaseModel):
    table_name: str
    columns : List[ColumnCreate]


# T = TypeVar("T", bound=BaseModel)


# class PaginatedResponse(BaseModel, Generic[T]):
#     items: List[T]
#     total: int
#     page: int
#     limit: int


# @app.get("/jobs/", response_model=PaginatedResponse)
# def list_jobs(
#     db: Session = Depends(get_db),
#     skip: int = Query(default=0, ge=0),
#     limit: int = Query(default=15, le=100),
# ):
#     query = db.query(Job)
#     total = query.count()
#     jobs = query.offset(skip).limit(limit).all()
#     return PaginatedResponse(items=jobs, total=total, page=(skip // limit) + 1, limit=limit)

