import logging
from contextlib import asynccontextmanager

import aioredis
import app.users.router as users_router
from app.config import CLOUDAMQP_URL, REDIS_URL
from app.exceptions import SocketIOExceptionHandler
from app.game_controller import GameController
from app.game_registry import GameRegistry
from app.log_formatter import custom_formatter
from app.play_controller import PlayController
from app.rate_limit import TokenBucketRateLimiter
from app.rmq import RMQConnectionManager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager

# logging config (override uvicorn default)
logger = logging.getLogger("uvicorn")
logger.handlers[0].setFormatter(custom_formatter)

# game registry
gr = GameRegistry()

# connection token bucket (rate limiting)
rate_limiter = TokenBucketRateLimiter()

# Redis client and MQ setup
redis_client = aioredis.Redis.from_url(REDIS_URL)

# RabbitMQ connection manager (pika)
rmq = RMQConnectionManager(CLOUDAMQP_URL, logger)


@asynccontextmanager
async def lifespan(_):
    """Handles startup/shutdown"""
    # Start token refiller
    rate_limiter.start_refiller()

    yield

    # Clean up before shutdown
    rate_limiter.stop_refiller()
    gr.clear()  # clear game registry
    if rmq.channel is not None and rmq.channel.is_open:  # close MQ
        rmq.channel.close()
    async for key in redis_client.scan_iter("game:*"):  # clear all games from redis cache
        await redis_client.delete(key)
    await redis_client.close()  # close redis connection


# Create FastAPI app instance
chess_api = FastAPI(lifespan=lifespan)

chess_api.include_router(users_router.router)

chess_api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://unichess.netlify.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socket_manager = SocketManager(app=chess_api)

# Game controller
gc = GameController(rmq, redis_client, chess_api.sio, gr, logger)

# Play (in game events) controller
pc = PlayController(rmq, gc)

# Global exception handler for controller methods
sioexc = SocketIOExceptionHandler(chess_api.sio, rmq, logger)

# Connect/disconnect handlers


@chess_api.sio.on("connect")
async def connect(sid, _):
    if rate_limiter.consume_token():
        logger.info(f"Client {sid} connected")
    else:
        await chess_api.sio.emit("error", "Connection limit exceeded", to=sid)
        logger.warning(f"Connection limit exceeded. Disconnecting {sid}")
        await chess_api.sio.disconnect(sid)


@chess_api.sio.on("disconnect")
async def disconnect(sid):
    await gc.clear_game(sid)
    logger.info(f"Client {sid} disconnected")


# Game management event handlers


@chess_api.sio.on("create")
@sioexc.sio_exception_handler
async def create(sid, time_control):
    await gc.create(sid, time_control)


@chess_api.sio.on("join")
@sioexc.sio_exception_handler
async def join(sid, gid):
    await gc.join(sid, gid)


# In-game event handlers


@chess_api.sio.on("move")
@sioexc.sio_exception_handler
async def move(sid, uci):
    await pc.move(sid, uci)


@chess_api.sio.on("offerDraw")
@sioexc.sio_exception_handler
async def offer_draw(sid):
    await pc.offer_draw(sid)


@chess_api.sio.on("acceptDraw")
@sioexc.sio_exception_handler
async def accept_draw(sid):
    await pc.accept_draw(sid)


@chess_api.sio.on("resign")
@sioexc.sio_exception_handler
async def resign(sid):
    await pc.resign(sid)


# NOTE: flag means run out of clock time


@chess_api.sio.on("flag")
@sioexc.sio_exception_handler
async def flag(sid, flagged):
    await pc.flag(sid, flagged)


# Rematch (game management)


@chess_api.sio.on("offerRematch")
@sioexc.sio_exception_handler
async def offer_rematch(sid):
    await gc.offer_rematch(sid)


@chess_api.sio.on("acceptRematch")
@sioexc.sio_exception_handler
async def accept_rematch(sid):
    await gc.accept_rematch(sid)


# Exit game handler


@chess_api.sio.on("exit")
@sioexc.sio_exception_handler
async def exit(sid):
    """When a client exits the game/match, clear it from game registry and cache"""
    await gc.clear_game(sid)
