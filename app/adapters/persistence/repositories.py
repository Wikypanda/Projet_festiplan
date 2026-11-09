"""Adaptateurs de persistance : implémentent les ports de app/application/ports.py."""
from sqlalchemy.orm import Session

from app.adapters.persistence.models import ArtistModel, ConcertModel, FestivalModel, IncidentModel, StageModel
from app.application.ports import ArtistRepository, FestivalRepository, IncidentRepository, StageRepository
from app.domain.artist import Artist
from app.domain.festival import Concert, ConcertStatus, Festival, PlanningStatus
from app.domain.incident import Incident
from app.domain.stage import Stage
from app.domain.value_objects import EquipmentSet, FestivalPeriod, TimeSlot


def _equipment_from_db(value: str) -> EquipmentSet:
    return EquipmentSet.of(value.split(","))


def _equipment_to_db(equipment: EquipmentSet) -> str:
    return ",".join(equipment.as_list())


class SqlAlchemyFestivalRepository(FestivalRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, festival_id):
        row = self.session.get(FestivalModel, festival_id)
        return self._to_domain(row) if row else None

    def get_by_concert_id(self, concert_id):
        concert = self.session.get(ConcertModel, concert_id)
        return self.get(concert.festival_id) if concert else None

    def list(self):
        rows = self.session.query(FestivalModel).order_by(FestivalModel.id).all()
        return [self._to_domain(row) for row in rows]

    def save(self, festival):
        try:
            self._write(festival)
            self.session.commit()  # tout l'agrégat est enregistré en une seule transaction
        except Exception:
            self.session.rollback()
            raise

    def _write(self, festival: Festival) -> None:
        row = self.session.get(FestivalModel, festival.id) if festival.id else None
        if row is None:
            row = FestivalModel()
            self.session.add(row)
        row.name = festival.name
        row.location = festival.location
        row.start_date = festival.period.start
        row.end_date = festival.period.end
        row.status = festival.status.value
        self.session.flush()
        festival.id = row.id

        for concert in festival.concerts:
            concert_row = self.session.get(ConcertModel, concert.id) if concert.id else None
            if concert_row is None:
                concert_row = ConcertModel(festival_id=row.id)
                self.session.add(concert_row)
            concert_row.artist_id = concert.artist_id
            concert_row.stage_id = concert.stage_id
            concert_row.start_time = concert.slot.start
            concert_row.end_time = concert.slot.end
            concert_row.status = concert.status.value
            self.session.flush()
            concert.id = concert_row.id
            concert.festival_id = row.id

    @staticmethod
    def _to_domain(row: FestivalModel) -> Festival:
        return Festival(
            id=row.id, name=row.name, location=row.location,
            period=FestivalPeriod(row.start_date, row.end_date),
            status=PlanningStatus(row.status),
            concerts=[Concert(id=c.id, festival_id=c.festival_id, artist_id=c.artist_id, stage_id=c.stage_id,
                              slot=TimeSlot(c.start_time, c.end_time), status=ConcertStatus(c.status))
                      for c in row.concerts],
        )


class SqlAlchemyArtistRepository(ArtistRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, artist_id):
        row = self.session.get(ArtistModel, artist_id)
        return self._to_domain(row) if row else None

    def get_by_name(self, name):
        row = self.session.query(ArtistModel).filter(ArtistModel.name == name).first()
        return self._to_domain(row) if row else None

    def list(self):
        return [self._to_domain(r) for r in self.session.query(ArtistModel).order_by(ArtistModel.name).all()]

    def add(self, artist):
        row = ArtistModel(name=artist.name, genre=artist.genre,
                          required_equipment=_equipment_to_db(artist.required_equipment))
        self.session.add(row)
        self.session.commit()
        artist.id = row.id

    @staticmethod
    def _to_domain(row: ArtistModel) -> Artist:
        return Artist(id=row.id, name=row.name, genre=row.genre,
                      required_equipment=_equipment_from_db(row.required_equipment))


class SqlAlchemyStageRepository(StageRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, stage_id):
        row = self.session.get(StageModel, stage_id)
        return self._to_domain(row) if row else None

    def list_for_festival(self, festival_id):
        rows = self.session.query(StageModel).filter(StageModel.festival_id == festival_id).order_by(StageModel.id)
        return [self._to_domain(r) for r in rows.all()]

    def add(self, stage):
        row = StageModel(festival_id=stage.festival_id, name=stage.name, capacity=stage.capacity,
                         available_equipment=_equipment_to_db(stage.available_equipment))
        self.session.add(row)
        self.session.commit()
        stage.id = row.id

    @staticmethod
    def _to_domain(row: StageModel) -> Stage:
        return Stage(id=row.id, festival_id=row.festival_id, name=row.name, capacity=row.capacity,
                     available_equipment=_equipment_from_db(row.available_equipment))


class SqlAlchemyIncidentRepository(IncidentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, incident):
        row = IncidentModel(concert_id=incident.concert_id, description=incident.description,
                            occurred_at=incident.occurred_at, resolved=incident.resolved)
        self.session.add(row)
        self.session.commit()
        incident.id = row.id

    def list(self, concert_id=None):
        query = self.session.query(IncidentModel)
        if concert_id is not None:
            query = query.filter(IncidentModel.concert_id == concert_id)
        return [Incident(id=r.id, concert_id=r.concert_id, description=r.description,
                         occurred_at=r.occurred_at, resolved=r.resolved)
                for r in query.order_by(IncidentModel.occurred_at.desc()).all()]
