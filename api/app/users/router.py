from typing import Annotated

from app.db import engine, get_db
from app.users import controller, models, schemas
from fastapi import APIRouter, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

models.Base.metadata.create_all(bind=engine)


router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_db)])


@router.post("/login", status_code=HTTP_200_OK, response_model=schemas.Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    return controller.login(db, form_data)


@router.post("/", status_code=HTTP_201_CREATED, response_model=schemas.Token)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return controller.create_user(db, user)


@router.get("/me", status_code=HTTP_200_OK, response_model=schemas.User)
def get_user_me(user: Annotated[schemas.User, Depends(controller.get_current_user)]):
    return user


@router.put("/me", status_code=HTTP_200_OK, response_model=schemas.User)
async def update_user(updates: schemas.UserUpdate, user: Annotated[schemas.User, Depends(controller.get_current_user)], db: Session = Depends(get_db)):
    return controller.update_user(db, user, updates)


@router.delete("/me", status_code=HTTP_204_NO_CONTENT)
async def delete_user(user: Annotated[schemas.User, Depends(controller.get_current_user)], db: Session = Depends(get_db)):
    return controller.delete_user(db, user)
