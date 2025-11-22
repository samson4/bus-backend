# pydantic schemas

from datetime import datetime
from typing import List
from pydantic import BaseModel

class Tables(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    table_name: str
    schema_name: str
class TablesPaginatedResponse(BaseModel):
    data: List[Tables]
    total: int
    page: int
    limit: int



# class CreateTableInfo(BaseModel):
    """ Table(
            "mytable",
            metadata,
            Column("mytable_id", Integer, primary_key=True),
            Column("value", String(50)),
        )"""   
    # table_name: str
    # columns:List[Columns]
