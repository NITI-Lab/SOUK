#!/usr/bin/env python3
"""Generate a persona library YAML for the simulator.

Usage:
    python scripts/generate_personas.py --n 200 --seed 0 --out personas.yaml
    python scripts/generate_personas.py --n 200 --summary   # print stats only
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

import yaml


def _setup_path() -> None:
    src = Path(__file__).resolve().parent.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _setup_path()
    from souk.simulator import sample_personas

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="number of personas")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None, help="output YAML path")
    ap.add_argument("--summary", action="store_true", help="print distribution stats only")
    args = ap.parse_args()

    lib = sample_personas(n=args.n, seed=args.seed)

    if args.summary or args.out is None:
        by_occ = collections.Counter(p.occupation for p in lib)
        by_pur = collections.Counter(p.purpose for p in lib)
        by_pri = collections.Counter(p.priorities for p in lib)
        by_comm = collections.Counter(p.comm_style for p in lib)
        inj_count = collections.Counter(len(p.injections) for p in lib)
        inj_ids = collections.Counter(i for p in lib for i in p.injections)
        print(f"Generated {len(lib)} personas (seed={args.seed})")
        print("--- occupation ---")
        [print(f"  {k}: {v}") for k, v in by_occ.most_common()]
        print("--- purpose ---")
        [print(f"  {k}: {v}") for k, v in by_pur.most_common()]
        print("--- priorities ---")
        [print(f"  {k}: {v}") for k, v in by_pri.most_common()]
        print("--- comm_style ---")
        [print(f"  {k}: {v}") for k, v in by_comm.most_common()]
        print("--- injection count per persona ---")
        for k in sorted(inj_count):
            print(f"  {k} injections: {inj_count[k]}")
        print("--- injector frequencies ---")
        for k, v in inj_ids.most_common():
            print(f"  {k}: {v}")

    if args.out is not None:
        payload = {
            "version": 1,
            "count": len(lib),
            "seed": args.seed,
            "personas": [p.to_dict() for p in lib],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
        print(f"\nWrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
