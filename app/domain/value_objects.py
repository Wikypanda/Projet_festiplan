"""Objets-valeurs : immuables, définis par leurs valeurs, valides dès leur création."""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.domain.errors import RuleViolation


@dataclass(frozen=True)
class TimeSlot:
    """Créneau d'un concert. Invariant R1 : fin strictement après le début."""

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise RuleViolation("L'heure de fin doit être strictement postérieure à l'heure de début")

    def overlaps(self, other: "TimeSlot") -> bool:
        # Deux créneaux qui se touchent (fin == début) ne se chevauchent pas.
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class FestivalPeriod:
    """Dates du festival. Un concert doit y être entièrement contenu (R6)."""

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise RuleViolation("La date de fin doit être postérieure à la date de début")

    def contains(self, slot: TimeSlot) -> bool:
        return self.start <= slot.start and slot.end <= self.end


@dataclass(frozen=True)
class EquipmentSet:
    """Ensemble d'équipements techniques (besoins d'un artiste ou dotation d'une scène)."""

    items: frozenset[str] = frozenset()

    @classmethod
    def of(cls, names: Iterable[str]) -> "EquipmentSet":
        return cls(frozenset(n.strip() for n in names if n and n.strip()))

    def missing_from(self, available: "EquipmentSet") -> set[str]:
        """Équipements de cet ensemble absents de `available`."""
        return set(self.items - available.items)

    def as_list(self) -> list[str]:
        return sorted(self.items)
