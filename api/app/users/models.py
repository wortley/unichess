from app.db import Base
from sqlalchemy import Column, Integer, String

# SQLAlchemy models


class UserTable(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
