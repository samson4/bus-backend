from pydantic import BaseModel
from datetime import datetime
from fastapi.security import OAuth2PasswordBearer
from src.db.users.userschemas import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class ProjectBase(BaseModel):
    """Base Project model."""

    id: str
    project_name: str
    db_connection_string: str
    created_by: str

    class Config:
        orm_mode = True

class ProjectCreate(BaseModel):
    """Model for creating a new project."""

    project_name: str
    db_connection_string: str
    database_dialect: str

    class Config:
        from_attributes = True
        orm_mode = True
class UserProjects(BaseModel):
    id: str
    project_id: str
    user_id: str

    class Config:
        from_attributes = True
        orm_mode = True


class UserProjectResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    project: ProjectBase
    user: User

    class Config:
        from_attributes = True
        orm_mode = True
