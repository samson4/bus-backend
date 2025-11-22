

import datetime
from typing import List

from fastapi import BackgroundTasks, Depends, status, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import create_engine
from fastapi import APIRouter
import functools

from src.projects.schemas import UserProjectResponse,ProjectCreate



from .models import ProjectModel, UserProjectsModel
from src.db.config import config

from src.db import metadata_engine, engine
from decouple import config as decouple_config
import jwt
from datetime import timedelta, timezone

SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = decouple_config("ACCESS_TOKEN_EXPIRE_MINUTES", 360)


project_router = APIRouter()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    issued_at = datetime.datetime.now(timezone.utc)
    to_encode.update({"iat": issued_at})
    if expires_delta:
        expire = datetime.datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(timezone.utc) + timedelta(minutes=60)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@functools.lru_cache(maxsize=32)
def get_engine(db_url: str):
    """
    Creates and caches a SQLAlchemy engine for a given database URL.
    We are NOT using NullPool here, so it will use the default QueuePool.
    """
    print(f"--- CREATING NEW ENGINE for {db_url} ---")
    #TODO: Consider adding pool_size and max_overflow parameters based on expected load
    return create_engine(db_url) 

async def get_db():
    db = Session(metadata_engine)
    try:
        yield db
    finally:
        db.close()


async def get_source_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


@project_router.get("/project/{project_id}", response_model=UserProjectResponse)
def get_project_by_id(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get a project by its ID for the current user"""
    try:
        user_id = request.state.user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        query = select(UserProjectsModel).where(
            UserProjectsModel.project_id == project_id,
            UserProjectsModel.user_id == user_id,
        )

        result = db.execute(query).scalars().first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return result
    except Exception as e:
        print("Exception occurred:", e)  # Log the full exception server-side
        raise HTTPException(status_code=400, detail="An unexpected error occurred. Please contact support.")

@project_router.get("/projects/", response_model=List[UserProjectResponse])
def get_user_projects(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get all projects for the current user"""
    
    try:
        user_id = request.state.user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        query = select(UserProjectsModel).where(UserProjectsModel.user_id == user_id)

        result = db.execute(query).scalars().all()
        return result
    except Exception as e:
        print("Exception occurred:", e)  # Log the full exception server-side
        raise HTTPException(status_code=400, detail="An unexpected error occurred. Please contact support.")


@project_router.post("/project/new", response_model=UserProjectResponse)
def create_project(
    request: Request, 
    form_data: ProjectCreate, 
     background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # print("proj",form_data.db_connection_string)
    """Create a new project for the current user"""
    headers = request.headers
    token = headers.get("authorization", "").split(" ")[1]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        config.set_config(
            form_data.db_connection_string, form_data.database_dialect
        )
        db_connection_string  = config.adapter.get_connection_string()

        print("db_connection_string", db_connection_string)
        if not db_connection_string:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid database connection string",
            )
        engine = get_engine(db_connection_string)
        # Test the connection
        with Session(engine) as test_db:
            query = text("SELECT 1")
            data = test_db.execute(query).scalar_one()
            if data != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to connect to the provided database.",
                )
            else:
                print("Successfully connected to the provided database.")
        new_project = ProjectModel(
            project_name=form_data.project_name,
            db_connection_string=db_connection_string,
            created_by=user_id,
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        new_user_project = UserProjectsModel(
            project_id=new_project.id,
            user_id=user_id,
        )
        db.add(new_user_project)
        db.commit()
        db.refresh(new_user_project)
        config.adapter.create_connection()
        config.adapter.get_connection_string
        background_tasks.add_task(config.adapter.initialize_metadata,project_id=new_project.id)
        return new_user_project
    except Exception as e:
        print("e", e)
        db.rollback()
        if config.adapter:
            config.adapter.close_connection()
        raise HTTPException(status_code=400, detail=str(e))


@project_router.get("/project/select/{project_id}")
def select_project(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
):
    """Select a project and set the database connection to the project's database"""
   
    try:
        # Get the user ID from the JWT token
        token = request.headers.get("authorization", "").split(" ")[1]
        user_id = request.state.user.get("user_id")
        decoded_token= jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Query the project with relationships
        project_query = (
            select(UserProjectsModel)
            .options(joinedload(UserProjectsModel.project), joinedload(UserProjectsModel.user))
            .where(
                UserProjectsModel.project_id == project_id,
                UserProjectsModel.user_id == user_id,
            )
        )

        project = db.execute(project_query).scalars().first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        print("project", project.project.db_connection_string)

        # Generate a JWT token with project details
        access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
        access_token = create_access_token(
            data={
                "sub": decoded_token.get("sub"),
                "bus": {
                    "user_id": decoded_token.get("bus")["user_id"],
                    "username": decoded_token.get("bus")["username"],
                    "email": decoded_token.get("bus")["email"],
                    "disabled": decoded_token.get("bus")["disabled"],
                    "project": {
                        "project_id": project.project.id,
                        "project_name": project.project.project_name,
                    },
                },
            },
            expires_delta=access_token_expires,
        )
        engine = get_engine(project.project.db_connection_string)
        with Session(engine) as target_db:
            
            
            query = text("SELECT 1")
            data = target_db.execute(query).scalar_one()
            print("data", data)
            if data != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to connect to the project's database.",
                )
            else:
                print("Successfully connected to the project's database.")
                return {"project_token": access_token}
    except Exception as e:
        print("e", e)
        raise HTTPException(status_code=400, detail=str(e))
        
    