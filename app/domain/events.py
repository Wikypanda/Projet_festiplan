"""Événements de domaine : des faits métier qui se sont produits (au passé)."""
from dataclasses import dataclass

from app.domain.value_objects import TimeSlot


@dataclass(frozen=True)
class ConcertRescheduled:
    festival_id: int
    concert_id: int
    previous_slot: TimeSlot
    new_slot: TimeSlot
    reason: str | None = None  # renseigné uniquement pour un planning déjà publié


@dataclass(frozen=True)
class ConcertCancelled:
    festival_id: int
    concert_id: int


@dataclass(frozen=True)
class PlanningPublished:
    festival_id: int
    festival_name: str


DomainEvent = ConcertRescheduled | ConcertCancelled | PlanningPublished
