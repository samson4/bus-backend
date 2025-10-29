#sqlalchemy models
from sqlalchemy import Column,String,Boolean


from sqlalchemy.ext.declarative import declarative_base


from src.mixins import UniqueIDMixin, TimeStampMixin


Base = declarative_base()
class UserModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_users"
    user_name = Column(String(255))
    email = Column(String(255), unique=True)
    password = Column(String(255))
    disabled = Column(Boolean, default=False)