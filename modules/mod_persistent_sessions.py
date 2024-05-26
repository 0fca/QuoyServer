from persistence.sqlite import Sqlite
from sqlalchemy import select
from sqlalchemy import String, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session

import json

from modules.mod_users import User

MODULE_NAME = "persistent_sessions"
    

class Base(DeclarativeBase):
    pass

class PersistentSession(Base):
    __tablename__ = "session"
    id = mapped_column(String, primary_key=True)
    json = mapped_column(JSON, nullable=False)

class Sessions:
    __sqlite_engine__ = None
    def __init__(self):
        self.__init_session__()

    def find_by_id(self, id) -> PersistentSession:
        s = select(PersistentSession).where(PersistentSession.id == id)
        r = self.__execute__stmt__(s)
        return r

    def append_session(self, session):
        self.__init_session__()
        ps = self.find_by_id(session.sid())
        if ps is None:
            ps = PersistentSession()
            ps.id = session.sid()
    
        ps.json = dict(sid=session.sid(), ip=session.ip(), username=session.username())
        with Session(self.__sqlite_engine__) as s:
            s.add(ps)
            s.commit()
        self.__sqlite_engine__.dispose()

    def forget_session(self, id):
        self.__init_session__()
        with Session(self.__sqlite_engine__) as s:
            tbd = self.find_by_id(id)
            s.delete(tbd)
            s.commit()
        self.__sqlite_engine__.dispose()

    def __execute__stmt__(self, stmt) -> PersistentSession:
        with Session(self.__sqlite_engine__) as s:
            return s.scalar(stmt)
    
    def __init_session__(self):
        sqlite = Sqlite()
        self.__sqlite_engine__ = sqlite.engine()

def __mod_init__() -> Sessions:
    return Sessions()