"""Kontrak JSON yang diandalkan parser sketch Wokwi (firmware/wokwi_node-*).

Sketch mem-parse respons `/snapshot` dengan pencarian string, bukan parser JSON
penuh. Test ini meniru pola ekstraksi yang sama (toleran spasi setelah ':')
terhadap output Flask ASLI, dan memverifikasi keterkaitan chain yang dicek
light node. Kalau Flask mengubah format JSON-nya, test ini gagal lebih dulu
sebelum sketch rusak di depan kelas.
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node import create_app


def _extract_values(body: str, key: str) -> list[str]:
    """Port dari extractValues() di sketch: string berkuote atau angka."""
    pat = re.compile(r'"%s":\s*(?:"([^"]*)"|(-?[\d.]+))' % re.escape(key))
    return [a or b for a, b in pat.findall(body)]


def _verify_chain(prev: list[str], hashes: list[str], idx: list[str]) -> bool:
    """Port dari verifyChain() di sketch."""
    if not idx:
        return False
    if prev[0] != "0":
        return False
    for i in range(len(idx)):
        if int(idx[i]) != i or not hashes[i]:
            return False
        if i > 0 and prev[i] != hashes[i - 1]:
            return False
    return True


def _chain_body(app, n_blocks: int) -> str:
    c = app.test_client()
    for i in range(n_blocks):
        c.post("/mine", json={"miner": "esp8266-esp01"})
    return c.get("/snapshot").get_data(as_text=True)


def _app():
    return create_app(port=5999, peers=[], difficulty=2, api_key="k",
                      data_dir=tempfile.mkdtemp())


def test_chain_fields_are_extractable_and_linked():
    body = _chain_body(_app(), 3)  # genesis + 3 blok = 4
    prev = _extract_values(body, "previous_hash")
    hashes = _extract_values(body, "hash")
    idx = _extract_values(body, "index")
    assert len(idx) == 4, f"harus 4 blok, dapat {len(idx)}"
    assert _verify_chain(prev, hashes, idx) is True


def test_snapshot_carries_balance_for_lcd():
    # Sketch mengambil saldo miner dari body /snapshot yang sama (bukan
    # request /status terpisah lagi) — pastikan kuncinya memang ada.
    c = _app().test_client()
    c.post("/mine", json={"miner": "esp8266-esp01"})
    body = c.get("/snapshot").get_data(as_text=True)
    assert _extract_values(body, "esp8266-esp01") == ["50.0"]


def test_verifier_rejects_broken_link():
    # chain valid...
    body = _chain_body(_app(), 3)
    prev = _extract_values(body, "previous_hash")
    hashes = _extract_values(body, "hash")
    idx = _extract_values(body, "index")
    # ...lalu putuskan linkage blok ke-2 (seperti chain rusak/di-tamper).
    prev[2] = "0" * 64
    assert _verify_chain(prev, hashes, idx) is False


if __name__ == "__main__":
    # `python tests/test_chain_contract.py` — self-check tanpa pytest.
    test_chain_fields_are_extractable_and_linked()
    test_verifier_rejects_broken_link()
    print("OK: parser & verifier sketch cocok dengan /snapshot Flask")

