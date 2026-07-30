from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings


_engine = None
_SessionFactory = None


def _get_session_factory() -> sessionmaker:

    global _engine, _SessionFactory

    if _SessionFactory is None:
        _engine = create_engine(settings.DATABASE_URI, pool_size=10)
        _SessionFactory = sessionmaker(bind=_engine)

    return _SessionFactory


@contextmanager
def get_session():

    session: Session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
