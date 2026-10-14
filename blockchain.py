"""Logika inti blockchain: Block, Proof-of-Work, reward, dan konsensus.

Modul ini murni (tanpa I/O jaringan) supaya mudah diuji. Server Flask di
node.py membungkusnya.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

REWARD = 50.0          # coin yang diberikan ke penambang tiap blok
GENESIS_PREV = "0"     # previous_hash blok genesis
COINBASE_SENDER = "0"  # pengirim semu untuk transaksi reward


def _tx_json(transactions: list[dict[str, Any]]) -> str:
    """Serialisasi transaksi yang deterministik (kunci terurut, tanpa spasi)."""
    return json.dumps(transactions, sort_keys=True, separators=(",", ":"))


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: list[dict[str, Any]]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        payload = (
            f"{self.index}|{self.timestamp}|{_tx_json(self.transactions)}"
            f"|{self.previous_hash}|{self.nonce}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def mine(self, difficulty: int) -> None:
        """Naikkan nonce sampai hash berawalan `difficulty` karakter '0'.

        Bagian statis header dihitung sekali agar tidak memanggil json.dumps
        tiap iterasi (penting supaya difficulty tinggi tetap cepat).
        """
        prefix = (f"{self.index}|{self.timestamp}|{_tx_json(self.transactions)}"
                  f"|{self.previous_hash}|")
        target = "0" * difficulty
        nonce = 0
        while True:
            digest = hashlib.sha256(f"{prefix}{nonce}".encode()).hexdigest()
            if digest.startswith(target):
                self.nonce = nonce
                self.hash = digest
                return
            nonce += 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Block":
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            transactions=d["transactions"],
            previous_hash=d["previous_hash"],
            nonce=d["nonce"],
            hash=d["hash"],
        )


class Blockchain:
    def __init__(self, difficulty: int = 4) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = [self._genesis()]
        self.pending: list[dict[str, Any]] = []

    def _genesis(self) -> Block:
        """Blok genesis ikut ditambang agar is_chain_valid konsisten."""
        blk = Block(index=0, timestamp=time.time(), transactions=[],
                    previous_hash=GENESIS_PREV)
        blk.mine(self.difficulty)
        return blk

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """Tambah transaksi ke antrian. Mengembalikan index blok berikutnya."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("amount harus angka > 0")
        self.pending.append(
            {"sender": sender, "recipient": recipient, "amount": float(amount),
             "type": "transfer"}
        )
        return len(self.chain)

    def mine_block(self, miner_address: str) -> Block:
        """Tambang satu blok: transaksi pending + reward coinbase untuk penambang."""
        reward_tx = {"sender": COINBASE_SENDER, "recipient": miner_address,
                     "amount": REWARD, "type": "reward"}
        txs = [reward_tx, *self.pending]
        blk = Block(index=len(self.chain), timestamp=time.time(),
                    transactions=txs, previous_hash=self.last_block.hash)
        blk.mine(self.difficulty)
        self.chain.append(blk)
        self.pending = []
        return blk

    def balances(self) -> dict[str, float]:
        bal: dict[str, float] = {}
        for blk in self.chain:
            for tx in blk.transactions:
                sender = tx["sender"]
                recipient = tx["recipient"]
                amount = float(tx["amount"])
                if sender != COINBASE_SENDER:
                    bal[sender] = bal.get(sender, 0.0) - amount
                bal[recipient] = bal.get(recipient, 0.0) + amount
        return bal

    def is_chain_valid(self, chain: list[Block] | None = None) -> bool:
        chain = chain if chain is not None else self.chain
        if not chain:
            return False
        if chain[0].previous_hash != GENESIS_PREV:
            return False
        target = "0" * self.difficulty
        for i, blk in enumerate(chain):
            if blk.hash != blk.compute_hash():
                return False
            if not blk.hash.startswith(target):
                return False
            if i > 0 and blk.previous_hash != chain[i - 1].hash:
                return False
        return True

    def replace_chain(self, new_chain: list[Block]) -> bool:
        """Adopsi new_chain hanya jika lebih panjang DAN valid (longest-chain)."""
        if len(new_chain) <= len(self.chain):
            return False
        if not self.is_chain_valid(new_chain):
            return False
        self.chain = new_chain
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain],
            "pending": self.pending,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Blockchain":
        bc = cls(difficulty=d.get("difficulty", 4))
        bc.chain = [Block.from_dict(b) for b in d["chain"]]
        bc.pending = d.get("pending", [])
        return bc


if __name__ == "__main__":
    # Self-check cepat: jalankan `python blockchain.py`.
    bc = Blockchain(difficulty=3)
    bc.add_transaction("kelompok6", "esp01", 10)
    bc.mine_block("kelompok6")
    bc.mine_block("esp01")
    assert bc.is_chain_valid(), "chain harus valid"
    assert bc.balances()["kelompok6"] == REWARD - 10
    assert bc.balances()["esp01"] == REWARD + 10
    print("OK: 2 blok ditambang, chain valid, saldo benar")
