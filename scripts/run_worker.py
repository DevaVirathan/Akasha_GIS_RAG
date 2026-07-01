"""Ingestion worker: consume jobs from Redis and run the pipeline.

Usage:
    python scripts/run_worker.py          # long-running: process jobs forever
    python scripts/run_worker.py --once   # process one job then exit (handy for demos)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akasha.ingest.pipeline import ingest_version  # noqa: E402
from akasha.queue import dequeue  # noqa: E402


def _process(job: dict) -> None:
    version_id = job["version_id"]
    print(f"worker: ingesting {version_id} …", flush=True)
    try:
        n = ingest_version(version_id, max_pages=job.get("max_pages"))
        print(f"worker: published {version_id} ({n} chunks)", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"worker: FAILED {version_id}: {exc}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Akasha ingestion worker.")
    parser.add_argument("--once", action="store_true", help="Process one job then exit.")
    args = parser.parse_args()

    if args.once:
        job = dequeue(timeout=15)
        if job:
            _process(job)
        else:
            print("worker: no job within timeout")
        return

    print("worker: waiting for jobs (Ctrl+C to stop)…", flush=True)
    while True:
        job = dequeue(timeout=5)
        if job:
            _process(job)


if __name__ == "__main__":
    main()
