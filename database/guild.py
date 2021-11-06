from __future__ import annotations

from sqlalchemy import Column, Integer
from sqlalchemy.orm import Session

from .setting import Base


class Guild(Base):
    __tablename__ = "guilds"

    id: int = Column("id", Integer, primary_key=True)

    @staticmethod
    def get_promised(session: Session, id: int) -> Guild:
        guild = session.query(Guild).filter(Guild.id == id).first()
        if guild is not None:
            return guild
        new_guild = Guild(id=id)
        session.add(new_guild)
        session.commit()
        return new_guild
