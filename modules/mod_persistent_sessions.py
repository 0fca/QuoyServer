from persistence.sqlite import Sqlite
from sqlalchemy import select
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import bindparam

from modules.mod_users import User

MODULE_NAME = "persistent_sessions"

def __init__():
    pass

class Base(DeclarativeBase):
    pass


class PersistentSession:
    __tablename__ = "session"
    id = mapped_column(String, primary_key=True, autoincrement=True)
    json = mapped_column(String, nullable=False)

class Sessions:
    __sqlite_engine__ = None
    def __init__(self):
        sqlite = Sqlite()
        if not sqlite.is_engine_initialized():
            self.__sqlite_engine__ = sqlite.init_engine()
        self.__sqlite_engine__ = sqlite.engine()

    def find_by_id(self, id: int):
        s = select(PersistentSession).where(PersistentSession.id == bindparam("id"))
        ps = self.__execute__stmt__(s, [id])
        print(ps)

    def __execute__stmt__(self, stmt, params: list):
        with self.__sqlite_engine__.connect() as c:
            cursor = c.connection.cursor()
            cursor.execute(str(stmt), params)
            return cursor.fetchall()