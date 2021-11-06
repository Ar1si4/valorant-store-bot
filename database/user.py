from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

from .setting import Base


class User(Base):
    __tablename__ = "users"

    id: int = Column("id", Integer, primary_key=True)
    language: str = Column("language", String)

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
