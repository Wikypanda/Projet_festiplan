from datetime import datetime

import pytest

from app.domain.artist import Artist
from app.domain.errors import InvalidStateTransition, RuleViolation
from app.domain.festival import Concert, ConcertStatus
from app.domain.incident import Incident
from app.domain.stage import Stage
from app.domain.value_objects import TimeSlot


@pytest.mark.parametrize("capacity", [0, -100])
def test_stage_capacity_must_be_strictly_positive(capacity):  # R9
    with pytest.raises(RuleViolation):
        Stage(id=None, festival_id=1, name="Mainstage", capacity=capacity)


@pytest.mark.parametrize("description", ["", "   "])
def test_incident_description_must_not_be_blank(description):  # R10
    with pytest.raises(RuleViolation):
        Incident(id=None, concert_id=1, description=description, occurred_at=datetime(2027, 6, 18))


def test_artist_name_is_required():
    with pytest.raises(RuleViolation):
        Artist(id=None, name=" ", genre="Doom")


def test_cancelled_concert_cannot_be_moved_or_cancelled_again():
    concert = Concert(id=1, festival_id=1, artist_id=1, stage_id=1,
                      slot=TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19)))
    concert.cancel()
    assert concert.status is ConcertStatus.CANCELLED
    with pytest.raises(InvalidStateTransition):
        concert.cancel()
    with pytest.raises(InvalidStateTransition):
        concert.move_to(TimeSlot(datetime(2027, 6, 18, 20), datetime(2027, 6, 18, 21)))
