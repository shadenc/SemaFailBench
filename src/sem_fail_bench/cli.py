from __future__ import annotations

import argparse
import json
from collections import Counter

from sem_fail_bench import __version__
from sem_fail_bench.catalog import canary_by_id, load_canaries
from sem_fail_bench.runner import run_suite, write_run
from sem_fail_bench.scorers import score_canary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sfb", description="SemaFailBench CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("summary", help="Print catalog coverage")

    score_p = sub.add_parser("score", help="Score one offline response")
    score_p.add_argument("--canary-id", required=True)
    score_p.add_argument("--response", required=True)

    run_p = sub.add_parser("run", help="Run canaries against a serving endpoint")
    run_p.add_argument("--condition", default="healthy")
    run_p.add_argument("--temperature", type=float, default=0.0)
    run_p.add_argument("--seed", type=int, default=0)
    run_p.add_argument("--limit", type=int)
    run_p.add_argument("--subtype")
    run_p.add_argument("--capability")
    run_p.add_argument("--split", choices=["core", "held_out"])
    run_p.add_argument("--dry-run", action="store_true")
    run_p.add_argument("--warmup", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "summary":
        return cmd_summary()
    if args.cmd == "score":
        return cmd_score(args.canary_id, args.response)
    if args.cmd == "run":
        summary = run_suite(
            condition=args.condition,
            temperature=args.temperature,
            seed=args.seed,
            limit=args.limit,
            subtype=args.subtype,
            capability=args.capability,
            split=args.split,
            dry_run=args.dry_run,
            warmup=args.warmup,
        )
        if not args.dry_run:
            path = write_run(summary)
            print(path)
        print(json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=2))
        return 0
    return 1


def cmd_summary() -> int:
    catalog = load_canaries()
    canaries = catalog["canaries"]
    print(f"suite: {catalog.get('suite_version')}  n={len(canaries)}")
    print("splits:")
    for split, n in Counter(c.get("split", "?") for c in canaries).most_common():
        print(f"  {split:12} {n}")
    print("capabilities:")
    for cap, n in Counter(c["capability"] for c in canaries).most_common():
        print(f"  {cap}  {n}")
    print("subtypes:")
    for subtype, n in Counter(c["subtype"] for c in canaries).most_common():
        print(f"  {subtype:40} {n}")
    return 0


def cmd_score(canary_id: str, response: str) -> int:
    canary = canary_by_id(canary_id)
    result = score_canary(canary, response)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["strict_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
