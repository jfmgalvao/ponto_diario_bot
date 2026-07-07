import os
from datetime import datetime
import pytz
from peewee import Model, CharField, DateTimeField, PostgresqlDatabase

DB_HOST = os.getenv("HOST", "localhost")
DB_USER = os.getenv("USER_DB", "postgres")
DB_PASS = os.getenv("PSW_DB", "root")
DB_NAME = os.getenv("DATABASE", "postgres")
DB_PORT = int(os.getenv("DB_PORT", 5432))

db = PostgresqlDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)

def get_now_sp():
    return datetime.now(pytz.timezone('America/Sao_Paulo'))

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    telegram_id = CharField(unique=True)
    nome = CharField()
    empresa = CharField()
    created_at = DateTimeField(default=get_now_sp)

class Ponto(BaseModel):
    telegram_id = CharField()
    empresa = CharField()
    tipo = CharField() # 'entrada' ou 'saida'
    data_hora = DateTimeField(default=get_now_sp)

def init_db():
    db.connect()
    db.create_tables([User, Ponto])
    db.close()
