
#TODO 2)chage this import from projects to users once TODO 1 is done
from src.projects.schemas import User
from fastapi import APIRouter, Depends ,status, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.projects.models import UserModel


from src.auth.schemas import TokenData,Token

from decouple import config as decouple_config

from src.db import metadata_engine
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = decouple_config(
    "SECRET_KEY", "90ded69acb971f4f6f9a6913428503503eac012275cd9f2b13c37a0ba43f35c6"
)
ALGORITHM = decouple_config("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = decouple_config("ACCESS_TOKEN_EXPIRE_MINUTES", 360)

user_router = APIRouter()
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
    except jwt.ExpiredSignatureError:
        raise JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
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