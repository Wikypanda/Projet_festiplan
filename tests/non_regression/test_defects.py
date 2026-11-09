"""Tests de non-régression des trois défauts initiaux.

Ces tests passent uniquement par l'API HTTP : ils ont été écrits et exécutés
AVANT la refactorisation (ils échouaient tous sur le code legacy, voir
docs/01-diagnostic.md), puis conservés pour garantir que les défauts ne
réapparaissent pas.
"""
import pytest

from app.config import settings


def _setup_planning(client):
    """Festival + 2 scènes + 3 artistes + 3 concerts, en préparation."""
    festival = client.post("/festivals", json={
        "name": "Hellforge Open Air", "location": "Clisson",
        "start_date": "2027-06-18T10:00:00", "end_date": "2027-06-20T23:59:00",
    }).json()
    fid = festival["id"]
    main = client.post("/stages", json={"festival_id": fid, "name": "Mainstage", "capacity": 50000,
                                        "available_equipment": ["large_rigging"]}).json()
    warzone = client.post("/stages", json={"festival_id": fid, "name": "Warzone", "capacity": 15000,
                                           "available_equipment": []}).json()
    iron = client.post("/artists", json={"name": "Iron Vow", "genre": "Heavy", "required_equipment": []}).json()
    crimson = client.post("/artists", json={"name": "Crimson Engine", "genre": "Thrash", "required_equipment": []}).json()
    concrete = client.post("/artists", json={"name": "Concrete Reign", "genre": "Hardcore", "required_equipment": []}).json()

    def concert(artist, stage, start, end):
        r = client.post("/concerts", json={"festival_id": fid, "artist_id": artist["id"], "stage_id": stage["id"],
                                           "start_time": start, "end_time": end})
        assert r.status_code == 201, r.text
        return r.json()

    return {
        "festival": festival,
        # Iron Vow 18h-19h sur Mainstage
        "iron_main": concert(iron, main, "2027-06-18T18:00:00", "2027-06-18T19:00:00"),
        # Crimson Engine 20h-21h sur Mainstage
        "crimson_main": concert(crimson, main, "2027-06-18T20:00:00", "2027-06-18T21:00:00"),
        # Iron Vow 21h-22h sur Warzone (2e concert du même artiste)
        "iron_warzone": concert(iron, warzone, "2027-06-18T21:00:00", "2027-06-18T22:00:00"),
        "concrete": concrete,
    }


def _reschedule(client, concert_id, start, end):
    return client.patch(f"/concerts/{concert_id}/reschedule", json={"start_time": start, "end_time": end})


# --------------------------------------------------------------------------- #
# Défaut 1 — chevauchement de concerts lors d'un déplacement
# --------------------------------------------------------------------------- #

def test_defect1_reschedule_onto_occupied_stage_is_refused(client):
    data = _setup_planning(client)
    crimson = data["crimson_main"]

    # Crimson Engine est déplacé sur le créneau d'Iron Vow, même scène.
    r = _reschedule(client, crimson["id"], "2027-06-18T18:30:00", "2027-06-18T19:30:00")

    assert r.status_code == 409
    unchanged = client.get(f"/concerts/{crimson['id']}").json()
    assert unchanged["start_time"] == "2027-06-18T20:00:00"


def test_defect1_artist_cannot_play_on_two_stages_at_the_same_time(client):
    data = _setup_planning(client)
    iron_warzone = data["iron_warzone"]

    # Iron Vow joue déjà 18h-19h sur Mainstage : on déplace son concert Warzone à 18h30.
    r = _reschedule(client, iron_warzone["id"], "2027-06-18T18:30:00", "2027-06-18T19:30:00")

    assert r.status_code == 409


def test_defect1_reschedule_outside_festival_period_is_refused(client):
    data = _setup_planning(client)

    r = _reschedule(client, data["crimson_main"]["id"], "2027-06-25T20:00:00", "2027-06-25T21:00:00")

    assert r.status_code == 400


def test_defect1_valid_reschedule_is_accepted(client):
    data = _setup_planning(client)
    crimson = data["crimson_main"]

    # 19h-20h : collé au concert d'Iron Vow (fin 19h) mais sans chevauchement.
    r = _reschedule(client, crimson["id"], "2027-06-18T19:00:00", "2027-06-18T20:00:00")

    assert r.status_code == 200
    assert r.json()["start_time"] == "2027-06-18T19:00:00"


# --------------------------------------------------------------------------- #
# Défaut 2 — échec de notification après une modification enregistrée
# --------------------------------------------------------------------------- #

@pytest.fixture()
def failing_notifications(monkeypatch):
    # Même scénario que FESTIPLAN_FAIL_NOTIFICATIONS=true décrit dans le README.
    monkeypatch.setattr(settings, "fail_notifications", True)


def test_defect2_reschedule_succeeds_even_if_notification_fails(client, failing_notifications):
    data = _setup_planning(client)
    crimson = data["crimson_main"]

    r = _reschedule(client, crimson["id"], "2027-06-18T22:00:00", "2027-06-18T23:00:00")

    # La modification est réussie : pas de 500, et l'échec de notification est signalé.
    assert r.status_code == 200
    assert r.json()["warnings"], "l'échec de la notification doit être signalé"
    saved = client.get(f"/concerts/{crimson['id']}").json()
    assert saved["start_time"] == "2027-06-18T22:00:00"


def test_defect2_publish_succeeds_even_if_notification_fails(client, failing_notifications):
    data = _setup_planning(client)
    fid = data["festival"]["id"]

    r = client.post(f"/festivals/{fid}/publish")

    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["warnings"]


# --------------------------------------------------------------------------- #
# Défaut 3 — modification d'un planning publié
# --------------------------------------------------------------------------- #

def test_defect3_ordinary_reschedule_is_refused_once_published(client):
    data = _setup_planning(client)
    crimson = data["crimson_main"]
    assert client.post(f"/festivals/{data['festival']['id']}/publish").status_code == 200

    r = _reschedule(client, crimson["id"], "2027-06-18T22:00:00", "2027-06-18T23:00:00")

    assert r.status_code == 409
    unchanged = client.get(f"/concerts/{crimson['id']}").json()
    assert unchanged["start_time"] == "2027-06-18T20:00:00"


def test_defect3_published_planning_can_be_changed_through_explicit_procedure(client):
    data = _setup_planning(client)
    crimson = data["crimson_main"]
    assert client.post(f"/festivals/{data['festival']['id']}/publish").status_code == 200

    r = client.post(f"/concerts/{crimson['id']}/published-reschedule", json={
        "start_time": "2027-06-18T22:00:00", "end_time": "2027-06-18T23:00:00",
        "reason": "Retard de l'avion du groupe",
    })

    assert r.status_code == 200
    assert r.json()["start_time"] == "2027-06-18T22:00:00"


def test_defect3_explicit_procedure_still_checks_conflicts(client):
    data = _setup_planning(client)
    crimson = data["crimson_main"]
    assert client.post(f"/festivals/{data['festival']['id']}/publish").status_code == 200

    r = client.post(f"/concerts/{crimson['id']}/published-reschedule", json={
        "start_time": "2027-06-18T18:30:00", "end_time": "2027-06-18T19:30:00",
        "reason": "Demande du tourneur",
    })

    assert r.status_code == 409


def test_defect3_new_concert_is_refused_once_published(client):
    data = _setup_planning(client)
    fid = data["festival"]["id"]
    assert client.post(f"/festivals/{fid}/publish").status_code == 200
    stage_id = data["crimson_main"]["stage_id"]

    r = client.post("/concerts", json={"festival_id": fid, "artist_id": data["concrete"]["id"], "stage_id": stage_id,
                                       "start_time": "2027-06-19T12:00:00", "end_time": "2027-06-19T13:00:00"})

    assert r.status_code == 409
