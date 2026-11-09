"""Commandes : demandes d'action adressées aux cas d'utilisation.

Ce sont de simples données, indépendantes de HTTP (un script ou un test peut
les construire directement).
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CreateFestival:
    name: str
    location: str
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class PublishPlanning:
    festival_id: int


@dataclass(frozen=True)
class RegisterArtist:
    name: str
    genre: str
    required_equipment: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CreateStage:
    festival_id: int
    name: str
    capacity: int
    available_equipment: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScheduleConcert:
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class RescheduleConcert:
    concert_id: int
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class ReschedulePublishedConcert:
    concert_id: int
    start_time: datetime
    end_time: datetime
    reason: str


@dataclass(frozen=True)
class CancelConcert:
    concert_id: int


@dataclass(frozen=True)
class ReportIncident:
    concert_id: int
    description: str
    occurred_at: datetime | None = None
