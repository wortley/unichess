from time import time

import jwt
from app.config import JWT_SECRET

ALGORITHM = "HS256"
EXPIRE_DELTA = 43200  # 12 hours


def decode_token(enc_token: bytes):
    dec_token = jwt.decode(enc_token, JWT_SECRET, algorithms=[ALGORITHM])
    if dec_token["exp"] < time():  # check if token has expired
        raise jwt.ExpiredSignatureError()
    return int(dec_token["sub"])  # return user ID


def create_token(uid: int, username: str):
    enc_token = jwt.encode({"sub": str(uid), "username": username, "exp": time() + EXPIRE_DELTA}, JWT_SECRET, algorithm=ALGORITHM)
    return enc_token
