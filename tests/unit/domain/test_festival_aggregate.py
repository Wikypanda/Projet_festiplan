from datetime import datetime

import pytest

from app.domain.artist import Artist
from app.domain.errors import InvalidStateTransition, PlanningNotPublishable, RuleViolation, SchedulingConflict
from app.domain.events import ConcertCancelled, ConcertRescheduled, PlanningPublished
from app.domain.festival import Concert, Festival, PlanningStatus
from app.domain.stage import Stage
from app.domain.value_objects import EquipmentSet, FestivalPeriod, TimeSlot

MAIN = Stage(id=1, festival_id=1, name="Mainstage", capacity=50000,
             available_equipment=EquipmentSet.of(["large_rigging", "special_lighting"]))
WARZONE = Stage(id=2, festival_id=1, name="Warzone", capacity=15000)
OTHER_FESTIVAL_STAGE = Stage(id=3, festival_id=99, name="Ailleurs", capacity=100)
IRON = Artist(id=1, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["large_rigging"]))
CRIMSON = Artist(id=2, name="Crimson Engine", genre="Thrash")
ARTISTS = {a.id: a for a in (IRON, CRIMSON)}
STAGES = {s.id: s for s in (MAIN, WARZONE)}


def slot(start_h, end_h, day=18):
    return TimeSlot(datetime(2027, 6, day, start_h), datetime(2027, 6, day, end_h))


def new_festival(concerts=None):
    return Festival(id=1, name="Hellforge", location="Clisson",
                    period=FestivalPeriod(datetime(2027, 6, 18, 10), datetime(2027, 6, 20, 23, 59)),
                    concerts=concerts or [])


def festival_with_two_concerts():
    """Iron Vow 18h-19h Mainstage (#1) ; Crimson Engine 20h-21h Mainstage (#2)."""
    return new_festival([
        Concert(id=1, festival_id=1, artist_id=IRON.id, stage_id=MAIN.id, slot=slot(18, 19)),
        Concert(id=2, festival_id=1, artist_id=CRIMSON.id, stage_id=MAIN.id, slot=slot(20, 21)),
    ])


# ------------------------------------------------------------- programmation

def test_schedule_concert_adds_it_to_the_planning():
    festival = new_festival()
    concert = festival.schedule_concert(CRIMSON, WARZONE, slot(18, 19))
    assert festival.schedule() == [concert]


def test_schedule_refuses_overlap_on_same_stage():  # R2
    festival = festival_with_two_concerts()
    with pytest.raises(SchedulingConflict):
        festival.schedule_concert(CRIMSON, MAIN, slot(18, 19, day=18))


def test_schedule_refuses_artist_on_two_stages_at_same_time():  # R3
    festival = festival_with_two_concerts()
    with pytest.raises(SchedulingConflict, match="artiste"):
        festival.schedule_concert(CRIMSON, WARZONE, slot(20, 22))  # Crimson joue déjà 20h-21h sur Mainstage


def test_schedule_refuses_stage_of_another_festival():  # R4
    with pytest.raises(RuleViolation):
        new_festival().schedule_concert(CRIMSON, OTHER_FESTIVAL_STAGE, slot(18, 19))


def test_schedule_refuses_stage_without_required_equipment():  # R5
    with pytest.raises(RuleViolation, match="large_rigging"):
        new_festival().schedule_concert(IRON, WARZONE, slot(18, 19))


def test_schedule_refuses_concert_outside_festival_period():  # R6
    with pytest.raises(RuleViolation):
        new_festival().schedule_concert(CRIMSON, WARZONE, slot(18, 19, day=25))


# --------------------------------------------------------------- déplacement

def test_reschedule_refuses_overlap_on_same_stage():  # Défaut 1 / R2
    festival = festival_with_two_concerts()
    with pytest.raises(SchedulingConflict):
        festival.reschedule_concert(2, TimeSlot(datetime(2027, 6, 18, 18, 30), datetime(2027, 6, 18, 19, 30)))
    assert festival.find_concert(2).slot == slot(20, 21)  # rien n'a été modifié
    assert festival.pull_events() == []


def test_reschedule_refuses_artist_playing_elsewhere():  # Défaut 1 / R3
    festival = festival_with_two_concerts()
    festival.concerts.append(Concert(id=3, festival_id=1, artist_id=IRON.id, stage_id=WARZONE.id, slot=slot(21, 22)))
    with pytest.raises(SchedulingConflict, match="artiste"):
        festival.reschedule_concert(3, slot(18, 19))


def test_valid_reschedule_moves_concert_and_records_event():
    festival = festival_with_two_concerts()
    concert = festival.reschedule_concert(2, slot(19, 20))  # collé au concert #1, sans chevauchement
    assert concert.slot == slot(19, 20)
    assert festival.pull_events() == [ConcertRescheduled(1, 2, slot(20, 21), slot(19, 20))]


def test_concert_can_be_moved_onto_its_own_previous_slot():
    festival = festival_with_two_concerts()
    festival.reschedule_concert(2, slot(20, 22))  # chevauche son ancien créneau : pas un conflit
    assert festival.find_concert(2).slot == slot(20, 22)


def test_cancelled_concert_frees_its_slot():
    festival = festival_with_two_concerts()
    festival.cancel_concert(1)
    festival.reschedule_concert(2, slot(18, 19))
    assert [c.id for c in festival.schedule()] == [2]
    assert isinstance(festival.pull_events()[0], ConcertCancelled)


# ------------------------------------------------------ publication (R7, R8)

def test_publish_changes_state_and_records_event():
    festival = festival_with_two_concerts()
    festival.publish(ARTISTS, STAGES)
    assert festival.status is PlanningStatus.PUBLISHED
    assert festival.pull_events() == [PlanningPublished(1, "Hellforge")]


def test_publish_twice_is_refused():
    festival = festival_with_two_concerts()
    festival.publish(ARTISTS, STAGES)
    with pytest.raises(InvalidStateTransition):
        festival.publish(ARTISTS, STAGES)


def test_publish_refuses_inconsistent_planning():  # R8 (ex. données héritées du code legacy)
    festival = new_festival([
        Concert(id=1, festival_id=1, artist_id=IRON.id, stage_id=MAIN.id, slot=slot(18, 19)),
        Concert(id=2, festival_id=1, artist_id=CRIMSON.id, stage_id=MAIN.id, slot=slot(18, 20)),
    ])
    with pytest.raises(PlanningNotPublishable) as exc:
        festival.publish(ARTISTS, STAGES)
    assert len(exc.value.problems) == 2
    assert festival.status is PlanningStatus.PREPARATION


@pytest.mark.parametrize("operation", [
    lambda f: f.schedule_concert(CRIMSON, WARZONE, slot(15, 16)),
    lambda f: f.reschedule_concert(2, slot(22, 23)),
    lambda f: f.cancel_concert(2),
])
def test_ordinary_operations_are_refused_once_published(operation):  # Défaut 3 / R7
    festival = festival_with_two_concerts()
    festival.publish(ARTISTS, STAGES)
    with pytest.raises(InvalidStateTransition):
        operation(festival)


def test_published_planning_can_be_changed_with_explicit_procedure():
    festival = festival_with_two_concerts()
    festival.publish(ARTISTS, STAGES)
    festival.pull_events()

    festival.reschedule_published_concert(2, slot(22, 23), reason="Retard d'avion")

    assert festival.find_concert(2).slot == slot(22, 23)
    assert festival.is_published
    assert festival.pull_events()[0].reason == "Retard d'avion"


def test_explicit_procedure_requires_a_reason_and_keeps_checking_rules():
    festival = festival_with_two_concerts()
    festival.publish(ARTISTS, STAGES)
    with pytest.raises(RuleViolation):
        festival.reschedule_published_concert(2, slot(22, 23), reason="  ")
    with pytest.raises(SchedulingConflict):
        festival.reschedule_published_concert(2, slot(18, 19), reason="Demande du tourneur")


def test_explicit_procedure_is_only_for_published_planning():
    with pytest.raises(InvalidStateTransition):
        festival_with_two_concerts().reschedule_published_concert(2, slot(22, 23), reason="Motif")
