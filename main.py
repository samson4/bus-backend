from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    Query,
    BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import create_engine, select, Table, MetaData, and_,text
from sqlalchemy.orm import Session, joinedload

import jwt
from jwt.exceptions import InvalidTokenError as InvalidTokenError
from passlib.context import CryptContext

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


app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


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


def fake_decode_token(token):
    # This doesn't provide any security at all
    # Check the next version
    user = get_user(token)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
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
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def insert_schema(session):
    with Session(metadata_engine) as internalSession:
        schema_query = select(SchemaInfo.schema_name).where(
            SchemaInfo.schema_name.notin_(exclude_schemas)
        )
        schema_result = session.execute(schema_query).all()
        for schema in schema_result:

            # Check if schema already exists
            existing_schema = (
                internalSession.query(SchemaMetadata)
                .filter(SchemaMetadata.schema_name == schema[0])
                .first()
            )
            if existing_schema:

                continue

            schema_data = SchemaMetadata(schema_name=schema[0], project_id=1)
            internalSession.add(schema_data)
            internalSession.commit()
            internalSession.refresh(schema_data)
            asyncio.create_task(insert_tables(session, schema[0], internalSession))

    # return schema_result


async def insert_tables(session, schema, internalSession):
    print("insert_tables", schema)
    tables_query = select(TableInfo.table_name, TableInfo.table_schema).where(
        TableInfo.table_schema == schema
    )

    tables_result = session.execute(tables_query).all()
    for table in tables_result:

        # Check if table already exists
        existing_table = (
            internalSession.query(TableMetadata)
            .filter(
                TableMetadata.table_name == table.table_name,
                TableMetadata.schema_name == table.table_schema,
            )
            .first()
        )
        if existing_table:

            asyncio.create_task(
                insert_columns(session, table.table_name, schema, internalSession)
            )
            # Insert table if it does not exist
        else:

            table_data = TableMetadata(
                table_name=table.table_name, schema_name=table.table_schema
            )
            internalSession.add(table_data)
            internalSession.commit()
            internalSession.refresh(table_data)
            asyncio.create_task(
                insert_columns(session, table.table_name, schema, internalSession)
            )


async def insert_columns(session, table, schema, internalSession):

    columns_query = select(ColumnInfo.column_name, ColumnInfo.table_name).where(
        ColumnInfo.table_name == table
    )
    columns_result = session.execute(columns_query).all()
    for column in columns_result:

        # Check if column already exists
        existing_column = (
            internalSession.query(ColumnMetadata)
            .filter(
                ColumnMetadata.column_name == column.column_name,
                ColumnMetadata.table_name == column.table_name,
                ColumnMetadata.schema_name == schema,
            )
            .first()
        )
        if existing_column:

            continue

        column_data = ColumnMetadata(
            column_name=column.column_name,
            table_name=column.table_name,
            schema_name=schema,
        )
        internalSession.add(column_data)
        internalSession.commit()
        internalSession.refresh(column_data)

    # return columns_result


@app.middleware("http")
async def verify_token(request: Request, call_next):
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    if request.url.path in ["/token", "/register", "/docs", "/openapi.json", "/redoc"]:
        response = await call_next(request)
        return response
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )
    token = authorization.split(" ")[1]
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
        request.state.user = payload.get("bus")
        response = await call_next(request)
        return response
    except Exception as e:
        print("e", e)
        # raise HTTPException(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid token",
        # )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) 
        
           

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


# @app.on_event("startup")
async def insert_metadata():
    print("Inserting metadata on startup")
    with Session(engine) as session:
        if dialect.name == "mysql":

            schema_query = select(SchemaInfo.schema_name).where(
                SchemaInfo.schema_name == engine.url.database
            )

            schema_result = session.execute(schema_query).all()

            with Session(metadata_engine) as internalSession:

                for schema in schema_result:

                    # Check if schema already exists
                    existing_schema = (
                        internalSession.query(SchemaMetadata)
                        .filter(SchemaMetadata.schema_name == schema[0])
                        .first()
                    )
                    if existing_schema:
                        print("Schema already exists:")
                        asyncio.create_task(
                            insert_tables(session, schema[0], internalSession)
                        )
                    else:

                        schema_data = SchemaMetadata(
                            schema_name=schema[0],
                            project_id=1,
                        )  # type:ignore
                        internalSession.add(schema_data)
                        internalSession.commit()
                        internalSession.refresh(schema_data)

                        asyncio.create_task(
                            insert_tables(session, schema[0], internalSession)
                        )
        else:
            asyncio.create_task(insert_schema(session))


@app.get("/projects", response_model=List[UserProjectResponse])
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

        # Convert the project to the response model
        # project_details = UserProjectResponse(**project.__dict__)
        # print("project_details", project_details)

        # Generate a JWT token with project details
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
            }
        )
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


@app.get("/columns/")
def get_columns(table_id: str, limit: Optional[int] = 100, db: Session = Depends(get_db)):
    query = (
        select(ColumnMetadata).where(ColumnMetadata.table_id == table_id).limit(limit)
    )
    columns = db.execute(query)
    return columns.scalars().all()


@app.get("/data/")
def get_data(
    schema: str,
    table: str,
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, le=100),
    db: Session = Depends(get_db)
):
    try:
        print("config",config)
        user = request.state.user
        project = user.get("project")
        project_id = project.get("project_id")
        db_url_query = select(ProjectModel.db_connection_string).where(ProjectModel.id == project_id)
        db_url = db.execute(db_url_query).scalars().first()
        schema_query = select(SchemaMetadata.schema_name).where(and_(SchemaMetadata.project_id == project_id, SchemaMetadata.id == schema))
        schema_result = db.execute(schema_query).scalars().first()
        print("db_url", db_url)
        print("db_url_query", db_url_query)
        db_engine = create_engine(db_url)
        print("db_engine", db_engine)
        target_db = Session(db_engine)
        print("db", target_db)
        query = select(Table(table, MetaData(schema=schema_result), autoload_with=target_db.bind)).limit(limit).offset(skip)
        print("query", query)
        total_data = target_db.query(Table(table, MetaData(schema=schema_result), autoload_with=target_db.bind)).count()
        print("total_data", total_data)
        result = target_db.execute(query)
        
        return {
            "data": result.mappings().all(),
            "total": total_data,
            "page": (skip // limit) + 1,
            "limit": limit,
        }

    except Exception as e:
        print("e", e)
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
        result = target_db.execute(t)
        
        if result.returns_rows:
            print("result", result)
            # print("result.keys()", result.keys())
            # print("result.mappings().all()", result.mappings().all())
            return {
            "data": result.mappings().all(),
        }
        else:
            target_db.commit()
            return {"message": "Query executed successfully."}
        
    except Exception as e:
        print("e", e)
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/")
def read_root():
    return "Server is running"


if __name__ == "__main__":
    print("main")
