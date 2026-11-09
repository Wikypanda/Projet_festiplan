"""Contrôleurs HTTP des artistes, scènes et incidents."""
from fastapi import APIRouter, Depends

from app.adapters.http.dependencies import get_use_cases
from app.adapters.http.schemas import ArtistCreate, ArtistRead, IncidentCreate, IncidentRead, StageCreate, StageRead
from app.application.commands import CreateStage, RegisterArtist, ReportIncident
from app.bootstrap import UseCases

artists_router = APIRouter(prefix="/artists", tags=["artists"])
stages_router = APIRouter(prefix="/stages", tags=["stages"])
incidents_router = APIRouter(prefix="/incidents", tags=["incidents"])


@artists_router.get("", response_model=list[ArtistRead])
def list_artists(uc: UseCases = Depends(get_use_cases)):
    return [ArtistRead.from_domain(a) for a in uc.list_artists.execute()]


@artists_router.post("", response_model=ArtistRead, status_code=201)
def create_artist(payload: ArtistCreate, uc: UseCases = Depends(get_use_cases)):
    return ArtistRead.from_domain(uc.register_artist.execute(RegisterArtist(**payload.model_dump())))


@stages_router.get("", response_model=list[StageRead])
def list_stages(festival_id: int, uc: UseCases = Depends(get_use_cases)):
    return [StageRead.from_domain(s) for s in uc.list_stages.execute(festival_id)]


@stages_router.post("", response_model=StageRead, status_code=201)
def create_stage(payload: StageCreate, uc: UseCases = Depends(get_use_cases)):
    return StageRead.from_domain(uc.create_stage.execute(CreateStage(**payload.model_dump())))


@incidents_router.post("", response_model=IncidentRead, status_code=201)
def create_incident(payload: IncidentCreate, uc: UseCases = Depends(get_use_cases)):
    return IncidentRead.from_domain(uc.report_incident.execute(ReportIncident(**payload.model_dump())))


@incidents_router.get("", response_model=list[IncidentRead])
def list_incidents(concert_id: int | None = None, uc: UseCases = Depends(get_use_cases)):
    return [IncidentRead.from_domain(i) for i in uc.list_incidents.execute(concert_id)]
