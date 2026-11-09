"""Tests de l'adaptateur HTTP : routes, codes de retour, sérialisation."""


def create_festival(client, **overrides):
    payload = {"name": "Hellforge Open Air", "location": "Clisson",
               "start_date": "2027-06-18T10:00:00", "end_date": "2027-06-20T23:59:00", **overrides}
    return client.post("/festivals", json=payload)


def setup_one_concert(client):
    fid = create_festival(client).json()["id"]
    stage = client.post("/stages", json={"festival_id": fid, "name": "Mainstage", "capacity": 50000,
                                         "available_equipment": ["large_rigging"]}).json()
    artist = client.post("/artists", json={"name": "Iron Vow", "genre": "Heavy",
                                           "required_equipment": ["large_rigging"]}).json()
    concert = client.post("/concerts", json={"festival_id": fid, "artist_id": artist["id"], "stage_id": stage["id"],
                                             "start_time": "2027-06-18T18:00:00",
                                             "end_time": "2027-06-18T19:00:00"}).json()
    return fid, stage, artist, concert


# ------------------------------------------- tests repris du projet initial

def test_health_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_artist_name_must_be_a_string(client):
    assert client.post("/artists", json={"name": 123, "genre": "Metal", "required_equipment": []}).status_code == 422


def test_concert_end_must_be_after_start(client):
    r = client.post("/concerts", json={"festival_id": 1, "artist_id": 1, "stage_id": 1,
                                       "start_time": "2027-06-18T15:00:00", "end_time": "2027-06-18T14:00:00"})
    assert r.status_code in (400, 422)


def test_festival_end_must_be_after_start(client):
    assert create_festival(client, start_date="2027-06-20T10:00:00", end_date="2027-06-19T10:00:00").status_code == 400


def test_publish_unknown_festival_returns_404(client):
    assert client.post("/festivals/999/publish").status_code == 404


def test_stage_capacity_must_be_positive(client):
    r = client.post("/stages", json={"festival_id": 1, "name": "Mainstage", "capacity": 0, "available_equipment": []})
    assert r.status_code == 422


# ------------------------------------------------------- nouveaux tests

def test_festival_lifecycle(client):
    created = create_festival(client).json()
    assert created["status"] == "preparation"
    assert client.get(f"/festivals/{created['id']}").json() == created
    assert client.get("/festivals").json() == [created]
    assert client.get("/festivals/999").status_code == 404


def test_artist_and_stage_equipment_are_returned_as_lists(client):
    fid, stage, artist, _ = setup_one_concert(client)
    assert artist["required_equipment"] == ["large_rigging"]
    assert client.get(f"/stages?festival_id={fid}").json() == [stage]
    assert client.get("/artists").json() == [artist]


def test_duplicate_artist_name_returns_400(client):
    client.post("/artists", json={"name": "Iron Vow", "genre": "Heavy"})
    assert client.post("/artists", json={"name": "Iron Vow", "genre": "Heavy"}).status_code == 400


def test_concert_requires_existing_references(client):
    fid = create_festival(client).json()["id"]
    r = client.post("/concerts", json={"festival_id": fid, "artist_id": 1, "stage_id": 1,
                                       "start_time": "2027-06-18T15:00:00", "end_time": "2027-06-18T16:00:00"})
    assert r.status_code == 404


def test_concert_on_stage_without_equipment_returns_400(client):  # R5
    fid, _, artist, _ = setup_one_concert(client)
    small = client.post("/stages", json={"festival_id": fid, "name": "Valley", "capacity": 8000}).json()
    r = client.post("/concerts", json={"festival_id": fid, "artist_id": artist["id"], "stage_id": small["id"],
                                       "start_time": "2027-06-19T15:00:00", "end_time": "2027-06-19T16:00:00"})
    assert r.status_code == 400
    assert "large_rigging" in r.json()["detail"]


def test_schedule_is_sorted_and_excludes_cancelled_concerts(client):
    fid, stage, _, first = setup_one_concert(client)
    other = client.post("/artists", json={"name": "Crimson Engine", "genre": "Thrash"}).json()
    early = client.post("/concerts", json={"festival_id": fid, "artist_id": other["id"], "stage_id": stage["id"],
                                           "start_time": "2027-06-18T12:00:00",
                                           "end_time": "2027-06-18T13:00:00"}).json()
    assert [c["id"] for c in client.get(f"/concerts/schedule/{fid}").json()] == [early["id"], first["id"]]

    cancelled = client.post(f"/concerts/{early['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert [c["id"] for c in client.get(f"/concerts?festival_id={fid}").json()] == [first["id"]]


def test_unknown_concert_returns_404(client):
    assert client.get("/concerts/999").status_code == 404
    assert client.patch("/concerts/999/reschedule", json={"start_time": "2027-06-18T18:00:00",
                                                          "end_time": "2027-06-18T19:00:00"}).status_code == 404


def test_publish_returns_published_festival_without_warning(client):
    fid, *_ = setup_one_concert(client)
    r = client.post(f"/festivals/{fid}/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published" and r.json()["warnings"] == []
    assert client.post(f"/festivals/{fid}/publish").status_code == 409  # transition déjà faite


def test_incidents(client):
    _, _, _, concert = setup_one_concert(client)
    r = client.post("/incidents", json={"concert_id": concert["id"], "description": "Coupure de courant",
                                        "occurred_at": "2027-06-18T18:30:00"})
    assert r.status_code == 201
    assert client.get(f"/incidents?concert_id={concert['id']}").json() == [r.json()]
    assert client.post("/incidents", json={"concert_id": 999, "description": "Panne"}).status_code == 404
    assert client.post("/incidents", json={"concert_id": concert["id"], "description": "    "}).status_code == 400
