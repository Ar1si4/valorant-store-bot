from __future__ import annotations

from typing import List

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Session, relationship

from .setting import Base


class User(Base):
    __tablename__ = "users"

    id: int = Column("id", Integer, primary_key=True)
    language: str = Column("language", String)

    riot_accounts: List[RiotAccount] = relationship("RiotAccount")

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

    username: str = Column("username", String)
    password: str = Column("password", String)
    region: str = Column("region", String)

    riot_id: str = Column("riot_id", String)

    user_id: int = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", backref="RiotAccount")
