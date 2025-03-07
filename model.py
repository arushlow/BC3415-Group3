from peewee import (
    AutoField,
    SqliteDatabase,
    Model,
    CharField,
    IntegerField,
    ForeignKeyField,
)

database = SqliteDatabase("fintwin.db")


class BaseModel(Model):
    class Meta:
        database = database


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()


class Investment(BaseModel):
    user = ForeignKeyField(User, backref="investments")
    # TODO: Other investment fields


class ChatHistory(BaseModel):
    user = ForeignKeyField(User, backref="chats")
    chat_id = IntegerField()
    message_id = AutoField()
    message = CharField()

    class Meta:
        indexes = (
            (("user", "chat_id"), False),
        )


def create_tables():
    with database:
        database.create_tables([User, Investment, ChatHistory])
