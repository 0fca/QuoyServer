from config import USER_CONF
from persistence.sqlite import Sqlite
from sqlalchemy import select
from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column

import json

MODULE_NAME = "users"

def __mod_init__():
    return Users()

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String, nullable=False)
    user_data = mapped_column(JSON, nullable=False)

    def read_from_data(self, key: str):
        return self.user_data[key] if self.user_data is not None else None
        
class Users:
    __sqlite_engine__ = None
    def __init__(self):
        self.__init_session__()

    def find_by_id(self, id) -> User:
        self.__init_session__()
        s = select(User).where(User.id == id)
        u = self.__execute__stmt__(s)
        self.__sqlite_engine__.dispose()
        return u[0] if len(u) > 0 else None

    def find_by_name(self, username: str) -> User:
        self.__init_session__()
        s = select(User).where(User.name == username)
        u = self.__execute__stmt__(s)
        self.__sqlite_engine__.dispose()
        return u

    def upsert_user_data(self, username: str, user_data: dict) -> User:
        self.__init_session__()
        with Session(self.__sqlite_engine__) as s:
            user = s.scalar(select(User).where(User.name == username))
            if user is None:
                user = User(name=username, user_data=user_data)
                s.add(user)
            else:
                user.user_data = user_data
            s.commit()
            s.refresh(user)
            self.__sqlite_engine__.dispose()
            return user

    @staticmethod
    def normalize_user_data(user: User | None) -> dict:
        if user is None or user.user_data is None:
            return {}
        if isinstance(user.user_data, dict):
            return dict(user.user_data)
        if isinstance(user.user_data, str):
            return json.loads(user.user_data)
        return {}


    def __execute__stmt__(self, stmt) -> User:
        with Session(self.__sqlite_engine__) as s:
            return s.scalar(stmt)
    
    def __init_session__(self):
        sqlite = Sqlite()
        self.__sqlite_engine__ = sqlite.engine()
