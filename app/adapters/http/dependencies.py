"""Dépendances FastAPI : une session par requête, puis les cas d'utilisation câblés
par le module de composition. Les tests remplacent `get_session` ou `get_notifier`
via `app.dependency_overrides`."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.persistence.database import SessionLocal
from app.application.ports import Notifier
from app.bootstrap import UseCases, build_notifier


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_notifier() -> Notifier:
    return build_notifier()


def get_use_cases(session: Session = Depends(get_session), notifier: Notifier = Depends(get_notifier)) -> UseCases:
    return UseCases(session, notifier)
