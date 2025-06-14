from fastapi import Depends, FastAPI, HTTPException, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import create_engine, select, Table, MetaData
from sqlalchemy.orm import Session

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
    UserProjectsModel,
)
from src.db.schemas import SchemasPaginatedResponse, TablesPaginatedResponse
from src.db.users.userschemas import User, UserCreate, UserCreateResponse
from src.db.projects.projectschemas import (
    UserProjectResponse,
)

# from src.db.utils.decode import get_current_user
from src.db import DATABASE_URL
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
engine = create_engine(DATABASE_URL)
metadata_engine = create_engine("sqlite:///./metadata.db")
dialect = engine.dialect
dialct_name = metadata_engine.dialect
print(f"Connected database dialect: {dialect.name} {dialct_name.name}")

SchemaMetadata.metadata.create_all(bind=engine)
ColumnMetadata.metadata.create_all(bind=engine)
UserModel.metadata.create_all(bind=metadata_engine)
TableMetadata.metadata.create_all(bind=engine)


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


def insert_schema(
    session,
):
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

            schema_data = SchemaMetadata(schema_name=schema[0])
            internalSession.add(schema_data)
            internalSession.commit()
            internalSession.refresh(schema_data)
            insert_tables(session, schema[0], internalSession)

    # return schema_result


def insert_tables(session, schema, internalSession):

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

            insert_columns(session, table.table_name, schema, internalSession)
            # Insert table if it does not exist
        else:

            table_data = TableMetadata(
                table_name=table.table_name, schema_name=table.table_schema
            )
            internalSession.add(table_data)
            internalSession.commit()
            internalSession.refresh(table_data)
            insert_columns(session, table.table_name, schema, internalSession)


def insert_columns(session, table, schema, internalSession):

    #columns_metadata = select(ColumnMetadata)
    #columns_metadata_exists = internalSession.execute(columns_metadata).all()

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

@app.on_event("startup")
def insert_metadata():
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

                         insert_tables(session, schema[0], internalSession)
                     else:

                         schema_data = SchemaMetadata(
                             schema_name=schema[0]
                         )  # type:ignore
                         internalSession.add(schema_data)
                         internalSession.commit()
                         internalSession.refresh(schema_data)

                         insert_tables(session, schema[0], internalSession)
         else:
             insert_schema(session)


@app.get("/projects", response_model=List[UserProjectResponse])
def get_user_projects(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get all projects for the current user"""
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
        query = select(UserProjectsModel).where(UserProjectsModel.user_id == user_id)

        result = db.execute(query).scalars().all()
        return result
    except Exception as e:
        print("e", e)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("project/new")
def create_project(request: Request, form_data):
    pass


# API Routes
@app.get("/schemas/", response_model=SchemasPaginatedResponse)
def get_schemas(
    request: Request,
    schema_name: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=15, le=100),
    db: Session = Depends(get_db),
):
    # headers = request.headers
    # token = headers["authorization"].split(" ")[1]
    query = select(SchemaMetadata).limit(limit).order_by(SchemaMetadata.schema_name)
    # print(
    #    "dec",
    #    jwt.decode(
    #        token,
    #        SECRET_KEY,
    #        algorithms=["HS256"],
    #    ),
    # )
    total_query = db.query(SchemaMetadata).count()
    result = db.execute(query)
    return {
        "data": result.scalars().all(),
        "total": total_query,
        "page": (skip // limit) + 1,
        "limit": limit,
    }


@app.get("/tables/", response_model=TablesPaginatedResponse)
def get_tables(
    schema: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, le=100),
    db: Session = Depends(get_db),
):
    """Get all tables with schema filter"""

    query = (
        select(TableMetadata)
        .where(TableMetadata.schema_name == schema)
        .limit(limit)
        .offset(skip)
    )
    total_query = (
        db.query(TableMetadata).filter(TableMetadata.schema_name == schema).count()
    )
    result = db.execute(query)
    return {
        "data": result.scalars().all(),
        "total": total_query,
        "page": (skip // limit) + 1,
        "limit": limit,
    }


@app.get("/columns/")
def get_columns(table: str, limit: Optional[int] = 30, db: Session = Depends(get_db)):
    query = (
        select(ColumnMetadata).where(ColumnMetadata.table_name == table).limit(limit)
    )
    columns = db.execute(query)
    return columns.scalars().all()


@app.get("/data/")
def get_data(
    schema: str,
    table: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, le=100),
    db: Session = Depends(get_source_db),
):
    try:
        # Method 1: Using MetaData reflection
        metadata = MetaData(schema=schema)
        # Reflect only the specific table
        target_table = Table(table, metadata, autoload_with=db.bind)
        query = select(target_table).limit(limit).offset(skip)

        total_data = db.query(target_table).count()
        print("total_data", total_data)
        result = db.execute(query)
        return {
            "data": result.mappings().all(),
            "total": total_data,
            "page": (skip // limit) + 1,
            "limit": limit,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: User = Depends(get_current_active_user),
):
    return [{"item_id": "Foo", "owner": current_user.username}]


@app.get("/")
def read_root():
    return "Server is running"


if __name__ == "__main__":
    print("main")
