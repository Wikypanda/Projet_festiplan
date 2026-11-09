"""Ports sortants : contrats dont les cas d'utilisation ont besoin.

Les implémentations (SQLAlchemy, faux email...) sont dans app/adapters et sont
injectées par le module de composition app/bootstrap.py.
"""
from abc import ABC, abstractmethod

from app.domain.artist import Artist
from app.domain.festival import Festival
from app.domain.incident import Incident
from app.domain.stage import Stage


class FestivalRepository(ABC):
    """Charge et enregistre l'agrégat Festival complet (festival + concerts)."""

    @abstractmethod
    def get(self, festival_id: int) -> Festival | None: ...

    @abstractmethod
    def get_by_concert_id(self, concert_id: int) -> Festival | None: ...

    @abstractmethod
    def list(self) -> list[Festival]: ...

    @abstractmethod
    def save(self, festival: Festival) -> None:
        """Enregistre l'agrégat de façon atomique et attribue les identifiants manquants."""


class ArtistRepository(ABC):
    @abstractmethod
    def get(self, artist_id: int) -> Artist | None: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Artist | None: ...

    @abstractmethod
    def list(self) -> list[Artist]: ...

    @abstractmethod
    def add(self, artist: Artist) -> None: ...


class StageRepository(ABC):
    @abstractmethod
    def get(self, stage_id: int) -> Stage | None: ...

    @abstractmethod
    def list_for_festival(self, festival_id: int) -> list[Stage]: ...

    @abstractmethod
    def add(self, stage: Stage) -> None: ...


class IncidentRepository(ABC):
    @abstractmethod
    def add(self, incident: Incident) -> None: ...

    @abstractmethod
    def list(self, concert_id: int | None = None) -> list[Incident]: ...


class Notifier(ABC):
    """Envoi d'une notification à l'équipe de production."""

    @abstractmethod
    def send(self, subject: str, message: str) -> None:
        """Peut lever une exception si le service d'envoi est indisponible."""
