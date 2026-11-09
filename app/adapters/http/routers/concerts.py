"""Contrôleur HTTP des concerts : traduit la requête en commande, appelle le cas
d'utilisation, traduit le résultat en réponse. Aucune règle métier ici."""
from fastapi import APIRouter, Depends

from app.adapters.http.dependencies import get_use_cases
from app.adapters.http.schemas import (ConcertChanged, ConcertCreate, ConcertRead, ConcertReschedule,
                                       PublishedConcertReschedule)
from app.application.commands import CancelConcert, RescheduleConcert, ReschedulePublishedConcert, ScheduleConcert
from app.bootstrap import UseCases

router = APIRouter(prefix="/concerts", tags=["concerts"])


@router.get("", response_model=list[ConcertRead])
def list_concerts(festival_id: int, uc: UseCases = Depends(get_use_cases)):
    return [ConcertRead.from_domain(c) for c in uc.get_schedule.execute(festival_id)]


@router.get("/schedule/{festival_id}", response_model=list[ConcertRead])
def get_schedule(festival_id: int, uc: UseCases = Depends(get_use_cases)):
    return [ConcertRead.from_domain(c) for c in uc.get_schedule.execute(festival_id)]


@router.get("/{concert_id}", response_model=ConcertRead)
def get_concert(concert_id: int, uc: UseCases = Depends(get_use_cases)):
    return ConcertRead.from_domain(uc.get_concert.execute(concert_id))


@router.post("", response_model=ConcertRead, status_code=201)
def create_concert(payload: ConcertCreate, uc: UseCases = Depends(get_use_cases)):
    concert = uc.schedule_concert.execute(ScheduleConcert(**payload.model_dump()))
    return ConcertRead.from_domain(concert)


@router.patch("/{concert_id}/reschedule", response_model=ConcertChanged)
def reschedule_concert(concert_id: int, payload: ConcertReschedule, uc: UseCases = Depends(get_use_cases)):
    result = uc.reschedule_concert.execute(RescheduleConcert(concert_id, payload.start_time, payload.end_time))
    return ConcertChanged.from_domain(result.value, warnings=result.warnings)


@router.post("/{concert_id}/published-reschedule", response_model=ConcertChanged)
def reschedule_published_concert(concert_id: int, payload: PublishedConcertReschedule,
                                 uc: UseCases = Depends(get_use_cases)):
    """Procédure explicite pour déplacer un concert d'un planning déjà publié (motif obligatoire)."""
    result = uc.reschedule_published_concert.execute(
        ReschedulePublishedConcert(concert_id, payload.start_time, payload.end_time, payload.reason))
    return ConcertChanged.from_domain(result.value, warnings=result.warnings)


@router.post("/{concert_id}/cancel", response_model=ConcertChanged)
def cancel_concert(concert_id: int, uc: UseCases = Depends(get_use_cases)):
    result = uc.cancel_concert.execute(CancelConcert(concert_id))
    return ConcertChanged.from_domain(result.value, warnings=result.warnings)
