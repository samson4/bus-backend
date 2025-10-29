#pydantic schemas

from datetime import datetime
from typing import List
from pydantic import BaseModel

class Schemas(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    schema_name: str

    class Config:
        from_attributes = True
class SchemasPaginatedResponse(BaseModel):
    data: List[Schemas]
    total: int
    page: int
    limit: int