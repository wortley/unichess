from app.db import SessionLocal, engine
from app.users import controller, models, schemas
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# TODO: use alembic for table creation and migrations
models.Base.metadata.create_all(bind=engine)


def get_db():
    """Access DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_db)])


@router.get("/me")
async def get_user_me():
    pass


@router.get("/{uid}")
def get_user(uid: int, db: Session = Depends(get_db)):
    user = controller.get_user(db, uid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_exists = controller.get_user_by_email(db, email=user.email)
    if user_exists:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    return controller.create_user(db=db, user=user)


@router.put("/{uid}")
async def update_user(uid: int):
    pass


@router.delete("/{uid}")
async def delete_user(uid: int):
    pass
