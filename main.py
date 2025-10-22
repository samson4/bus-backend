# import sentry_sdk
import functools
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse
from starlette.config import Config as StarletteConfig
from starlette.middleware.sessions import SessionMiddleware
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    Query,
    BackgroundTasks
)
from starlette.responses import JSONResponse,Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import create_engine, select, Table, MetaData, and_,text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func
import jwt
from jwt.exceptions import InvalidTokenError as InvalidTokenError, ExpiredSignatureError
from pwdlib import PasswordHash

from src import (
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    TableMetadata,
    ColumnMetadata,
    SchemaMetadata,
    UserModel,
    ProjectModel,
    UserProjectsModel,
)
from src.db.schemas import SchemasPaginatedResponse, TablesPaginatedResponse
from src.db.users.userschemas import User, UserCreate, UserCreateResponse
from src.db.projects.projectschemas import (
    ProjectBase,
    UserProjectResponse,
    UserProjects,
    ProjectCreate,
)
from src.db.config import config
import asyncio

# from src.db.utils.decode import get_current_user
from src.db import DATABASE_URL, metadata_engine, engine
from src.db.users.userschemas import oauth2_scheme, Token, TokenData
from decouple import config as decouple_config


SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = decouple_config("ACCESS_TOKEN_EXPIRE_MINUTES", 60)





# sentry_sdk.init(
#     dsn="https://468bde44cffcc512f0d29ff307249c19@o4510186579492864.ingest.us.sentry.io/4510186581721088",
#     # Add data like request headers and IP for users,
#     # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#     send_default_pii=True,
# )
app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key="!secret")
headers = {
     "WWW-Authenticate": "Bearer",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


startlet_config = StarletteConfig('.env')
oauth = OAuth(startlet_config)

CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

print("DATABASE_URL", DATABASE_URL)
engine = engine
metadata_engine = metadata_engine
dialect = engine.dialect
dialct_name = metadata_engine.dialect
print(f"Connected database dialect: {dialect.name} {dialct_name.name}")

# SchemaMetadata.metadata.create_all(bind=engine)
# ColumnMetadata.metadata.create_all(bind=engine)
UserModel.metadata.create_all(bind=metadata_engine)
# TableMetadata.metadata.create_all(bind=engine)


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


def get_db():
    db = Session(metadata_engine)
    try:
        yield db
    finally:
        db.close()


def get_source_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


password_hash = PasswordHash.recommended()

# @app.get("/sentry-debug")
# async def trigger_error():
#     division_by_zero = 1 / 0
#     return division_by_zero
def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def authenticate_user(username: str, password: str, db):
    user = get_user(username, db)
    if not user:
        return False
    if not verify_password(password, hashed_password=user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)
    to_encode.update({"iat": issued_at})
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(email: str, db):
    query = select(UserModel).where(UserModel.email == email).limit(1)

    result = db.execute(query)

    user = result.scalars().first()

    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("bus")

        if user is None:
            raise credentials_exception
        token_data = TokenData(email=user["email"])
    except ExpiredSignatureError:
        raise JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise credentials_exception
    
    user = get_user(email=token_data.email, db=db)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    if request.url.path in ["/token", "/register", "/google/login", "/auth" ,"/docs", "/openapi.json", "/redoc", "/sentry-debug"]:
        response = await call_next(request)
        return response
    authorization = request.headers.get("authorization")
    if not authorization:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=headers,
            content={"detail":"Authorization header is missing"},
        )
    
    try:
        token = authorization.split(" ")[1]
    except IndexError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=headers,
            content={"detail": "Invalid authorization header format. Expected 'Bearer <token>'"},
        )
    
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=headers,
            content={"detail":"Authorization token is missing"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        request.state.user = payload.get("bus")
        response = await call_next(request)
        return response

    except ExpiredSignatureError:
        # Return proper HTTP response for expired token
        return JSONResponse(
            content={"detail":"Token has expired"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            
           headers=headers
        )
    except InvalidTokenError:
        # Return proper HTTP response for invalid token
        return JSONResponse(
            content={"detail":"Invalid token"},
            status_code=status.HTTP_401_UNAUTHORIZED,
            
           headers=headers
        )
    except Exception as e:
        print("Unexpected error:", e)
        return JSONResponse(
            content={"detail":"An unexpected error occurred during token validation."},
            status_code=500,
            headers=headers,

        )


@app.get("/google/login")
async def google_login(request: Request):
    try:
        redirect_uri = "http://127.0.0.1:8000/auth"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print("e", e)
@app.get("/google/auth")
async def google_auth(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token.get('userinfo')
        print("user", user) 
        if user:
            request.session['user'] = dict(user)
        return RedirectResponse(url='/')

    except Exception as e:
        print("e", e)
        return JSONResponse(content={"error": "Authentication failed"}, status_code=400)
@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={
            "sub": user.id,
            "bus": {
                "user_id": user.id,
                "username": user.user_name,
                "email": user.email,
                "disabled": user.disabled,
            },
        },
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/register", response_model=UserCreateResponse)
async def register(
    request: Request,
    form_data: UserCreate,
    db: Session = Depends(get_db),
):
    # user_data = User(form_data)

    user = get_user(form_data.email, db)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )
    hashed_password = get_password_hash(form_data.password)
    user_data = UserModel(
        user_name=form_data.email,
        email=form_data.email,
        password=hashed_password,
    )
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    user = UserCreateResponse(
        id=user_data.id,
        email=user_data.email,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )

    return user_data


@app.get("/projects/", response_model=List[UserProjectResponse])
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


@app.post("/project/new", response_model=UserProjectResponse)
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
        if config.adapter:
            config.adapter.close_connection()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/project/select/{project_id}")
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
        get_engine(project.project.db_connection_string)
        return {"project_token": access_token}
    except Exception as e:
        print("e", e)
        raise HTTPException(status_code=400, detail=str(e))
        
        
    

# API Routes
@app.get("/schemas/", response_model=SchemasPaginatedResponse)
def get_schemas(
    request: Request,
    schema_name: Optional[str] = None,
    
    skip: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=15, le=100),
    db: Session = Depends(get_db),
):
    user = request.state.user
    project = user.get("project")
    project_id = project.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not selected",
        )
    print(f"Debug: project_id={project_id}")  # Log the project_id for debugging
    query = select(SchemaMetadata).where(SchemaMetadata.project_id == project_id).limit(limit).order_by(SchemaMetadata.schema_name)
    print(f"Debug: query={query}")  # Log the query for debugging
  
    print("query", query)
    total_query = db.query(SchemaMetadata).filter(SchemaMetadata.project_id == project_id).count()
    result = db.execute(query)
    return {
        "data": result.scalars().all(),
        "total": total_query,
        "page": (skip // limit) + 1,
        "limit": limit,
    }


@app.get("/tables/", response_model=TablesPaginatedResponse)
def get_tables(
    schema_id: str,
    request: Request,
    search_query: Optional[str] = "",
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, le=100),
    db: Session = Depends(get_db),
):
    """Get all tables with schema filter"""
    user = request.state.user
    project = user.get("project")
    project_id = project.get("project_id")
    query = (
        select(TableMetadata).join(SchemaMetadata, TableMetadata.schema_name == SchemaMetadata.schema_name)
        .where(
            and_(
                SchemaMetadata.project_id == project_id,
                TableMetadata.schema_id == schema_id,
                TableMetadata.table_name.contains(search_query, autoescape=True), 
            )
        )
        .limit(limit)
        .offset(skip)
    )
    print("query", query)
    total_query = (
        db.query(TableMetadata)
        .filter(
            and_(
                TableMetadata.schema_id == schema_id,
                TableMetadata.table_name.contains(search_query, autoescape=True),
            )
        )
        .count()
    )
    result = db.execute(query)
    return {
        "data": result.scalars().all(),
        "total": total_query,
        "page": (skip // limit) + 1,
        "limit": limit,
    }

@functools.lru_cache(maxsize=32)
@app.get("/columns/")
def get_columns(table_id: str, limit: Optional[int] = 100, db: Session = Depends(get_db)):
    query = (
        select(ColumnMetadata).where(ColumnMetadata.table_id == table_id).limit(limit)
    )
    columns = db.execute(query)
    return columns.scalars().all()


@functools.lru_cache(maxsize=32)
def get_engine(db_url: str):
    """
    Creates and caches a SQLAlchemy engine for a given database URL.
    We are NOT using NullPool here, so it will use the default QueuePool.
    """
    print(f"--- CREATING NEW ENGINE for {db_url} ---")
    #TODO: Consider adding pool_size and max_overflow parameters based on expected load
    return create_engine(db_url) 

# Cache for table metadata
# The key will be a tuple: (db_url, schema_name, table_name)
@functools.lru_cache(maxsize=128)
def get_table(db_url: str, schema_name: str, table_name: str) -> Table:
    """
    Reflects and caches a Table object.
    The db_url is part of the key to ensure we cache per-database.
    """
    print(f"--- REFLECTING NEW TABLE {schema_name}.{table_name} ---")
    engine = get_engine(db_url) # This will be fast (from cache)
    metadata = MetaData()
    # Autoload the table structure ONCE
    table = Table(
        table_name, 
        metadata, 
        schema=schema_name, 
        autoload_with=engine
    )
    return table

@app.get("/data/")
async def get_data(
    schema: str,
    table: str,
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, le=100),
    db: Session = Depends(get_db) # This is your PRIMARY app database
):
    try:
        
        start_time = datetime.now()
        print("start", start_time)
        user = request.state.user
        project = user.get("project")
        project_id = project.get("project_id")
        
      
        db_url_query = select(ProjectModel.db_connection_string).where(ProjectModel.id == project_id)
        db_url = db.execute(db_url_query).scalars().first()
        
        schema_query = select(SchemaMetadata.schema_name).where(and_(SchemaMetadata.project_id == project_id, SchemaMetadata.id == schema))
        schema_result = db.execute(schema_query).scalars().first()

        if not db_url or not schema_result:
            raise HTTPException(status_code=404, detail="Project or schema not found.")

        target_engine = get_engine(db_url)

       
        target_table = get_table(db_url, schema_result, table)

        #TODO: Figure out why I cannot use dependency injection for target_db and why this persists connection
        with Session(target_engine) as target_db:
            
            
            query = select(target_table).limit(limit).offset(skip)
            
            
            total_query = select(func.count()).select_from(target_table)

            
            total_data = target_db.execute(total_query).scalar_one()
            result = target_db.execute(query)
            
            
            
            return {
                "data": result.mappings().all(),
                "total": total_data,
                "time_taken": (datetime.now() - start_time).total_seconds(),
                "page": (skip // limit) + 1,
                "limit": limit,
            }

    except Exception as e:
        print("e", e)
        # Handle specific exceptions if possible (e.g., table not found)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/table/new")
def create_new_table(
    request:Request,
    
    db: Session = Depends(get_db)
):
    """Endpoint for creating new table in the corresponding database
     e.g.::

        mytable = Table(
            "mytable",
            metadata,
            Column("mytable_id", Integer, primary_key=True),
            Column("value", String(50)),
        )
    """
    user = request.state.user
    project = user.get("project")
    project_id = project.get("project_id")
    db_url_query = select(ProjectModel.db_connection_string).where(ProjectModel.id == project_id)
    db_url = db.execute(db_url_query).scalars().first()
    db_engine = create_engine(db_url)
    print("db_engine", db_engine)
    target_db = Session(db_engine)
    print("db", target_db)
    Table(

    )
    pass

@app.post("/query/execute")
def execute_query(
    query:dict,
    request:Request,
    db: Session = Depends(get_db)
):
    """Endpoint for executing arbitrary SQL queries on the selected project database"""
    

    try:
        start_time = datetime.now()
        user = request.state.user
        print("user", user)
        project = user.get("project")
        project_id = project.get("project_id")
        db_url_query = select(ProjectModel.db_connection_string).where(ProjectModel.id == project_id)
        db_url = db.execute(db_url_query).scalars().first()
        db_engine = create_engine(db_url)
        print("db_engine", db_engine)
        target_db = Session(db_engine)
        print("db", target_db)
        query_str = query.get("query")
        print("query", query_str)
        if not query_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or empty 'query' parameter.",
            )
        t = text(query_str)
        print("start",datetime.now())
        result = target_db.execute(t)
        print("end",datetime.now())
        if result.returns_rows:
            return {
            "data": result.mappings().all(),
            "time_taken": (datetime.now() - start_time).total_seconds(),
        }
        else:
            target_db.commit()
            return {"message": "Query executed successfully.", "time_taken": (datetime.now() - start_time).total_seconds()}
        
    except Exception as e:
        print("e", e)
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/")
def read_root():
    return "Server is running"


if __name__ == "__main__":
    print("main")
    print("main")
