from sqlalchemy import Column, Integer


class User:
    __tablename__ = "users"

    id: int = Column("id", Integer, primary_key=True)
    @staticmethod
    def get_promised(session, id: int) -> User:
        user = session.query(User).filter(User.id == id).first()
        if user is not None:
            return user
        new_user = User(id=id)
        session.add(new_user)
        session.commit()
        return new_user
