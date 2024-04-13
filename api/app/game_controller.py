import asyncio
import json
import os
import random
import uuid
from logging import Logger
from time import time_ns
from typing import Tuple

import app.utils as utils
from aioredis import RedisError
from aioredis.client import Redis
from app.config import BROADCAST_KEY, MAX_EMIT_RETRIES, TimeConstants
from app.exceptions import CustomException
from app.game_registry import GameRegistry
from app.models import Colour, Event, Game
from app.rate_limit import RateLimitConfig
from app.rmq import RMQConnectionManager
from chess import Board
from socketio.asyncio_server import AsyncServer


class GameController:

    def __init__(self, rmq: RMQConnectionManager, redis_client: Redis, sio: AsyncServer, gr: GameRegistry, logger: Logger):
        self.rmq = rmq
        self.redis_client = redis_client
        self.sio = sio
        self.gr = gr
        self.logger = logger

    def _on_emit_done(self, task, event, sid, attempts):
        try:
            task.result()  #  raises exception if task failed
        except Exception as e:
            if attempts < MAX_EMIT_RETRIES:
                self.logger.error(f"Emit event failed with exception: {e}, retrying...")
                new_task = asyncio.create_task(self.sio.emit(event.name, event.data, to=sid))
                new_task.add_done_callback(lambda t, sid=sid: self._on_emit_done(t, event, sid, attempts + 1))
            else:
                self.logger.error(f"Emit event failed {MAX_EMIT_RETRIES} times, giving up")

    async def init_listener(self, gid, sid):
        self.logger.info("Initialising listener for game " + gid + ", user " + sid + ", on worker ID " + str(os.getpid()))

        def on_message(_, __, ___, body):
            message = json.loads(body)
            event = Event(**message)
            task = asyncio.create_task(self.sio.emit(event.name, event.data, to=sid))
            task.add_done_callback(lambda t, sid=sid: self._on_emit_done(t, event, sid, 1))

        self.gr.add_game_ctag(gid, self.rmq.channel.basic_consume(queue=utils.get_queue_name(gid, sid), on_message_callback=on_message, auto_ack=True))

    async def get_game_by_gid(self, gid, sid) -> Game:
        """Get game state from redis by game ID"""
        try:
            game = utils.deserialise_game_state(await self.redis_client.get(utils.get_redis_key(gid)))
        except RedisError as exc:
            raise CustomException(f"Redis error: {exc}", sid)
        if not game:
            raise CustomException("Game not found", sid)
        return game

    async def get_game_by_sid(self, sid) -> Tuple[Game, str]:
        """Get game state from redis by player ID"""
        gid = self.gr.get_gid(sid)
        game = await self.get_game_by_gid(gid, sid)
        return game, gid

    async def save_game(self, gid, game, _):
        """Save game state in Redis"""
        try:
            await self.redis_client.set(utils.get_redis_key(gid), utils.serialise_game_state(game))
        except RedisError as exc:
            raise CustomException(f"Redis error: {exc}", emit_local=False, gid=gid)

    async def create(self, sid, time_control):
        gid = str(uuid.uuid4())
        self.sio.enter_room(sid, gid)  # create a room for the game

        games_inpr = 0
        async for _ in self.redis_client.scan_iter("game:*"):  # count games in progress
            games_inpr += 1
        if games_inpr > RateLimitConfig.CONCURRENT_GAME_LIMIT:
            raise CustomException("Server concurrent game limit reached. Please try again later", sid)

        tr = time_control * TimeConstants.MILLISECONDS_PER_MINUTE
        game = Game(
            players=[sid],
            board=Board(),
            tr_w=tr,
            tr_b=tr,
            turn_start_time=-1,
            time_control=time_control,
        )

        self.gr.add_player_gid_record(sid, gid)
        await self.save_game(gid, game, sid)

        # send game id to client
        await self.sio.emit("gameId", gid, to=sid)  # N.B no need to publish this to MQ

        # create fanout exchange for game
        self.rmq.channel.exchange_declare(exchange=gid, exchange_type="topic")
        # create player 1 queue
        self.rmq.channel.queue_declare(queue=utils.get_queue_name(gid, sid))
        # bind the queue to the game exchange
        self.rmq.channel.queue_bind(exchange=gid, queue=utils.get_queue_name(gid, sid), routing_key=sid)
        self.rmq.channel.queue_bind(exchange=gid, queue=utils.get_queue_name(gid, sid), routing_key=BROADCAST_KEY)

        # init listener
        await self.init_listener(gid, sid)

    async def join(self, sid, gid):
        game = await self.get_game_by_gid(gid, sid)
        if len(game.players) > 1:
            raise CustomException("This game already has two players", sid)

        self.sio.enter_room(sid, gid)  # join room
        game.players.append(sid)

        self.gr.add_player_gid_record(sid, gid)

        random.shuffle(game.players)  # randomly pick white and black

        game.turn_start_time = time_ns() / 1_000_000  # reset turn start time

        await self.save_game(gid, game, sid)

        # create player 2 queue
        self.rmq.channel.queue_declare(queue=utils.get_queue_name(gid, sid))
        # bind the queue to the game exchange
        self.rmq.channel.queue_bind(exchange=gid, queue=utils.get_queue_name(gid, sid), routing_key=sid)
        self.rmq.channel.queue_bind(exchange=gid, queue=utils.get_queue_name(gid, sid), routing_key=BROADCAST_KEY)

        await self.init_listener(gid, sid)

        await utils.publish_event(
            self.rmq.channel,
            gid,
            Event(
                "start",
                {"colour": Colour.WHITE.value[0], "timeRemaining": game.tr_w},
            ),
            game.players[0],
        )
        await utils.publish_event(
            self.rmq.channel,
            gid,
            Event(
                "start",
                {"colour": Colour.BLACK.value[0], "timeRemaining": game.tr_b},
            ),
            game.players[1],
        )

    async def offer_rematch(self, sid):
        game, gid = await self.get_game_by_sid(sid)
        if game:
            await utils.publish_event(self.rmq.channel, gid, Event("rematchOffer", 1), next(p for p in game.players if p != sid))

    async def accept_rematch(self, sid):
        # TODO: check that player has actually been offered rematch
        game, gid = await self.get_game_by_sid(sid)
        game.board.reset()
        game.players.reverse()  # switch white and black
        game.tr_w = game.tr_b = TimeConstants.MILLISECONDS_PER_MINUTE * game.time_control
        game.turn_start_time = time_ns() / 1_000_000

        await self.save_game(gid, game, sid)

        await utils.publish_event(
            self.rmq.channel,
            gid,
            Event(
                "start",
                {"colour": Colour.WHITE.value[0], "timeRemaining": game.tr_w},
            ),
            game.players[0],
        )

        await utils.publish_event(
            self.rmq.channel,
            gid,
            Event(
                "start",
                {"colour": Colour.BLACK.value[0], "timeRemaining": game.tr_b},
            ),
            game.players[1],
        )

    async def clear_game(self, sid):
        """Clears a user's game(s) from memory"""
        if not self.gr.get_gid(sid):
            # if player already removed from game or game deleted, return
            return

        game, gid = await self.get_game_by_sid(sid)

        self.gr.remove_player_gid_record(sid)
        self.rmq.channel.queue_unbind(utils.get_queue_name(gid, sid), exchange=gid, routing_key=sid)
        self.rmq.channel.queue_unbind(utils.get_queue_name(gid, sid), exchange=gid, routing_key=BROADCAST_KEY)

        if len(game.players) > 1:  # remove player from game.players
            game.players.remove(sid)
            await self.save_game(gid, game, sid)
        else:  # last player to leave game
            for ctag in self.gr.get_game_ctags(gid):
                self.rmq.channel.basic_cancel(consumer_tag=ctag)
            self.gr.remove_all_game_ctags(gid)
            self.rmq.channel.exchange_delete(exchange=gid)
            await self.redis_client.delete(utils.get_redis_key(gid))
