from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.http.errors import register_error_handlers
from app.adapters.http.routers import catalog, concerts, festivals
from app.adapters.persistence.database import init_db
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.2.0", description="API de gestion d'un festival fictif",
                  lifespan=lifespan)
    for router in (festivals.router, catalog.artists_router, catalog.stages_router, concerts.router,
                   catalog.incidents_router):
        app.include_router(router)
    register_error_handlers(app)

    @app.get("/")
    def health():
        return {"message": "Bienvenue sur FestiPlan", "status": "ok"}

    return app


app = create_app()
