from typing import Annotated

import bcrypt
import jwt
from app.db import get_db
from app.users import auth, models, schemas
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    try:
        uid = auth.decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token has expired", headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    except (KeyError, TypeError):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Could not validate token", headers={"WWW-Authenticate": "Bearer"})

    return get_user_by_id(db, uid)


def login(db: Session, form_data: OAuth2PasswordRequestForm):
    db_user = get_user_by_username(db, form_data.username)
    if db_user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    if not bcrypt.checkpw(form_data.password.encode(), db_user.hashed_password):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    return schemas.Token(access_token=auth.create_token(db_user.id, db_user.username), token_type="bearer")


def get_user_by_id(db: Session, uid: int):
    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    user_exists = get_user_by_username(db, user.username)
    if user_exists:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Username already taken")

    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return schemas.Token(access_token=auth.create_token(db_user.id, db_user.username), token_type="bearer")


def update_user(db: Session, user: schemas.User, updates: schemas.UserUpdate):
    update_data = updates.model_dump(exclude_defaults=True)

    if "password" in update_data:
        hashed_password = bcrypt.hashpw(update_data["password"].encode(), bcrypt.gensalt())
        update_data["hashed_password"] = hashed_password
        del update_data["password"]

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: schemas.User):
    db.delete(user)
    db.commit()
