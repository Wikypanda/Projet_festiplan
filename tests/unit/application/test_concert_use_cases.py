"""Tests des cas d'utilisation avec des repositories en mémoire (ni FastAPI, ni SQLite)."""
from datetime import datetime

import pytest

from app.application.commands import (CancelConcert, PublishPlanning, RescheduleConcert, ReschedulePublishedConcert,
                                      ScheduleConcert)
from app.application.notifications import NotificationHandler
from app.application.use_cases.concerts import (CancelConcertUseCase, GetScheduleUseCase, RescheduleConcertUseCase,
                                                ReschedulePublishedConcertUseCase, ScheduleConcertUseCase)
from app.application.use_cases.festivals import PublishPlanningUseCase
from app.domain.artist import Artist
from app.domain.errors import InvalidStateTransition, NotFound, RuleViolation, SchedulingConflict
from app.domain.festival import ConcertStatus, Festival
from app.domain.stage import Stage
from app.domain.value_objects import FestivalPeriod
from tests.fakes import (FailingNotifier, InMemoryArtistRepository, InMemoryFestivalRepository,
                         InMemoryStageRepository, SpyNotifier)


def at(hour, minute=0, day=18):
    return datetime(2027, 6, day, hour, minute)


class World:
    """Festival en préparation avec 2 scènes, 2 artistes et 2 concerts sur Mainstage."""

    def __init__(self, notifier=None):
        self.festivals = InMemoryFestivalRepository()
        self.festivals.save(Festival(id=None, name="Hellforge", location="Clisson",
                                     period=FestivalPeriod(at(10), at(23, 59, day=20))))
        self.artists = InMemoryArtistRepository(Artist(id=1, name="Iron Vow", genre="Heavy"),
                                                Artist(id=2, name="Crimson Engine", genre="Thrash"))
        self.stages = InMemoryStageRepository(Stage(id=1, festival_id=1, name="Mainstage", capacity=50000),
                                              Stage(id=2, festival_id=1, name="Warzone", capacity=15000))
        self.notifier = notifier or SpyNotifier()
        self.notifications = NotificationHandler(self.notifier)
        self.schedule = ScheduleConcertUseCase(self.festivals, self.artists, self.stages)
        self.reschedule = RescheduleConcertUseCase(self.festivals, self.notifications)
        self.reschedule_published = ReschedulePublishedConcertUseCase(self.festivals, self.notifications)
        self.cancel = CancelConcertUseCase(self.festivals, self.notifications)
        self.publish = PublishPlanningUseCase(self.festivals, self.artists, self.stages, self.notifications)
        self.iron = self.schedule.execute(ScheduleConcert(1, 1, 1, at(18), at(19)))
        self.crimson = self.schedule.execute(ScheduleConcert(1, 2, 1, at(20), at(21)))

    def stored_concert(self, concert_id):
        return self.festivals.get_by_concert_id(concert_id).find_concert(concert_id)


# ------------------------------------------------------------- programmation

def test_schedule_concert_persists_it():
    world = World()
    assert [c.id for c in GetScheduleUseCase(world.festivals).execute(1)] == [world.iron.id, world.crimson.id]


@pytest.mark.parametrize("command", [
    ScheduleConcert(festival_id=99, artist_id=1, stage_id=1, start_time=at(12), end_time=at(13)),
    ScheduleConcert(festival_id=1, artist_id=99, stage_id=1, start_time=at(12), end_time=at(13)),
    ScheduleConcert(festival_id=1, artist_id=1, stage_id=99, start_time=at(12), end_time=at(13)),
])
def test_schedule_requires_existing_references(command):  # R4
    with pytest.raises(NotFound):
        World().schedule.execute(command)


def test_schedule_with_invalid_slot_is_refused_before_loading_anything():  # R1
    world = World()
    saves = world.festivals.save_count
    with pytest.raises(RuleViolation):
        world.schedule.execute(ScheduleConcert(1, 1, 2, at(15), at(14)))
    assert world.festivals.save_count == saves


# --------------------------------------------------------------- déplacement

def test_reschedule_saves_then_notifies():
    world = World()
    result = world.reschedule.execute(RescheduleConcert(world.crimson.id, at(22), at(23)))

    assert result.warnings == []
    assert world.stored_concert(world.crimson.id).slot.start == at(22)
    assert world.notifier.sent == [(f"Modification du concert #{world.crimson.id}",
                                    "Concert déplacé au 2027-06-18T22:00:00 (fin 2027-06-18T23:00:00)")]


def test_conflicting_reschedule_is_neither_saved_nor_notified():  # Défaut 1
    world = World()
    saves = world.festivals.save_count
    with pytest.raises(SchedulingConflict):
        world.reschedule.execute(RescheduleConcert(world.crimson.id, at(18, 30), at(19, 30)))
    assert world.festivals.save_count == saves
    assert world.stored_concert(world.crimson.id).slot.start == at(20)
    assert world.notifier.sent == []


def test_reschedule_unknown_concert():
    with pytest.raises(NotFound):
        World().reschedule.execute(RescheduleConcert(999, at(22), at(23)))


def test_notification_failure_does_not_cancel_the_reschedule():  # Défaut 2
    world = World(notifier=FailingNotifier())

    result = world.reschedule.execute(RescheduleConcert(world.crimson.id, at(22), at(23)))

    assert result.value.slot.start == at(22)
    assert len(result.warnings) == 1 and "enregistrée" in result.warnings[0]
    assert world.stored_concert(world.crimson.id).slot.start == at(22)


# ------------------------------------------------------------ publication

def test_publish_then_ordinary_reschedule_is_refused():  # Défaut 3
    world = World()
    world.publish.execute(PublishPlanning(1))
    with pytest.raises(InvalidStateTransition):
        world.reschedule.execute(RescheduleConcert(world.crimson.id, at(22), at(23)))
    assert world.stored_concert(world.crimson.id).slot.start == at(20)


def test_published_reschedule_procedure_saves_and_notifies_with_reason():
    world = World()
    world.publish.execute(PublishPlanning(1))
    world.notifier.sent.clear()

    world.reschedule_published.execute(ReschedulePublishedConcert(world.crimson.id, at(22), at(23), "Retard d'avion"))

    assert world.stored_concert(world.crimson.id).slot.start == at(22)
    assert "Retard d'avion" in world.notifier.sent[0][1]


def test_publish_notifies_and_failure_is_reported_as_warning():
    world = World(notifier=FailingNotifier())
    result = world.publish.execute(PublishPlanning(1))
    assert result.value.is_published
    assert world.festivals.get(1).is_published
    assert result.warnings


def test_cancel_concert():
    world = World()
    world.cancel.execute(CancelConcert(world.iron.id))
    assert world.stored_concert(world.iron.id).status is ConcertStatus.CANCELLED
    assert world.notifier.sent[0][0] == f"Annulation du concert #{world.iron.id}"
