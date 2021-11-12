import datetime

from sqlalchemy import Column, Integer, String, DATETIME

from .setting import Base


class SkinLog(Base):
    __tablename__ = "skin_logs"

    id: int = Column("id", Integer, autoincrement=True, primary_key=True)

    account_puuid: str = Column("account_puuid", String)
    date: datetime.datetime = Column("date", DATETIME)
    skin_1: str = Column("skin_1", String)
    skin_2: str = Column("skin_2", String)
    skin_3: str = Column("skin_3", String)
    skin_4: str = Column("skin_4", String)
