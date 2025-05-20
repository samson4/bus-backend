from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import create_engine, select, Table, MetaData
from sqlalchemy.orm import Session, aliased

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from src import (
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    TableMetadata,
    ColumnMetadata,
    SchemaMetadata,
    UserModel,
)
from src.db.users.userschemas import User, UserCreate, UserCreateResponse

# from src.db.utils.decode import get_current_user
from src.db import Schemas
from src.db import DATABASE_URL
from src.db.users.userschemas import oauth2_scheme, Token, TokenData
from decouple import config as decouple_config

SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = decouple_config("ACCESS_TOKEN_EXPIRE_MINUTES", 30)


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
dialect = engine.dialect
print(f"Connected database dialect: {dialect.name}")

SchemaMetadata.metadata.create_all(bind=engine)
ColumnMetadata.metadata.create_all(bind=engine)
UserModel.metadata.create_all(bind=engine)
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(email: str, db):
    query = select(UserModel).where(UserModel.email == email).limit(1)
    print("result123", query)
    result = db.execute(query)
    print("res", result)
    user = result.scalars().first()
    print("UserModel(**result)", user)
    # if user:
    #     print("UserModel(**user)", UserModel(user))
    # return User(**user)
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
        print("bus", user)
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
    print("schemastart", datetime.utcnow())
    metadata = select(SchemaMetadata)
    metadata_exists = session.execute(metadata).all()
    print(
        "metadata_exists",
        len(metadata_exists),
    )
    if len(metadata_exists) == 0:
        schema_query = select(SchemaInfo.schema_name).where(
            SchemaInfo.schema_name.notin_(exclude_schemas)
        )
        schema_result = session.execute(schema_query).all()
        for schema in schema_result:
            schema_data = SchemaMetadata(schema_name=schema[0])
            session.add(schema_data)
            session.commit()
            session.refresh(schema_data)
            insert_tables(session, schema[0])
    print("schemaend", datetime.utcnow())
    # return schema_result


def insert_tables(session, schema: str = None):
    print("tablestart", datetime.utcnow())
    tables_metadata = select(TableMetadata)
    table_metadata_exists = session.execute(tables_metadata).all()
    print("table_metadata_exists", len(table_metadata_exists))
    if len(table_metadata_exists) == 0:
        tables_query = select(TableInfo.table_name, TableInfo.table_schema).where(
            TableInfo.table_schema == schema
        )
        print("tables_query", tables_query)
        tables_result = session.execute(tables_query).all()
        for table in tables_result:
            table_data = TableMetadata(
                table_name=table.table_name, schema_name=table.table_schema
            )
            session.add(table_data)
            session.commit()
            session.refresh(table_data)
            insert_columns(session, table.table_name)
    print("tableend", datetime.utcnow())
    # return tables_result


def insert_columns(session, table: str = None):
    print("columnstart", datetime.utcnow())
    columns_metadata = select(ColumnMetadata)
    columns_metadata_exists = session.execute(columns_metadata).all()
    print("columns_metadata_exists", len(columns_metadata_exists))
    if len(columns_metadata_exists) == 0:
        columns_query = select(ColumnInfo.column_name, ColumnInfo.table_name).where(
            ColumnInfo.table_name == table
        )
        columns_result = session.execute(columns_query).all()
        for column in columns_result:
            column_data = ColumnMetadata(
                column_name=column.column_name, table_name=column.table_name
            )
            session.add(column_data)
            session.commit()
            session.refresh(column_data)
    print("columnend", datetime.utcnow())
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
    print("form_data", form_data)
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
    print("user_data", user_data)

    return user_data


with Session(engine) as session:
    if dialect.name == "mysql":
        print("edb", engine.url.database)

        schema_query = select(SchemaInfo.schema_name).where(
            SchemaInfo.schema_name == engine.url.database
        )
        print("schema_query", schema_query)

        schema_result = session.execute(schema_query).all()

        print("schema_result", schema_result)
        if len(schema_result) == 0:
            for schema in schema_result:
                schema_data = SchemaMetadata(schema_name=schema[0])
                session.add(schema_data)
                session.commit()
                session.refresh(schema_data)
                insert_tables(session, schema[0])
    else:
        insert_schema(session)


# API Routes
@app.get("/schemas/", response_model=List[Schemas])
def get_schemas(
    request: Request,
    schema_name: Optional[str] = None,
    limit: Optional[int] = 15,
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

    print("query", query)
    result = db.execute(query)
    return result.scalars().all()


@app.get("/tables/")
def get_tables(schema: str, limit: Optional[int] = 15, db: Session = Depends(get_db)):
    """Get all tables with schema filter"""
    BusMetadataAlias = aliased(SchemaMetadata)
    query = (
        select(TableMetadata, BusMetadataAlias)
        .join(
            BusMetadataAlias, TableMetadata.schema_name == BusMetadataAlias.schema_name
        )
        .where(TableMetadata.schema_name == schema)
        .limit(limit)
    )
    print("gen", query)
    result = db.execute(query)
    return result.scalars().all()


@app.get("/columns/")
def get_columns(table: str, limit: Optional[int] = 15, db: Session = Depends(get_db)):
    query = (
        select(ColumnMetadata).where(ColumnMetadata.table_name == table).limit(limit)
    )
    columns = db.execute(query)
    return columns.scalars().all()


@app.get("/data/")
def get_data(
    schema: str, table: str, limit: Optional[int] = 15, db: Session = Depends(get_db)
):
    try:
        # Method 1: Using MetaData reflection
        metadata = MetaData(schema=schema)
        # Reflect only the specific table
        target_table = Table(table, metadata, autoload_with=db.bind)
        query = select(target_table).limit(limit)
        result = db.execute(query)
        return result.mappings().all()

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


if __name__ == "__main__":
    print("main")
