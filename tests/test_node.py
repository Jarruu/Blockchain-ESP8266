import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node import create_app


def make_client(tmp):
    app = create_app(port=5999, peers=[], difficulty=2,
                     api_key="k", data_dir=tmp)
    return app.test_client()


def test_status_and_chain(tmp_path):
    c = make_client(str(tmp_path))
    r = c.get("/status")
    assert r.status_code == 200
    assert r.get_json()["height"] == 1


def test_mine_returns_block(tmp_path):
    c = make_client(str(tmp_path))
    r = c.post("/mine", json={"miner": "kelompok6"})
    assert r.status_code == 200
    assert r.get_json()["block"]["hash"].startswith("00")


def test_trigger_requires_api_key(tmp_path):
    c = make_client(str(tmp_path))
    assert c.post("/trigger", json={"miner": "esp"}).status_code == 401
    ok = c.post("/trigger", json={"miner": "esp"}, headers={"X-API-Key": "k"})
    assert ok.status_code == 200
    assert ok.get_json()["reward"] == 50.0


def test_bad_json_returns_400(tmp_path):
    c = make_client(str(tmp_path))
    r = c.post("/transactions/new", data="not json",
               content_type="application/json")
    assert r.status_code == 400


def test_zero_amount_rejected(tmp_path):
    c = make_client(str(tmp_path))
    r = c.post("/transactions/new",
               json={"sender": "a", "recipient": "b", "amount": 0})
    assert r.status_code == 400


def test_missing_field_rejected(tmp_path):
    c = make_client(str(tmp_path))
    r = c.post("/transactions/new", json={"sender": "a", "amount": 5})
    assert r.status_code == 400


def test_resolve_survives_dead_peer(tmp_path):
    c = make_client(str(tmp_path))
    r = c.post("/nodes/register", json={"nodes": ["http://127.0.0.1:1"]})
    assert r.status_code == 200
    res = c.get("/nodes/resolve")          # peer mati -> tidak boleh 500
    assert res.status_code == 200


def test_chain_persisted_across_restart(tmp_path):
    c = make_client(str(tmp_path))
    c.post("/mine", json={"miner": "kelompok6"})
    c2 = make_client(str(tmp_path))        # app baru, data_dir sama
    assert c2.get("/status").get_json()["height"] == 2
