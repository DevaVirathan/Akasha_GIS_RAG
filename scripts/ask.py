"""Ask a question against the ingested corpus: retrieve -> answer.

Usage (once modules are implemented):
    python scripts/ask.py "What is the difference between active and passive remote sensing?"

Scaffold: wiring is present but query stages raise NotImplementedError.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akasha.query.answer import answer  # noqa: E402
from akasha.query.retrieve import retrieve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the GIS/RS RAG.")
    parser.add_argument("question", help="Your question.")
    args = parser.parse_args()

    retrieved = retrieve(args.question)
    print(answer(args.question, retrieved))


if __name__ == "__main__":
    main()
