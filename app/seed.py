"""Réinitialise la base et charge les données de démonstration.

Les données sont créées via les cas d'utilisation : elles respectent donc
toutes les règles métier (impossible de créer un planning incohérent).
"""
from datetime import datetime

from app.adapters.notifications.fake_email_notifier import FakeEmailNotifier
from app.adapters.persistence.database import Base, SessionLocal, engine, init_db
from app.application.commands import CreateFestival, CreateStage, RegisterArtist, ScheduleConcert
from app.bootstrap import UseCases

ARTISTS = [
    ("Iron Vow", "Heavy metal", ["large_rigging", "special_lighting"]),
    ("Crimson Engine", "Thrash metal", ["special_lighting"]),
    ("The Last Citadel", "Power metal", ["large_rigging"]),
    ("Concrete Reign", "Hardcore", []),
    ("Ashes of Tomorrow", "Metalcore", ["special_lighting"]),
    ("Static Violence", "Punk", []),
    ("Hollow Mountain", "Stoner", ["special_lighting"]),
    ("Solar Funeral", "Doom metal", []),
    ("Desert Crown", "Sludge", []),
    ("Winter Throne", "Black metal", ["special_lighting"]),
    ("Nocturnal Veil", "Black metal", []),
    ("Pale Kingdom", "Atmospheric metal", ["special_lighting"]),
]
STAGES = [
    ("Mainstage", 50000, ["large_rigging", "special_lighting", "pyrotechnics"]),
    ("Warzone", 15000, ["special_lighting"]),
    ("Valley", 8000, ["special_lighting"]),
    ("Temple", 10000, ["special_lighting"]),
]
SHOWS = [
    ("Iron Vow", "Mainstage", "2027-06-18T18:00:00", "2027-06-18T19:00:00"),
    ("Crimson Engine", "Mainstage", "2027-06-18T19:30:00", "2027-06-18T20:30:00"),
    ("The Last Citadel", "Mainstage", "2027-06-18T21:00:00", "2027-06-18T22:00:00"),
    ("Concrete Reign", "Warzone", "2027-06-18T17:00:00", "2027-06-18T17:45:00"),
    ("Ashes of Tomorrow", "Warzone", "2027-06-18T18:15:00", "2027-06-18T19:00:00"),
    ("Hollow Mountain", "Valley", "2027-06-18T19:00:00", "2027-06-18T20:00:00"),
    ("Solar Funeral", "Valley", "2027-06-18T20:30:00", "2027-06-18T21:30:00"),
    ("Winter Throne", "Temple", "2027-06-18T20:00:00", "2027-06-18T21:00:00"),
    ("Nocturnal Veil", "Temple", "2027-06-18T21:30:00", "2027-06-18T22:30:00"),
    ("Static Violence", "Warzone", "2027-06-19T14:00:00", "2027-06-19T14:45:00"),
    ("Desert Crown", "Valley", "2027-06-19T15:00:00", "2027-06-19T16:00:00"),
    ("Pale Kingdom", "Temple", "2027-06-19T16:30:00", "2027-06-19T17:30:00"),
    ("Iron Vow", "Mainstage", "2027-06-19T21:00:00", "2027-06-19T22:00:00"),
    ("Crimson Engine", "Mainstage", "2027-06-20T20:00:00", "2027-06-20T21:00:00"),
]


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    init_db()
    with SessionLocal() as session:
        uc = UseCases(session, FakeEmailNotifier())
        festival = uc.create_festival.execute(CreateFestival(
            "Hellforge Open Air", "Clisson-sur-Rivière", dt("2027-06-18T10:00:00"), dt("2027-06-20T23:59:00")))
        artists = {name: uc.register_artist.execute(RegisterArtist(name, genre, equipment))
                   for name, genre, equipment in ARTISTS}
        stages = {name: uc.create_stage.execute(CreateStage(festival.id, name, capacity, equipment))
                  for name, capacity, equipment in STAGES}
        for artist, stage, start, end in SHOWS:
            uc.schedule_concert.execute(ScheduleConcert(festival.id, artists[artist].id, stages[stage].id,
                                                        dt(start), dt(end)))
    print(f"Données chargées : Hellforge Open Air, {len(STAGES)} scènes, {len(ARTISTS)} artistes, "
          f"{len(SHOWS)} concerts.")


if __name__ == "__main__":
    seed()
