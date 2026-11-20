"""Explain synthetic writer references preventing EOF after pipe drainage."""

import argparse
import json
import sys

from . import TraceError, audit
from .io import load


def render(report):
    lines = [f"events={report['events']} checks={report['checks_total']} failed={report['failed_checks']}"]
    for check in report["checks"]:
        state = "PASS" if check["eof_after_drain"] else "HELD"
        lines.append(f"event={check['event']} {check['process']}:{check['fd']} pipe={check['pipe']} "
                     f"after_drain={state} writers={check['writer_descriptors']} "
                     f"self_held={check['self_held_writers']}")
        for holder in check["holders"]:
            lines.append(f"  holder={holder['process']}:{holder['fd']} created_event={holder['created_event']} "
                         f"via={holder['via']} cloexec={str(holder['cloexec']).lower()}")
        if check["omitted_holders"]:
            lines.append(f"  omitted_holders={check['omitted_holders']}")
    lines.append("gate=" + ("FAIL (EOF expectations held)" if report["gate_failed"]
                             else "PASS (modeled EOF expectations only)"))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", help="local UTF-8 JSON synthetic trace")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--holders", type=int, default=8, help="0..32 writer holders per check")
    args = parser.parse_args(argv)
    try:
        result = audit(load(args.trace), holders=args.holders)
    except TraceError as exc:
        print(f"pipe-hold: {exc}", file=sys.stderr)
        return 2
    text = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
            if args.format == "json" else render(result))
    sys.stdout.write(text)
    return int(result["gate_failed"])


if __name__ == "__main__":
    raise SystemExit(main())
