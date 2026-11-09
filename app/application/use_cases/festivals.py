from app.application.commands import CreateFestival, PublishPlanning
from app.application.notifications import NotificationHandler, OperationResult
from app.application.ports import ArtistRepository, FestivalRepository, StageRepository
from app.domain.errors import NotFound
from app.domain.festival import Festival
from app.domain.value_objects import FestivalPeriod


class CreateFestivalUseCase:
    def __init__(self, festivals: FestivalRepository):
        self.festivals = festivals

    def execute(self, command: CreateFestival) -> Festival:
        festival = Festival(id=None, name=command.name, location=command.location,
                            period=FestivalPeriod(command.start_date, command.end_date))
        self.festivals.save(festival)
        return festival


class ListFestivalsUseCase:
    def __init__(self, festivals: FestivalRepository):
        self.festivals = festivals

    def execute(self) -> list[Festival]:
        return self.festivals.list()


class GetFestivalUseCase:
    def __init__(self, festivals: FestivalRepository):
        self.festivals = festivals

    def execute(self, festival_id: int) -> Festival:
        festival = self.festivals.get(festival_id)
        if festival is None:
            raise NotFound("Festival introuvable")
        return festival


class PublishPlanningUseCase:
    """Publie le planning après avoir revérifié tous ses concerts (R8)."""

    def __init__(self, festivals: FestivalRepository, artists: ArtistRepository, stages: StageRepository,
                 notifications: NotificationHandler):
        self.festivals = festivals
        self.artists = artists
        self.stages = stages
        self.notifications = notifications

    def execute(self, command: PublishPlanning) -> OperationResult[Festival]:
        festival = self.festivals.get(command.festival_id)
        if festival is None:
            raise NotFound("Festival introuvable")
        artists = {a.id: a for a in self.artists.list()}
        stages = {s.id: s for s in self.stages.list_for_festival(festival.id)}

        festival.publish(artists, stages)
        self.festivals.save(festival)

        warnings = self.notifications.handle(festival.pull_events())
        return OperationResult(festival, warnings)
