import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL")
CLOUDAMQP_URL = os.environ.get("CLOUDAMQP_URL")
JWT_SECRET = os.environ.get("JWT_SECRET")

MAX_EMIT_RETRIES = 5
BROADCAST_KEY = "all"


class TimeConstants:
    DECISECONDS_PER_MINUTE = 600
    MILLISECONDS_PER_MINUTE = 60000
