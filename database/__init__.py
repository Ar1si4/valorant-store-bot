from .setting import Base, ENGINE, session

Base.metadata.create_all(bind=ENGINE)
