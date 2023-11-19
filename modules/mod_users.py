from config import USER_CONF
from persistence.sqlite import Sqlite
from sqlalchemy import select
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import bindparam

import json

MODULE_NAME = "users"

def __init__():
    pass

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String, nullable=False)
    registered_sessions = mapped_column(String, nullable=False)

    def sessions(self) -> list:
        return json.loads(self.registered_sessions)
        
class Users:
    __sqlite_engine__ = None
    def __init__(self):
        sqlite = Sqlite()
        if not sqlite.is_engine_initialized():
            self.__sqlite_engine__ = sqlite.init_engine()
        self.__sqlite_engine__ = sqlite.engine()

    def find_by_id(self, id) -> User:
        s = select(User).where(User.id == bindparam('id'))
        u = self.__execute__stmt__(s, [id])
        return u[0] if len(u) > 0 else None

    def find_by_name(self, username: str) -> User:
        s = select(User).where(User.name == bindparam('username'))
        u = self.__execute__stmt__(s, [username])
        return u[0] if len(u) > 0 else None
    
    def find_by_session(self, sid: str):
        s = select(User).where(User.registered_sessions.contains(sid))
        print(s)

    def __execute__stmt__(self, stmt, params: list):
        with self.__sqlite_engine__.connect() as c:
            cursor = c.connection.cursor()
            cursor.execute(str(stmt), params)
            return cursor.fetchall()
            