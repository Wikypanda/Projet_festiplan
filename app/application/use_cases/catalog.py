"""Cas d'utilisation simples : artistes, scènes et incidents."""
from datetime import datetime, timezone

from app.application.commands import CreateStage, RegisterArtist, ReportIncident
from app.application.ports import ArtistRepository, FestivalRepository, IncidentRepository, StageRepository
from app.domain.artist import Artist
from app.domain.errors import NotFound, RuleViolation
from app.domain.incident import Incident
from app.domain.stage import Stage
from app.domain.value_objects import EquipmentSet


class RegisterArtistUseCase:
    def __init__(self, artists: ArtistRepository):
        self.artists = artists

    def execute(self, command: RegisterArtist) -> Artist:
        if self.artists.get_by_name(command.name) is not None:
            raise RuleViolation("Un artiste porte déjà ce nom")
        artist = Artist(id=None, name=command.name, genre=command.genre,
                        required_equipment=EquipmentSet.of(command.required_equipment))
        self.artists.add(artist)
        return artist


class ListArtistsUseCase:
    def __init__(self, artists: ArtistRepository):
        self.artists = artists

    def execute(self) -> list[Artist]:
        return self.artists.list()


class CreateStageUseCase:
    def __init__(self, stages: StageRepository, festivals: FestivalRepository):
        self.stages = stages
        self.festivals = festivals

    def execute(self, command: CreateStage) -> Stage:
        if self.festivals.get(command.festival_id) is None:
            raise NotFound("Festival introuvable")
        stage = Stage(id=None, festival_id=command.festival_id, name=command.name, capacity=command.capacity,
                      available_equipment=EquipmentSet.of(command.available_equipment))
        self.stages.add(stage)
        return stage


class ListStagesUseCase:
    def __init__(self, stages: StageRepository):
        self.stages = stages

    def execute(self, festival_id: int) -> list[Stage]:
        return self.stages.list_for_festival(festival_id)


class ReportIncidentUseCase:
    def __init__(self, incidents: IncidentRepository, festivals: FestivalRepository):
        self.incidents = incidents
        self.festivals = festivals

    def execute(self, command: ReportIncident) -> Incident:
        if self.festivals.get_by_concert_id(command.concert_id) is None:  # R10 : concert existant
            raise NotFound("Concert introuvable")
        occurred_at = command.occurred_at or datetime.now(timezone.utc).replace(tzinfo=None)
        incident = Incident(id=None, concert_id=command.concert_id, description=command.description,
                            occurred_at=occurred_at)
        self.incidents.add(incident)
        return incident


class ListIncidentsUseCase:
    def __init__(self, incidents: IncidentRepository):
        self.incidents = incidents

    def execute(self, concert_id: int | None = None) -> list[Incident]:
        return self.incidents.list(concert_id)
