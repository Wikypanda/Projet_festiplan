from fastapi import APIRouter, Depends

from app.adapters.http.dependencies import get_use_cases
from app.adapters.http.schemas import FestivalCreate, FestivalPublished, FestivalRead
from app.application.commands import CreateFestival, PublishPlanning
from app.bootstrap import UseCases

router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.get("", response_model=list[FestivalRead])
def list_festivals(uc: UseCases = Depends(get_use_cases)):
    return [FestivalRead.from_domain(f) for f in uc.list_festivals.execute()]


@router.get("/{festival_id}", response_model=FestivalRead)
def get_festival(festival_id: int, uc: UseCases = Depends(get_use_cases)):
    return FestivalRead.from_domain(uc.get_festival.execute(festival_id))


@router.post("", response_model=FestivalRead, status_code=201)
def create_festival(payload: FestivalCreate, uc: UseCases = Depends(get_use_cases)):
    return FestivalRead.from_domain(uc.create_festival.execute(CreateFestival(**payload.model_dump())))


@router.post("/{festival_id}/publish", response_model=FestivalPublished)
def publish_festival(festival_id: int, uc: UseCases = Depends(get_use_cases)):
    result = uc.publish_planning.execute(PublishPlanning(festival_id))
    return FestivalPublished.from_domain(result.value, warnings=result.warnings)
