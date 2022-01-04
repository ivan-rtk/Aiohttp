import hashlib
from datetime import datetime
import json

from module_dotenv import db_dsn
from app import config

import asyncio
import aiopg as aiopg
from aiohttp import web
from gino import Gino
from asyncpg.exceptions import UniqueViolationError


db = Gino()
app = web.Application()
routes = web.RouteTableDef()


class BaseModel:

    @classmethod
    async def get_or_404(cls, obj_id):
        instance = await cls.get(obj_id)
        if instance:
            return instance
        raise web.HTTPNotFound(text='данного ID нет в базе')

    @classmethod
    async def create_instance(cls, **kwargs):
        try:
            instance = await cls.create(**kwargs)
        except UniqueViolationError:
            raise web.HTTPBadRequest()
        return instance


class User(db.Model, BaseModel):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    _idx1 = db.Index('users_user_email', 'email', unique=True)

    def __str__(self):
        return '<User {}>'.format(self.username)

    def __repr__(self):
        return str(self)

    @classmethod
    async def create_instance(cls, **kwargs):
        kwargs['password'] = hashlib.md5(kwargs['password'].encode()).hexdigest()
        return await super().create_instance(**kwargs)

    def check_password(self, raw_password: str):
        raw_password = f'{raw_password}{config.SALT}'
        return self.password == hashlib.md5(raw_password.encode()).hexdigest()

    def to_dict(self):
        user_data = super().to_dict()
        user_data.pop('password')
        return user_data


class Ad(db.Model, BaseModel):

    __tablename__ = 'advertisements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    _idx1 = db.Index('advertisements_ad_title', 'title', unique=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': str(self.created_at),
            'creator_id': self.creator_id,
        }

    def __str__(self):
        return '<Advertisment {}>'.format(self.title)

    def __repr__(self):
        return str(self)


async def set_connection():
    return await db.set_bind(db_dsn)


async def disconnect():
    return await db.pop_bind().close()


async def pg_pool(app):
    async with aiopg.create_pool(db_dsn) as pool:
        app['pg_pool'] = pool
        yield
        pool.close()


async def orm_engine(app):
    app['db'] = db
    await set_connection()
    await db.gino.create_all()
    yield
    await disconnect()


class UserView(web.View):

    async def get(self):
        user_id = int(self.request.match_info['user_id'])
        user = await User.get_or_404(user_id)
        return web.json_response(user.to_dict())

    async def post(self):
        data = await self.request.json()
        user = await User.create_instance(**data)
        return web.json_response(user.to_dict())


class AdView(web.View):

    async def get(self):
        ad_id = int(self.request.match_info['ad_id'])
        ad = await Ad.get_or_404(ad_id)
        return web.json_response(ad.to_dict())

    async def post(self):
        data = await self.request.json()
        ad = await Ad.create_instance(**data)
        return web.json_response(ad.to_dict())

    async def delete(self):
        ad_id = int(self.request.match_info['ad_id'])
        instance = await Ad.get_or_404(ad_id)
        await instance.delete()
        return web.Response(text=f'Ad {instance} was deleted')


@routes.get('/health')
async def health(request):
    pool = request.app['pg_pool']
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute('SELECT 1')
            data = await cursor.fetchall()
            return web.Response(body=json.dumps({'data': data}))


app.cleanup_ctx.append(orm_engine)
app.cleanup_ctx.append(pg_pool)

app.add_routes([
    web.get('/users/{user_id:\d+}', UserView),
    web.post('/users', UserView),
    web.get('/ads/{ad_id:\d+}', AdView),
    web.post('/ads', AdView),
    web.delete('/ads/{ad_id:\d+}', AdView),
     ])

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
web.run_app(app, port=8088)
