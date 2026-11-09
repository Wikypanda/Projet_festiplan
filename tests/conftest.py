import os

# Base en mémoire : les tests n'écrivent jamais dans festiplan.db.
os.environ["FESTIPLAN_DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402

# Les imports de FastAPI / SQLAlchemy sont faits DANS les fixtures : les tests
# du domaine et des cas d'utilisation ne chargent ainsi aucune technologie.


@pytest.fixture()
def session_factory():
    """Base SQLite en mémoire, neuve pour chaque test."""
    from sqlalchemy.orm import sessionmaker

    from app.adapters.persistence.database import init_db, make_engine

    engine = make_engine("sqlite://")
    init_db(bind=engine)
    yield sessionmaker(bind=engine, autocommit=False, autoflush=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    from fastapi.testclient import TestClient

    from app.adapters.http.dependencies import get_session
    from app.main import app

    def test_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    yield TestClient(app)
    app.dependency_overrides.clear()
