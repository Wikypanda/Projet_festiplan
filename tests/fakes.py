"""Doubles de test : implémentations en mémoire des ports.

Les agrégats sont copiés à l'enregistrement et à la lecture, comme le ferait
une vraie base : une modification non enregistrée n'est donc jamais visible.
"""
from copy import deepcopy
from itertools import count

from app.application.ports import ArtistRepository, FestivalRepository, IncidentRepository, Notifier, StageRepository


class InMemoryFestivalRepository(FestivalRepository):
    def __init__(self):
        self.rows = {}
        self.save_count = 0
        self._festival_ids = count(1)
        self._concert_ids = count(1)

    def get(self, festival_id):
        return deepcopy(self.rows.get(festival_id))

    def get_by_concert_id(self, concert_id):
        for festival in self.rows.values():
            if any(c.id == concert_id for c in festival.concerts):
                return deepcopy(festival)
        return None

    def list(self):
        return [deepcopy(f) for f in self.rows.values()]

    def save(self, festival):
        if festival.id is None:
            festival.id = next(self._festival_ids)
        for concert in festival.concerts:
            concert.festival_id = festival.id
            if concert.id is None:
                concert.id = next(self._concert_ids)
        stored = deepcopy(festival)
        stored.pull_events()  # les événements ne sont pas persistés
        self.rows[festival.id] = stored
        self.save_count += 1


class InMemoryArtistRepository(ArtistRepository):
    def __init__(self, *artists):
        self.rows = {}
        for artist in artists:
            self.add(artist)

    def get(self, artist_id):
        return self.rows.get(artist_id)

    def get_by_name(self, name):
        return next((a for a in self.rows.values() if a.name == name), None)

    def list(self):
        return list(self.rows.values())

    def add(self, artist):
        artist.id = artist.id or len(self.rows) + 1
        self.rows[artist.id] = artist


class InMemoryStageRepository(StageRepository):
    def __init__(self, *stages):
        self.rows = {}
        for stage in stages:
            self.add(stage)

    def get(self, stage_id):
        return self.rows.get(stage_id)

    def list_for_festival(self, festival_id):
        return [s for s in self.rows.values() if s.festival_id == festival_id]

    def add(self, stage):
        stage.id = stage.id or len(self.rows) + 1
        self.rows[stage.id] = stage


class InMemoryIncidentRepository(IncidentRepository):
    def __init__(self):
        self.rows = []

    def add(self, incident):
        incident.id = len(self.rows) + 1
        self.rows.append(incident)

    def list(self, concert_id=None):
        return [i for i in self.rows if concert_id is None or i.concert_id == concert_id]


class SpyNotifier(Notifier):
    """Enregistre les notifications envoyées."""

    def __init__(self):
        self.sent = []

    def send(self, subject, message):
        self.sent.append((subject, message))


class FailingNotifier(Notifier):
    """Simule un service de notification en panne."""

    def send(self, subject, message):
        raise RuntimeError("service de notification indisponible")
