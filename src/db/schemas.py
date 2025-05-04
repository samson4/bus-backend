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
