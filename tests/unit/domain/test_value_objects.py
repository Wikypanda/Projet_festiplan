from datetime import datetime

import pytest

from app.domain.errors import RuleViolation
from app.domain.value_objects import EquipmentSet, FestivalPeriod, TimeSlot


def slot(start_h, end_h, day=18):
    return TimeSlot(datetime(2027, 6, day, start_h), datetime(2027, 6, day, end_h))


@pytest.mark.parametrize("start_h,end_h", [(20, 20), (21, 20)])
def test_time_slot_end_must_be_strictly_after_start(start_h, end_h):  # R1
    with pytest.raises(RuleViolation):
        slot(start_h, end_h)


def test_overlapping_slots():
    assert slot(18, 20).overlaps(slot(19, 21))
    assert slot(18, 22).overlaps(slot(19, 20))  # inclus


def test_adjacent_slots_do_not_overlap():
    assert not slot(18, 19).overlaps(slot(19, 20))
    assert not slot(19, 20).overlaps(slot(18, 19))


def test_time_slot_is_immutable():
    with pytest.raises(AttributeError):
        slot(18, 19).start = datetime(2027, 6, 18, 10)


def test_festival_period_must_be_valid():
    with pytest.raises(RuleViolation):
        FestivalPeriod(datetime(2027, 6, 20), datetime(2027, 6, 19))


def test_festival_period_contains_slot_only_if_entirely_inside():  # R6
    period = FestivalPeriod(datetime(2027, 6, 18, 10), datetime(2027, 6, 20, 23, 59))
    assert period.contains(slot(18, 19))
    assert not period.contains(TimeSlot(datetime(2027, 6, 18, 9), datetime(2027, 6, 18, 11)))
    assert not period.contains(TimeSlot(datetime(2027, 6, 20, 23), datetime(2027, 6, 21, 1)))


def test_equipment_set_ignores_blanks_and_detects_missing_items():  # R5
    required = EquipmentSet.of(["large_rigging", " special_lighting ", ""])
    available = EquipmentSet.of(["special_lighting"])
    assert required.missing_from(available) == {"large_rigging"}
    assert EquipmentSet.of(["a", "a"]) == EquipmentSet.of(["a"])
