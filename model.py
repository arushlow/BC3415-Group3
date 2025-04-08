from peewee import (
    AutoField,
    DateTimeField,
    SqliteDatabase,
    Model,
    CharField,
    UUIDField,
    ForeignKeyField,
    DecimalField,
    IntegerField,
    DateField
)

database = SqliteDatabase("fintwin.db", pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 64,
    'foreign_keys': 1,
    'synchronous': 1,
    'busy_timeout': 20000
})


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
    chat_id = UUIDField()
    chat_title = CharField()
    message_id = AutoField()
    message = CharField()
    created_at = DateTimeField()
    
    class Meta:
        indexes = (
            (("user", "chat_id"), False),
        )
    
class DataOverview(BaseModel):
    user = ForeignKeyField(User, backref="overview")
    account_id = IntegerField()
    bank_name = CharField()
    bank_name_short = CharField()
    account_type = CharField()
    balance = DecimalField(decimal_places=2)
    
class DataTransaction(BaseModel):
    transaction_id = AutoField()
    user = ForeignKeyField(User, backref="transaction")
    bank_account_id = ForeignKeyField(DataOverview, backref="transaction")
    date = DateField()
    description = CharField()
    amount = DecimalField(decimal_places=2)
    
class DataInvestment(BaseModel):
    user = ForeignKeyField(User, backref="invest")
    name = CharField()
    ticker = CharField()
    invest_type = CharField()
    price = DecimalField(decimal_places=2, null=True)
    quantity = IntegerField(null=True)
    amount = DecimalField(decimal_places=2)
    date = DateField()
    


def create_tables():
    with database:
        database.create_tables([User, Investment, ChatHistory, DataOverview, DataTransaction, DataInvestment])
