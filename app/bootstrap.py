"""Module de composition : le SEUL endroit où les adaptateurs concrets sont
créés et injectés dans les cas d'utilisation.

Il est indépendant de FastAPI : l'API (app/adapters/http) et le script de
seed (app/seed.py) l'utilisent tous les deux.
"""
from sqlalchemy.orm import Session

from app.adapters.notifications.fake_email_notifier import FakeEmailNotifier
from app.adapters.persistence.repositories import (SqlAlchemyArtistRepository, SqlAlchemyFestivalRepository,
                                                   SqlAlchemyIncidentRepository, SqlAlchemyStageRepository)
from app.application.notifications import NotificationHandler
from app.application.ports import Notifier
from app.application.use_cases.catalog import (CreateStageUseCase, ListArtistsUseCase, ListIncidentsUseCase,
                                               ListStagesUseCase, RegisterArtistUseCase, ReportIncidentUseCase)
from app.application.use_cases.concerts import (CancelConcertUseCase, GetConcertUseCase, GetScheduleUseCase,
                                                RescheduleConcertUseCase, ReschedulePublishedConcertUseCase,
                                                ScheduleConcertUseCase)
from app.application.use_cases.festivals import (CreateFestivalUseCase, GetFestivalUseCase, ListFestivalsUseCase,
                                                 PublishPlanningUseCase)
from app.config import settings


def build_notifier() -> Notifier:
    return FakeEmailNotifier(fail=settings.fail_notifications)


class UseCases:
    """Tous les cas d'utilisation, câblés pour une session de base de données."""

    def __init__(self, session: Session, notifier: Notifier):
        festivals = SqlAlchemyFestivalRepository(session)
        artists = SqlAlchemyArtistRepository(session)
        stages = SqlAlchemyStageRepository(session)
        incidents = SqlAlchemyIncidentRepository(session)
        notifications = NotificationHandler(notifier)

        self.create_festival = CreateFestivalUseCase(festivals)
        self.list_festivals = ListFestivalsUseCase(festivals)
        self.get_festival = GetFestivalUseCase(festivals)
        self.publish_planning = PublishPlanningUseCase(festivals, artists, stages, notifications)

        self.register_artist = RegisterArtistUseCase(artists)
        self.list_artists = ListArtistsUseCase(artists)

        self.create_stage = CreateStageUseCase(stages, festivals)
        self.list_stages = ListStagesUseCase(stages)

        self.schedule_concert = ScheduleConcertUseCase(festivals, artists, stages)
        self.reschedule_concert = RescheduleConcertUseCase(festivals, notifications)
        self.reschedule_published_concert = ReschedulePublishedConcertUseCase(festivals, notifications)
        self.cancel_concert = CancelConcertUseCase(festivals, notifications)
        self.get_concert = GetConcertUseCase(festivals)
        self.get_schedule = GetScheduleUseCase(festivals)

        self.report_incident = ReportIncidentUseCase(incidents, festivals)
        self.list_incidents = ListIncidentsUseCase(incidents)
