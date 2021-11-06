from __future__ import annotations
from sqlalchemy import String, Column
from sqlalchemy.orm import Session
from valorant_api import SyncValorantApi

from .user import User
from .setting import Base


class Weapon(Base):
    __tablename__ = "weapons"

    uuid: str = Column("uuid", String, primary_key=True)
    lang: str = Column("lang", String)
    display_name: str = Column("display_name", String)
    display_icon: str = Column("display_icon", String)
    streamed_video: str = Column("streamed_video", String)

    @staticmethod
    def get_promised(session: Session, uuid: str, user: User) -> Weapon:
        weapon = session.query(Weapon).filter(Weapon.uuid == uuid, Weapon.lang == user.language).first()
        if weapon is not None:
            return weapon

        skin = SyncValorantApi(user.language).search_weapon_levels_by_uuid(uuid)

        new_weapon = Weapon(
            uuid=uuid,
            lang=user.language,
            display_name=skin.display_name,
            display_icon=skin.display_icon,
            streamed_video=skin.streamed_video
        )
        session.add(new_weapon)
        session.commit()
        return new_weapon
