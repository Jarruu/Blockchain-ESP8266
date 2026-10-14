"""Benchmark mining & sinkronisasi node. Hasil ditulis ke docs/bukti/benchmark.md.

    python benchmark.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

from blockchain import Blockchain

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "bukti" / "benchmark.md"
DIFFICULTIES = [2, 3, 4, 5]


def bench_mine(difficulty: int, n: int = 5) -> float:
    bc = Blockchain(difficulty=difficulty)
    start = time.perf_counter()
    for i in range(n):
        bc.mine_block(f"miner{i}")
    return (time.perf_counter() - start) / n


def _wait(port: int, timeout: float = 15.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            requests.get(f"http://127.0.0.1:{port}/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def bench_sync(blocks: int = 10) -> float:
    """Waktu node kosong mengejar chain sumber (dalam detik)."""
    src, dst = 5200, 5201
    data_dir = tempfile.mkdtemp(prefix="bc_bench_")  # bersih tiap run
    procs = []
    try:
        procs.append(subprocess.Popen(
            [sys.executable, str(ROOT / "node.py"), "--port", str(src),
             "--difficulty", "2", "--data-dir", data_dir],
            cwd=str(ROOT)))
        procs.append(subprocess.Popen(
            [sys.executable, str(ROOT / "node.py"), "--port", str(dst),
             "--difficulty", "2", "--data-dir", data_dir],
            cwd=str(ROOT)))
        assert _wait(src) and _wait(dst), "node benchmark gagal start"

        requests.post(f"http://127.0.0.1:{dst}/nodes/register",
                      json={"nodes": [f"http://127.0.0.1:{src}"]}, timeout=5)
        for i in range(blocks):
            requests.post(f"http://127.0.0.1:{src}/mine",
                          json={"miner": f"m{i}"}, timeout=15)

        start = time.perf_counter()
        while True:
            requests.get(f"http://127.0.0.1:{dst}/nodes/resolve", timeout=5)
            h = requests.get(f"http://127.0.0.1:{dst}/status",
                             timeout=2).json()["height"]
            if h == blocks + 1:
                return time.perf_counter() - start
            if time.perf_counter() - start > 30:
                return -1.0
    finally:
        for pr in procs:
            pr.terminate()
        for pr in procs:
            try:
                pr.wait(timeout=5)
            except Exception:
                pr.kill()
        shutil.rmtree(data_dir, ignore_errors=True)


def main() -> None:
    print("Benchmark mining (rata-rata 5 blok)...")
    mine_rows = []
    for d in DIFFICULTIES:
        secs = bench_mine(d)
        mine_rows.append((d, secs))
        print(f"  difficulty {d}: {secs:.4f} detik/blok")

    print("Benchmark sinkronisasi (10 blok)...")
    sync_secs = bench_sync(10)
    print(f"  {sync_secs:.3f} detik")

    lines = ["# Hasil Benchmark", "",
             f"Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             "## Waktu mining vs difficulty", "",
             "| difficulty | rata-rata detik/blok |", "|---|---|"]
    lines += [f"| {d} | {s:.4f} |" for d, s in mine_rows]
    lines += ["", "## Waktu sinkronisasi antar-node", "",
              "| blok | detik sinkronisasi |", "|---|---|",
              f"| 10 | {sync_secs:.3f} |", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nHasil ditulis ke {OUT}")


if __name__ == "__main__":
    main()
