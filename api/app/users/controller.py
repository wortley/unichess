from app.users import models, schemas
from sqlalchemy.orm import Session


def get_user(db: Session, uid: int):
    return db.query(models.User).filter(models.User.id == uid).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user: schemas.User):
    pass


def delete_user(db: Session, uid: int):
    pass
