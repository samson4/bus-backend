#sqlalchemy models
from typing import List
from sqlalchemy import (
    MetaData,
    Column,
    Table,
    String,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship

from src.mixins import UniqueIDMixin, TimeStampMixin
# from src.users.models import UserModel
Base = declarative_base()
meta = MetaData(schema="information_schema")
tablemeta = MetaData()


#TODO 1: Move UserModel to a users module(Also figure out why importing it from users/models.py raises Mapper error)
class UserModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_users"
    user_name = Column(String(255))
    email = Column(String(255), unique=True)
    password = Column(String(255))
    disabled = Column(Boolean, default=False)


class ProjectModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_projects"
    project_name = Column(String(255), nullable=False)
    db_connection_string = Column(String(255), nullable=False)
    created_by = Column(
        String(255),
        ForeignKey("bus_users.id"),
        nullable=False,
    )
    user_projects = relationship("UserProjectsModel", back_populates="project")


class UserProjectsModel(Base, UniqueIDMixin, TimeStampMixin):
    __tablename__ = "bus_user_projects"
    project_id = Column(
        String(255),
        ForeignKey("bus_projects.id"),
        nullable=False,
    )
    user_id = Column(String(255), ForeignKey("bus_users.id"), nullable=False)
    project = relationship("ProjectModel", back_populates="user_projects")
    user = relationship("UserModel")  # Change this to a string reference