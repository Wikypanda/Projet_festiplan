from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

Base = declarative_base()


def make_engine(url: str):
    if not url.startswith("sqlite"):
        return create_engine(url)
    options = {"connect_args": {"check_same_thread": False}}
    if url in ("sqlite://", "sqlite:///:memory:"):
        options["poolclass"] = StaticPool  # une seule connexion partagée pour la base en mémoire
    return create_engine(url, **options)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(bind=engine) -> None:
    from app.adapters.persistence import models  # noqa: F401 (enregistre les tables)
    Base.metadata.create_all(bind=bind)
