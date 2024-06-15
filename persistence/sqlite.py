from sqlalchemy import create_engine
from sqlalchemy import Engine
from config import DB_CONF


class Sqlite:
    __engine__ : Engine = None

    def __init__(self) -> None:
        self.__init_engine__()

    def __init_engine__(self) -> None:
        if not self.__engine__:
            e = create_engine(
                f"sqlite:///{DB_CONF['db_name']}?"
                "check_same_thread=true&timeout=10&uri=true"
            )
            self.__engine__ = e

    def is_engine_initialized(self) -> bool:
        return self.__engine__ is not None

    def engine(self) -> Engine:
        return self.__engine__