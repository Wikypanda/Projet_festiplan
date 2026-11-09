"""Tests de l'adaptateur de persistance : aller-retour domaine <-> SQLite."""
from datetime import datetime

import pytest

from app.adapters.persistence.repositories import (SqlAlchemyArtistRepository, SqlAlchemyFestivalRepository,
                                                   SqlAlchemyStageRepository)
from app.domain.artist import Artist
from app.domain.festival import ConcertStatus, Festival, PlanningStatus
from app.domain.stage import Stage
from app.domain.value_objects import EquipmentSet, FestivalPeriod, TimeSlot


@pytest.fixture()
def session(session_factory):
    with session_factory() as s:
        yield s


@pytest.fixture()
def saved_festival(session):
    """Festival enregistré avec une scène, un artiste et un concert."""
    festivals = SqlAlchemyFestivalRepository(session)
    festival = Festival(id=None, name="Hellforge", location="Clisson",
                        period=FestivalPeriod(datetime(2027, 6, 18, 10), datetime(2027, 6, 20, 23, 59)))
    festivals.save(festival)
    stage = Stage(id=None, festival_id=festival.id, name="Mainstage", capacity=50000,
                  available_equipment=EquipmentSet.of(["large_rigging", "pyrotechnics"]))
    SqlAlchemyStageRepository(session).add(stage)
    artist = Artist(id=None, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["large_rigging"]))
    SqlAlchemyArtistRepository(session).add(artist)
    festival.schedule_concert(artist, stage, TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19)))
    festivals.save(festival)
    return festival


def test_festival_aggregate_round_trip(session, saved_festival):
    loaded = SqlAlchemyFestivalRepository(session).get(saved_festival.id)

    assert loaded.name == "Hellforge"
    assert loaded.period == saved_festival.period
    assert loaded.status is PlanningStatus.PREPARATION
    assert len(loaded.concerts) == 1
    concert = loaded.concerts[0]
    assert concert.id is not None and concert.festival_id == saved_festival.id
    assert concert.slot == TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19))


def test_saving_aggregate_persists_concert_changes_and_status(session, saved_festival):
    repo = SqlAlchemyFestivalRepository(session)
    concert_id = saved_festival.concerts[0].id
    festival = repo.get_by_concert_id(concert_id)
    festival.reschedule_concert(concert_id, TimeSlot(datetime(2027, 6, 19, 20), datetime(2027, 6, 19, 21)))
    festival.cancel_concert(concert_id)
    festival.status = PlanningStatus.PUBLISHED
    repo.save(festival)

    reloaded = repo.get(festival.id)
    assert reloaded.is_published
    assert reloaded.concerts[0].slot.start == datetime(2027, 6, 19, 20)
    assert reloaded.concerts[0].status is ConcertStatus.CANCELLED


def test_unknown_ids_return_none(session):
    assert SqlAlchemyFestivalRepository(session).get(42) is None
    assert SqlAlchemyFestivalRepository(session).get_by_concert_id(42) is None
    assert SqlAlchemyArtistRepository(session).get(42) is None


def test_equipment_is_mapped_to_value_object(session, saved_festival):
    artist = SqlAlchemyArtistRepository(session).get_by_name("Iron Vow")
    stage = SqlAlchemyStageRepository(session).list_for_festival(saved_festival.id)[0]
    assert artist.required_equipment == EquipmentSet.of(["large_rigging"])
    assert stage.available_equipment.as_list() == ["large_rigging", "pyrotechnics"]
