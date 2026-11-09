"""Traduction des erreurs métier en réponses HTTP, en un seul endroit."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (DomainError, InvalidStateTransition, NotFound, PlanningNotPublishable, RuleViolation,
                               SchedulingConflict)

STATUS_CODES = [
    (NotFound, 404),
    (SchedulingConflict, 409),
    (InvalidStateTransition, 409),
    (RuleViolation, 400),
]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        status = next((code for error_type, code in STATUS_CODES if isinstance(exc, error_type)), 400)
        body = {"detail": str(exc)}
        if isinstance(exc, PlanningNotPublishable):
            body["problems"] = exc.problems
        return JSONResponse(status_code=status, content=body)
