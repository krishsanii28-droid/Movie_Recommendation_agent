import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from moodreel.api.main import app
    from moodreel.services import get_agent

    get_agent().typing_delay = 0
    with TestClient(app) as c:
        yield c


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        data = next((line[6:] for line in block.splitlines() if line.startswith("data: ")), None)
        if data:
            events.append(json.loads(data))
    return events


def test_health_and_meta(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["movies"] >= 100
    assert h["engines"]["llm"] == "rules"
    m = client.get("/api/meta").json()
    assert {c["id"] for c in m["chips"]} >= {
        "drained",
        "happy",
        "heartbroken",
        "stressed",
        "think",
        "party",
    }
    assert "TMDB" in m["attribution"]["tmdb"] and "JustWatch" in m["attribution"]["justwatch"]


def test_chat_streams_sse_events(client):
    with client.stream(
        "POST", "/api/chat", json={"user_id": "api-u1", "message": "long day, want something cosy"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())
    events = parse_sse(body)
    types = [e["type"] for e in events]
    assert types[0] == "session" and types[-1] == "done"
    assert "mood" in types and "delta" in types and "recommendations" in types
    recs = next(e for e in events if e["type"] == "recommendations")["items"]
    assert 3 <= len(recs) <= 5
    assert {"movie", "reason", "slot", "why"} <= set(recs[0])


def test_chat_sync_followup_flow(client):
    first = client.post(
        "/api/chat/sync", json={"user_id": "api-u2", "message": "feeling down"}
    ).json()
    assert first["question"] and first["options"]
    second = client.post(
        "/api/chat/sync",
        json={
            "user_id": "api-u2",
            "session_id": first["session_id"],
            "message": first["options"][1],
        },
    ).json()
    assert second["recommendations"] and second["mood"]["goal"] == "shift"


def test_chat_validation(client):
    assert client.post("/api/chat/sync", json={"message": "hi"}).status_code == 422
    assert client.post("/api/chat/sync", json={"user_id": "x", "energy": 3}).status_code == 422


def test_group_and_surprise(client):
    g = client.post(
        "/api/group/sync",
        json={
            "user_id": "api-g",
            "members": [
                {"name": "Asha", "mood": "tired"},
                {"name": "Ravi", "mood": "want to laugh"},
            ],
        },
    ).json()
    assert g["recommendations"] and "Asha" in g["message"]
    assert (
        client.post(
            "/api/group/sync", json={"user_id": "x", "members": [{"name": "A", "mood": "ok"}]}
        ).status_code
        == 422
    )
    s = client.post("/api/surprise/sync", json={"user_id": "api-s", "languages": ["ta"]}).json()
    assert s["recommendations"] and all(
        r["movie"]["language"] == "ta" for r in s["recommendations"]
    )
    with client.stream("POST", "/api/surprise", json={"user_id": "api-s"}) as r:
        assert "recommendations" in "".join(r.iter_text())


def test_feedback_watchlist_and_moods(client):
    user = "api-u3"
    reply = client.post(
        "/api/chat/sync", json={"user_id": user, "message": "so happy today, want something fun"}
    ).json()
    movie_id = reply["recommendations"][0]["movie"]["id"]

    assert client.post(
        "/api/feedback", json={"user_id": user, "movie_id": movie_id, "signal": "loved"}
    ).json()["ok"]
    assert (
        client.post(
            "/api/feedback", json={"user_id": user, "movie_id": movie_id, "signal": "meh"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/feedback", json={"user_id": user, "movie_id": 1, "signal": "seen"}
        ).status_code
        == 404
    )
    assert movie_id in client.get(f"/api/users/{user}/history").json()["loved"]

    assert client.post("/api/watchlist", json={"user_id": user, "movie_id": movie_id}).json()["ok"]
    client.post("/api/watchlist", json={"user_id": user, "movie_id": movie_id})  # idempotent
    wl = client.get("/api/watchlist", params={"user_id": user}).json()
    assert len(wl) == 1 and wl[0]["movie"]["id"] == movie_id
    client.delete(f"/api/watchlist/{movie_id}", params={"user_id": user})
    assert client.get("/api/watchlist", params={"user_id": user}).json() == []

    moods = client.get("/api/moods", params={"user_id": user}).json()
    assert moods["counts"].get("happy", 0) >= 1 and moods["top"] == "happy"
    assert moods["labels"]["happy"]["emoji"] == "😄"


def test_movie_endpoint(client):
    movie_id = client.post("/api/surprise/sync", json={"user_id": "m"}).json()["recommendations"][
        0
    ]["movie"]["id"]
    assert client.get(f"/api/movies/{movie_id}").json()["id"] == movie_id
    assert client.get("/api/movies/1").status_code == 404
