from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    Query,
    BackgroundTasks
)
from fastapi import APIRouter
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from starlette.config import Config as StarletteConfig
from authlib.integrations.starlette_client import OAuth
from src.users.models import UserModel
from src.db import metadata_engine, engine


import jwt

from .schemas import Token, UserCreateResponse, User, UserCreate
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from decouple import config as decouple_config

auth_router = APIRouter()
password_hash = PasswordHash.recommended()


ACCESS_TOKEN_EXPIRE_MINUTES = decouple_config("ACCESS_TOKEN_EXPIRE_MINUTES", 360)
SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")


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

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    user = get_user(username, db)
    if not user:
        return False
    if not verify_password(password, hashed_password=user.password):
        return False
    return user


def get_password_hash(password):
    return password_hash.hash(password)


async def get_db():
    db = Session(metadata_engine)
    try:
        yield db
    finally:
        db.close()


def get_user(email: str, db):
    query = select(UserModel).where(UserModel.email == email).limit(1)

    result = db.execute(query)

    user = result.scalars().first()

    return user

@auth_router.post("/register", response_model=UserCreateResponse)
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



@auth_router.post("/token")
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



@auth_router.get("/google/login")
async def google_login(request: Request):
    try:
        redirect_uri = "http://127.0.0.1:8000/auth"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print("e", e)
@auth_router.get("/google/auth")
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