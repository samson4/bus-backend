
from datetime import datetime
from pydantic import BaseModel


class Columns(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    column_name: str
    table_name: str