from typing import Annotated

from app.db import get_db
from app.users import controller, schemas
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_db)])


@router.post("/login", status_code=HTTP_200_OK, response_model=schemas.Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    return await controller.login(db, form_data)


@router.post("/", status_code=HTTP_201_CREATED, response_model=schemas.Token)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await controller.create_user(db, user)


@router.get("/me", status_code=HTTP_200_OK, response_model=schemas.User)
async def get_user_me(user: Annotated[schemas.User, Depends(controller.get_current_user)]):
    return user


@router.put("/me", status_code=HTTP_200_OK, response_model=schemas.User)
async def update_user(updates: schemas.UserUpdate, user: Annotated[schemas.User, Depends(controller.get_current_user)], db: AsyncSession = Depends(get_db)):
    return await controller.update_user(db, user, updates)


@router.delete("/me", status_code=HTTP_204_NO_CONTENT)
async def delete_user(user: Annotated[schemas.User, Depends(controller.get_current_user)], db: AsyncSession = Depends(get_db)):
    await controller.delete_user(db, user)
