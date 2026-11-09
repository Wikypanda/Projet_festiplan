"""Agrégat Festival : racine = Festival, entités internes = Concert.

Toutes les règles qui portent sur PLUSIEURS concerts d'un même festival
(chevauchements R2/R3, période R6, état du planning R7/R8) ne peuvent être
garanties que si l'on voit l'ensemble du planning. C'est pourquoi les concerts
font partie de l'agrégat Festival et ne sont modifiés qu'à travers lui.
"""
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Mapping

from app.domain.artist import Artist
from app.domain.errors import (DomainError, InvalidStateTransition, NotFound, PlanningNotPublishable,
                               RuleViolation, SchedulingConflict)
from app.domain.events import ConcertCancelled, ConcertRescheduled, DomainEvent, PlanningPublished
from app.domain.stage import Stage
from app.domain.value_objects import FestivalPeriod, TimeSlot


class PlanningStatus(str, Enum):
    PREPARATION = "preparation"
    PUBLISHED = "published"


class ConcertStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


@dataclass(eq=False)
class Concert:
    """Entité : deux concerts aux mêmes horaires restent deux concerts distincts."""

    id: int | None
    festival_id: int | None
    artist_id: int
    stage_id: int
    slot: TimeSlot
    status: ConcertStatus = ConcertStatus.SCHEDULED

    @property
    def is_active(self) -> bool:
        return self.status is ConcertStatus.SCHEDULED

    def move_to(self, slot: TimeSlot) -> None:
        if not self.is_active:
            raise InvalidStateTransition("Un concert annulé ne peut pas être déplacé")
        self.slot = slot

    def cancel(self) -> None:
        if not self.is_active:
            raise InvalidStateTransition("Ce concert est déjà annulé")
        self.status = ConcertStatus.CANCELLED


@dataclass(eq=False)
class Festival:
    id: int | None
    name: str
    location: str
    period: FestivalPeriod
    status: PlanningStatus = PlanningStatus.PREPARATION
    concerts: list[Concert] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------ lecture

    @property
    def is_published(self) -> bool:
        return self.status is PlanningStatus.PUBLISHED

    def find_concert(self, concert_id: int) -> Concert:
        for concert in self.concerts:
            if concert.id == concert_id:
                return concert
        raise NotFound("Concert introuvable")

    def schedule(self) -> list[Concert]:
        """Planning : concerts actifs dans l'ordre chronologique."""
        return sorted((c for c in self.concerts if c.is_active), key=lambda c: (c.slot.start, c.stage_id))

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    # ------------------------------------------- opérations ordinaires (R7)

    def schedule_concert(self, artist: Artist, stage: Stage, slot: TimeSlot) -> Concert:
        self._ensure_in_preparation()
        concert = Concert(id=None, festival_id=self.id, artist_id=artist.id, stage_id=stage.id, slot=slot)
        self._check_resources(concert, artist, stage)
        self._check_availability(concert)
        self.concerts.append(concert)
        return concert

    def reschedule_concert(self, concert_id: int, new_slot: TimeSlot) -> Concert:
        self._ensure_in_preparation()
        return self._move(concert_id, new_slot, reason=None)

    def cancel_concert(self, concert_id: int) -> Concert:
        self._ensure_in_preparation()
        concert = self.find_concert(concert_id)
        concert.cancel()
        self._events.append(ConcertCancelled(festival_id=self.id, concert_id=concert.id))
        return concert

    # ------------------------------------------------- publication (R7, R8)

    def publish(self, artists: Mapping[int, Artist], stages: Mapping[int, Stage]) -> None:
        """Transition PREPARATION -> PUBLISHED, seulement si tout le planning est valide."""
        if self.is_published:
            raise InvalidStateTransition("Le planning est déjà publié")
        problems = []
        for concert in self.schedule():
            try:
                self._check_resources(concert, artists.get(concert.artist_id), stages.get(concert.stage_id))
                self._check_availability(concert, ignore=concert)
            except DomainError as exc:
                problems.append(f"concert #{concert.id} : {exc}")
        if problems:
            raise PlanningNotPublishable(problems)
        self.status = PlanningStatus.PUBLISHED
        self._events.append(PlanningPublished(festival_id=self.id, festival_name=self.name))

    def reschedule_published_concert(self, concert_id: int, new_slot: TimeSlot, reason: str) -> Concert:
        """Procédure explicite de modification d'un planning publié.

        Le planning reste publié, mais un motif est obligatoire et toutes les
        règles de disponibilité restent appliquées.
        """
        if not self.is_published:
            raise InvalidStateTransition("Le planning n'est pas publié : utilisez le déplacement ordinaire")
        if not reason or not reason.strip():
            raise RuleViolation("Un motif est obligatoire pour modifier un planning publié")
        return self._move(concert_id, new_slot, reason=reason.strip())

    # ------------------------------------------------------- règles internes

    def _move(self, concert_id: int, new_slot: TimeSlot, reason: str | None) -> Concert:
        concert = self.find_concert(concert_id)
        previous_slot = concert.slot
        # On vérifie le concert "candidat" avant de modifier l'original.
        self._check_availability(replace(concert, slot=new_slot), ignore=concert)
        concert.move_to(new_slot)
        self._events.append(ConcertRescheduled(festival_id=self.id, concert_id=concert.id,
                                               previous_slot=previous_slot, new_slot=new_slot, reason=reason))
        return concert

    def _ensure_in_preparation(self) -> None:  # R7
        if self.is_published:
            raise InvalidStateTransition(
                "Le planning est publié : il ne peut plus être modifié par une opération ordinaire")

    def _check_resources(self, concert: Concert, artist: Artist | None, stage: Stage | None) -> None:
        """R4 (références valides, scène du festival) et R5 (équipements)."""
        if artist is None or stage is None:
            raise RuleViolation("Le concert doit référencer un artiste et une scène existants")
        if stage.festival_id != self.id:
            raise RuleViolation("La scène n'appartient pas à ce festival")
        missing = artist.required_equipment.missing_from(stage.available_equipment)
        if missing:
            raise RuleViolation(
                f"La scène {stage.name} ne dispose pas des équipements requis : {', '.join(sorted(missing))}")

    def _check_availability(self, concert: Concert, ignore: Concert | None = None) -> None:
        """Règles de disponibilité du planning : R6, R2 et R3, centralisées ici."""
        if not self.period.contains(concert.slot):
            raise RuleViolation("Le concert doit se dérouler entièrement pendant le festival")
        for other in self.concerts:
            if other is ignore or not other.is_active or not other.slot.overlaps(concert.slot):
                continue
            if other.stage_id == concert.stage_id:
                raise SchedulingConflict(f"Conflit : la scène est déjà occupée par le concert #{other.id}")
            if other.artist_id == concert.artist_id:
                raise SchedulingConflict(f"Conflit : l'artiste joue déjà au même moment (concert #{other.id})")
