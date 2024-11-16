import logging
from contextlib import contextmanager
from typing import Generator

from sqlmodel import SQLModel, create_engine, Session

from src.config import PROJECT_ROOT

DATABASE_PATH = PROJECT_ROOT / "database.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, echo=True)

logging.getLogger("sqlalchemy.engine.Engine").handlers = [logging.NullHandler()]


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()