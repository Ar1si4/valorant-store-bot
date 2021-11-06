from __future__ import annotations

from typing import List

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Session, relationship

from .setting import Base


class User(Base):
    __tablename__ = "users"

    id: int = Column("id", Integer, primary_key=True)
    language: str = Column("language", String)

    riot_accounts: List[RiotAccount] = relationship("RiotAccount", overlaps="riot_accounts")

    @staticmethod
    def get_promised(session: Session, id: int) -> User:
        user = session.query(User).filter(User.id == id).first()
        if user is not None:
            return user
        new_user = User(id=id)
        session.add(new_user)
        session.commit()
        return new_user

    def get_text(self, ja: str, en: str):
        if self.language == "ja-JP":
            return ja
        return en


class RiotAccount(Base):
    __tablename__ = "riot_accounts"

    uuid: int = Column("uuid", Integer, autoincrement=True, primary_key=True)

    username: str = Column("username", String)
    password: str = Column("password", String)
    region: str = Column("region", String)

    game_name: str = Column("game_name", String)

    user_id: int = Column("user_id", Integer, ForeignKey("users.id"))
    user = relationship("User", backref="RiotAccount", overlaps="riot_accounts")
