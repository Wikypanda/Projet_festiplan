from datetime import datetime

import pytest

from app.application.commands import CreateFestival, CreateStage, RegisterArtist, ReportIncident
from app.application.use_cases.catalog import CreateStageUseCase, RegisterArtistUseCase, ReportIncidentUseCase
from app.application.use_cases.festivals import CreateFestivalUseCase
from app.domain.errors import NotFound, RuleViolation
from app.domain.festival import Concert, PlanningStatus
from app.domain.value_objects import TimeSlot
from tests.fakes import InMemoryArtistRepository, InMemoryFestivalRepository, InMemoryIncidentRepository, \
    InMemoryStageRepository


def create_festival(festivals):
    return CreateFestivalUseCase(festivals).execute(
        CreateFestival("Hellforge", "Clisson", datetime(2027, 6, 18), datetime(2027, 6, 20)))


def test_create_festival_starts_in_preparation():
    festivals = InMemoryFestivalRepository()
    festival = create_festival(festivals)
    assert festival.id == 1
    assert festivals.get(1).status is PlanningStatus.PREPARATION


def test_create_festival_with_invalid_dates_is_refused():
    with pytest.raises(RuleViolation):
        CreateFestivalUseCase(InMemoryFestivalRepository()).execute(
            CreateFestival("Hellforge", "Clisson", datetime(2027, 6, 20), datetime(2027, 6, 18)))


def test_register_artist_refuses_duplicate_name():
    use_case = RegisterArtistUseCase(InMemoryArtistRepository())
    use_case.execute(RegisterArtist("Iron Vow", "Heavy", ["large_rigging"]))
    with pytest.raises(RuleViolation):
        use_case.execute(RegisterArtist("Iron Vow", "Heavy"))


def test_create_stage_requires_existing_festival():
    with pytest.raises(NotFound):
        CreateStageUseCase(InMemoryStageRepository(), InMemoryFestivalRepository()).execute(
            CreateStage(festival_id=1, name="Mainstage", capacity=100))


def test_create_stage_refuses_non_positive_capacity():  # R9 sans passer par Pydantic
    festivals = InMemoryFestivalRepository()
    create_festival(festivals)
    with pytest.raises(RuleViolation):
        CreateStageUseCase(InMemoryStageRepository(), festivals).execute(CreateStage(1, "Mainstage", 0))


class TestReportIncident:  # R10
    def setup_method(self):
        self.festivals = InMemoryFestivalRepository()
        festival = create_festival(self.festivals)
        festival.concerts.append(Concert(id=None, festival_id=1, artist_id=1, stage_id=1,
                                         slot=TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19))))
        self.festivals.save(festival)
        self.incidents = InMemoryIncidentRepository()
        self.use_case = ReportIncidentUseCase(self.incidents, self.festivals)

    def test_incident_is_recorded_for_existing_concert(self):
        incident = self.use_case.execute(ReportIncident(concert_id=1, description="Coupure de courant"))
        assert self.incidents.list(concert_id=1) == [incident]
        assert incident.occurred_at is not None

    def test_incident_on_unknown_concert_is_refused(self):
        with pytest.raises(NotFound):
            self.use_case.execute(ReportIncident(concert_id=42, description="Coupure de courant"))

    def test_incident_without_description_is_refused(self):
        with pytest.raises(RuleViolation):
            self.use_case.execute(ReportIncident(concert_id=1, description="   "))
