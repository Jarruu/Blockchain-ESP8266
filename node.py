"""Satu proses = satu node blockchain, dibungkus REST API Flask.

Menjalankan:
    python node.py --port 5000 --peers http://127.0.0.1:5001,... --difficulty 4
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import threading

import requests
from flask import Flask, jsonify, request

from blockchain import REWARD, Block, Blockchain

PEER_TIMEOUT = 2.0  # detik; peer mati harus di-skip, bukan bikin crash


class _DropStartupBanner(logging.Filter):
    """Buang banner startup Werkzeug, tapi pertahankan log request.

    Banner ('development server...', 'Running on ...', 'Press CTRL+C') dan
    log akses sama-sama level INFO, jadi filter ini membuang record yang
    memuat teks banner saja; baris 'GET /status 200' tetap tampil.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "development server" not in record.getMessage()


def _quiet_werkzeug() -> None:
    logger = logging.getLogger("werkzeug")
    if not any(isinstance(f, _DropStartupBanner) for f in logger.filters):
        logger.addFilter(_DropStartupBanner())


def create_app(port: int, peers: list[str], difficulty: int, api_key: str,
               data_dir: str) -> Flask:
    app = Flask(__name__)
    node_url = f"http://127.0.0.1:{port}"
    peers_set: set[str] = {p.rstrip("/") for p in peers if p}
    lock = threading.Lock()

    os.makedirs(data_dir, exist_ok=True)
    state_file = os.path.join(data_dir, f"node_{port}.json")

    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as fh:
            bc = Blockchain.from_dict(json.load(fh))
        bc.difficulty = difficulty
    else:
        bc = Blockchain(difficulty=difficulty)

    def _save() -> None:
        with open(state_file, "w", encoding="utf-8") as fh:
            json.dump(bc.to_dict(), fh)

    def _status_payload() -> dict:
        return {
            "node": node_url,
            "height": len(bc.chain),
            "difficulty": bc.difficulty,
            "peers": sorted(peers_set),
            "balances": bc.balances(),
            "last_block": bc.last_block.to_dict(),
        }

    @app.get("/status")
    def status():
        return jsonify(_status_payload())

    @app.get("/chain")
    def chain():
        return jsonify({"chain": [b.to_dict() for b in bc.chain],
                        "length": len(bc.chain)})

    @app.get("/snapshot")
    def snapshot():
        """Gabungan /chain + /status untuk light node (firmware Wokwi).

        Light node hanya butuh header blok (index/previous_hash/hash) untuk
        verifikasi linkage + saldo. Satu request = satu TLS handshake, bukan
        dua — ini yang paling memangkas jeda LCD di simulator.
        """
        with lock:
            payload = {
                "node": node_url,
                "height": len(bc.chain),
                "difficulty": bc.difficulty,
                "balances": bc.balances(),
                "chain": [{"index": b.index,
                           "previous_hash": b.previous_hash,
                           "hash": b.hash} for b in bc.chain],
            }
        return jsonify(payload)

    @app.post("/transactions/new")
    def new_transaction():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "body harus JSON objek"}), 400
        sender = data.get("sender")
        recipient = data.get("recipient")
        amount = data.get("amount")
        if sender is None or recipient is None or amount is None:
            return jsonify({"error": "field sender/recipient/amount wajib"}), 400
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return jsonify({"error": "amount harus angka"}), 400
        if amount <= 0:
            return jsonify({"error": "amount harus > 0"}), 400
        with lock:
            index = bc.add_transaction(sender, recipient, amount)
        return jsonify({"message": "transaksi ditambahkan",
                        "index": index}), 201

    @app.post("/mine")
    def mine():
        data = request.get_json(silent=True) or {}
        miner = data.get("miner", "unknown")
        with lock:
            blk = bc.mine_block(miner)
            _save()
        return jsonify({"block": blk.to_dict(), "height": len(bc.chain)})

    @app.post("/trigger")
    def trigger():
        """Pintu masuk hardware. Wajib header X-API-Key."""
        if request.headers.get("X-API-Key") != api_key:
            return jsonify({"error": "API key tidak valid"}), 401
        data = request.get_json(silent=True) or {}
        device = data.get("device", "unknown")
        miner = data.get("miner", f"device-{device}")
        with lock:
            blk = bc.mine_block(miner)
            _save()
        _broadcast_chain()
        return jsonify({
            "device": device,
            "miner": miner,
            "reward": REWARD,
            "block": blk.to_dict(),
            "height": len(bc.chain),
        })

    @app.post("/nodes/register")
    def register():
        data = request.get_json(silent=True) or {}
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            return jsonify({"error": "nodes harus list"}), 400
        for n in nodes:
            if isinstance(n, str) and n.strip():
                peers_set.add(n.rstrip("/"))
        return jsonify({"message": "peer terdaftar",
                        "peers": sorted(peers_set)}), 200

    @app.get("/nodes/resolve")
    def resolve():
        """Longest-chain consensus: tarik chain peer, adopsi bila valid & lebih panjang."""
        replaced = False
        for peer in sorted(peers_set):
            try:
                resp = requests.get(f"{peer}/chain", timeout=PEER_TIMEOUT)
                data = resp.json()
                candidate = [Block.from_dict(b) for b in data["chain"]]
            except Exception as exc:  # peer mati / JSON rusak -> skip
                app.logger.warning("peer %s tidak bisa dijangkau: %s", peer, exc)
                continue
            with lock:
                if bc.replace_chain(candidate):
                    replaced = True
                    _save()
        return jsonify({"replaced": replaced, "height": len(bc.chain)})

    def _broadcast_chain() -> None:
        """Best-effort: beri tahu peer supaya mereka menarik chain terbaru."""
        for peer in sorted(peers_set):
            try:
                requests.post(f"{peer}/nodes/register",
                              json={"nodes": [node_url]}, timeout=PEER_TIMEOUT)
            except Exception:
                pass

    app.bc = bc  # memudahkan debug/testing
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Node blockchain lokal")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--peers", default="",
                        help="daftar URL peer, dipisah koma")
    parser.add_argument("--difficulty", type=int, default=4)
    parser.add_argument("--api-key", default="dev-secret")
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    peers = [p for p in args.peers.split(",") if p.strip()]
    app = create_app(port=args.port, peers=peers, difficulty=args.difficulty,
                     api_key=args.api_key, data_dir=args.data_dir)
    _quiet_werkzeug()
    print(f"[node] http://127.0.0.1:{args.port}  peers={peers}")
    app.run(host="0.0.0.0", port=args.port, threaded=True)


if __name__ == "__main__":
    main()
