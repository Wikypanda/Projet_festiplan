"""Schémas Pydantic : validation du FORMAT des requêtes et forme des réponses.

Les règles métier (chevauchements, période du festival...) ne sont pas ici :
elles sont dans le domaine, pour rester vraies même sans passer par HTTP.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.artist import Artist
from app.domain.festival import Concert, Festival
from app.domain.incident import Incident
from app.domain.stage import Stage


class FestivalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    start_date: datetime
    end_date: datetime


class FestivalRead(FestivalCreate):
    id: int
    status: str

    @classmethod
    def from_domain(cls, f: Festival, **extra):
        return cls(id=f.id, name=f.name, location=f.location, start_date=f.period.start, end_date=f.period.end,
                   status=f.status.value, **extra)


class FestivalPublished(FestivalRead):
    warnings: list[str] = []


class ArtistCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    genre: str = Field(min_length=2, max_length=80)
    required_equipment: list[str] = []


class ArtistRead(BaseModel):
    id: int
    name: str
    genre: str
    required_equipment: list[str]

    @classmethod
    def from_domain(cls, a: Artist):
        return cls(id=a.id, name=a.name, genre=a.genre, required_equipment=a.required_equipment.as_list())


class StageCreate(BaseModel):
    festival_id: int
    name: str = Field(min_length=2, max_length=100)
    capacity: int = Field(gt=0)
    available_equipment: list[str] = []


class StageRead(BaseModel):
    id: int
    festival_id: int
    name: str
    capacity: int
    available_equipment: list[str]

    @classmethod
    def from_domain(cls, s: Stage):
        return cls(id=s.id, festival_id=s.festival_id, name=s.name, capacity=s.capacity,
                   available_equipment=s.available_equipment.as_list())


class ConcertCreate(BaseModel):
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


class ConcertReschedule(BaseModel):
    start_time: datetime
    end_time: datetime


class PublishedConcertReschedule(ConcertReschedule):
    reason: str = Field(description="Motif obligatoire de la modification d'un planning publié")


class ConcertRead(BaseModel):
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime
    status: str

    @classmethod
    def from_domain(cls, c: Concert, **extra):
        return cls(id=c.id, festival_id=c.festival_id, artist_id=c.artist_id, stage_id=c.stage_id,
                   start_time=c.slot.start, end_time=c.slot.end, status=c.status.value, **extra)


class ConcertChanged(ConcertRead):
    """Réponse d'une modification : la modification est faite, `warnings` liste
    les effets secondaires (notifications) qui ont échoué."""

    warnings: list[str] = []


class IncidentCreate(BaseModel):
    concert_id: int
    description: str = Field(min_length=3, max_length=2000)
    occurred_at: datetime | None = None


class IncidentRead(BaseModel):
    id: int
    concert_id: int
    description: str
    occurred_at: datetime
    resolved: bool

    @classmethod
    def from_domain(cls, i: Incident):
        return cls(id=i.id, concert_id=i.concert_id, description=i.description, occurred_at=i.occurred_at,
                   resolved=i.resolved)
