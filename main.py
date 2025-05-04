import uuid
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, select, text, Table, MetaData
from sqlalchemy.orm import Session

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
)
from src.db.users.userschemas import User

# from src.db.utils.decode import get_current_user
from src.db import Schemas, Tables, Columns
from src.db import DATABASE_URL
from src.db.users.userschemas import oauth2_scheme, Token, TokenData


SECRET_KEY = "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


app = FastAPI()
origins = ["*"]
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("DATABASE_URL", DATABASE_URL)
engine = create_engine(DATABASE_URL)

# if not engine.dialect.has_table(engine, 'bus_metadata'):
TableMetadata.metadata.create_all(bind=engine)
ColumnMetadata.metadata.create_all(bind=engine)
SchemaMetadata.metadata.create_all(bind=engine)


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


print("quiero", select(SchemaInfo.schema_name))


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}


def fake_hash_password(password: str):
    return "fakehashed" + password


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def fake_decode_token(token):
    # This doesn't provide any security at all
    # Check the next version
    user = get_user(fake_users_db, token)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def fake_decode_token(token):
    return User(
        username=token + "fakedecoded", email="john@example.com", full_name="John Doe"
    )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


with Session(engine) as session:
    print("schemastart", datetime.utcnow())
    metadata = select(SchemaMetadata)
    metadata_exists = session.execute(metadata).all()
    print(
        "metadata_exists",
        len(metadata_exists),
    )
    if len(metadata_exists) == 0:
        schema_query = select(SchemaInfo.schema_name)
        schema_result = session.execute(schema_query).all()
        for schema in schema_result:
            schema_data = SchemaMetadata(schema_name=schema[0])
            session.add(schema_data)
            session.commit()
            session.refresh(schema_data)
    print("schemaend", datetime.utcnow())
    print("tablestart", datetime.utcnow())
    tables_metadata = select(TableMetadata)
    table_metadata_exists = session.execute(tables_metadata).all()
    print("table_metadata_exists", len(table_metadata_exists))
    if len(table_metadata_exists) == 0:
        tables_query = select(TableInfo.table_name, TableInfo.table_schema)
        tables_result = session.execute(tables_query).all()
        for table in tables_result:
            table_data = TableMetadata(
                table_name=table.table_name, schema_name=table.table_schema
            )
            session.add(table_data)
            session.commit()
            session.refresh(table_data)
    print("tableend", datetime.utcnow())
    print("columnstart", datetime.utcnow())
    columns_metadata = select(ColumnMetadata)
    columns_metadata_exists = session.execute(columns_metadata).all()
    print("columns_metadata_exists", len(columns_metadata_exists))
    if len(columns_metadata_exists) == 0:
        columns_query = select(ColumnInfo.column_name, ColumnInfo.table_name)
        columns_result = session.execute(columns_query).all()
        for column in columns_result:
            column_data = ColumnMetadata(
                column_name=column.column_name, table_name=column.table_name
            )
            session.add(column_data)
            session.commit()
            session.refresh(column_data)
    print("columnend", datetime.utcnow())


# API Routes
@app.get("/schemas/", response_model=List[Schemas])
def get_schemas(
    schema_name: Optional[str] = None,
    limit: Optional[int] = 15,
    db: Session = Depends(get_db),
):
    query = select(SchemaMetadata).limit(limit).order_by(SchemaMetadata.schema_name)
    print("query", query)
    result = db.execute(query)
    return result.scalars().all()


@app.get("/tables/")
def get_tables(schema: str, limit: Optional[int] = 15, db: Session = Depends(get_db)):
    """Get all tables with schema filter"""
    query = (
        select(TableMetadata).where(TableMetadata.schema_name == schema).limit(limit)
    )
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


@app.get("/templates", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = Depends(oauth2_scheme)):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "menu_items": [
                {"name": "Dashboard", "icon": "home", "url": "/"},
                {"name": "Analytics", "icon": "bar-chart", "url": "/analytics"},
                {"name": "Users", "icon": "users", "url": "/users"},
                {"name": "Settings", "icon": "settings", "url": "/settings"},
            ],
        },
    )


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
