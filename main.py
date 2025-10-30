# import sentry_sdk
import functools
from starlette.middleware.sessions import SessionMiddleware
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    Query,
    
)
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import  Optional

from sqlalchemy import create_engine, select, Table, MetaData, and_,text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import jwt
from jwt.exceptions import InvalidTokenError as InvalidTokenError, ExpiredSignatureError

# from src import (
   
    # ColumnMetadata,
    
    # ProjectModel
# )

from src.models import Base, ColumnMetadata
from src.schema import TableMetadata, SchemaMetadata
# from src.db.schemas.models import SchemaMetadata
# from src.db.schemas import SchemasPaginatedResponse, TablesPaginatedResponse
from src.db.schemas.schemas import SchemasPaginatedResponse

from src.db.tables.schemas import TablesPaginatedResponse


# from src.users.models import UserModel
from src.projects.models import ProjectModel
# from src.db.utils.decode import get_current_user
from src.db import metadata_engine, engine
from src.projects.router import project_router
from src.auth.router import auth_router
from src.users.router import user_router
from decouple import config as decouple_config


SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")


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






Base.metadata.create_all(bind=metadata_engine)
# UserModel.metadata.create_all(bind=metadata_engine)
# ProjectModel.metadata.create_all(bind=metadata_engine)

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


@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    if request.url.path in ["/token", "/register", "/google/login", "/auth" ,"/docs", "/openapi.json", "/redoc", "/sentry-debug", "/project"]:
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

@app.get("/columns/")
def get_columns(table_id: str, limit: Optional[int] = 100, db: Session = Depends(get_db)):
    query = (
        select(ColumnMetadata).where(ColumnMetadata.table_id == table_id).limit(limit)
    )
    columns = db.execute(query)
    return columns.scalars().all()


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


app.include_router(project_router)
app.include_router(auth_router)
app.include_router(user_router)

if __name__ == "__main__":
    print("main")
