"""Cas d'utilisation sur les concerts.

Chaque cas d'utilisation suit le même schéma :
  1. construire les objets-valeurs (R1 vérifiée dès ici) ;
  2. charger l'agrégat via un port ;
  3. déléguer la décision métier à l'agrégat ;
  4. enregistrer l'agrégat (la modification est alors définitive) ;
  5. seulement ensuite, déclencher les effets secondaires (notifications).
"""
from app.application.commands import CancelConcert, RescheduleConcert, ReschedulePublishedConcert, ScheduleConcert
from app.application.notifications import NotificationHandler, OperationResult
from app.application.ports import ArtistRepository, FestivalRepository, StageRepository
from app.domain.errors import NotFound
from app.domain.festival import Concert, Festival
from app.domain.value_objects import TimeSlot


def _festival_of_concert(festivals: FestivalRepository, concert_id: int) -> Festival:
    festival = festivals.get_by_concert_id(concert_id)
    if festival is None:
        raise NotFound("Concert introuvable")
    return festival


class ScheduleConcertUseCase:
    def __init__(self, festivals: FestivalRepository, artists: ArtistRepository, stages: StageRepository):
        self.festivals = festivals
        self.artists = artists
        self.stages = stages

    def execute(self, command: ScheduleConcert) -> Concert:
        slot = TimeSlot(command.start_time, command.end_time)
        festival = self.festivals.get(command.festival_id)
        if festival is None:
            raise NotFound("Festival introuvable")
        artist = self.artists.get(command.artist_id)
        if artist is None:
            raise NotFound("Artiste introuvable")
        stage = self.stages.get(command.stage_id)
        if stage is None:
            raise NotFound("Scène introuvable")

        concert = festival.schedule_concert(artist, stage, slot)
        self.festivals.save(festival)
        return concert


class RescheduleConcertUseCase:
    """Déplacement ordinaire : refusé si le planning est publié (R7)."""

    def __init__(self, festivals: FestivalRepository, notifications: NotificationHandler):
        self.festivals = festivals
        self.notifications = notifications

    def execute(self, command: RescheduleConcert) -> OperationResult[Concert]:
        new_slot = TimeSlot(command.start_time, command.end_time)
        festival = _festival_of_concert(self.festivals, command.concert_id)

        concert = festival.reschedule_concert(command.concert_id, new_slot)
        self.festivals.save(festival)  # <- la modification est validée ici

        warnings = self.notifications.handle(festival.pull_events())
        return OperationResult(concert, warnings)


class ReschedulePublishedConcertUseCase:
    """Procédure explicite de modification d'un planning déjà publié (R7)."""

    def __init__(self, festivals: FestivalRepository, notifications: NotificationHandler):
        self.festivals = festivals
        self.notifications = notifications

    def execute(self, command: ReschedulePublishedConcert) -> OperationResult[Concert]:
        new_slot = TimeSlot(command.start_time, command.end_time)
        festival = _festival_of_concert(self.festivals, command.concert_id)

        concert = festival.reschedule_published_concert(command.concert_id, new_slot, command.reason)
        self.festivals.save(festival)

        warnings = self.notifications.handle(festival.pull_events())
        return OperationResult(concert, warnings)


class CancelConcertUseCase:
    def __init__(self, festivals: FestivalRepository, notifications: NotificationHandler):
        self.festivals = festivals
        self.notifications = notifications

    def execute(self, command: CancelConcert) -> OperationResult[Concert]:
        festival = _festival_of_concert(self.festivals, command.concert_id)

        concert = festival.cancel_concert(command.concert_id)
        self.festivals.save(festival)

        warnings = self.notifications.handle(festival.pull_events())
        return OperationResult(concert, warnings)


class GetConcertUseCase:
    def __init__(self, festivals: FestivalRepository):
        self.festivals = festivals

    def execute(self, concert_id: int) -> Concert:
        return _festival_of_concert(self.festivals, concert_id).find_concert(concert_id)


class GetScheduleUseCase:
    """Planning d'un festival : concerts actifs dans l'ordre chronologique."""

    def __init__(self, festivals: FestivalRepository):
        self.festivals = festivals

    def execute(self, festival_id: int) -> list[Concert]:
        festival = self.festivals.get(festival_id)
        if festival is None:
            raise NotFound("Festival introuvable")
        return festival.schedule()
