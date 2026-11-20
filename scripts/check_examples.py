"""Exercise documented CLI examples, including intentional finding exits."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args, code):
    result = subprocess.run([sys.executable, "-B", "-m", "pipe_hold", *args],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == code, (args, result.returncode, result.stderr)
    assert not result.stderr
    return result.stdout


def main():
    assert run("examples/parent-hold.json", code=1) == (ROOT/"examples/parent-hold.txt").read_text()
    parent=json.loads(run("examples/parent-hold.json", "--format", "json", code=1))
    assert [c["eof_after_drain"] for c in parent["checks"]] == [False, True]
    assert parent["checks"][0]["holders"][0]["process"] == "shell"
    capped=json.loads(run("examples/parent-hold.json", "--format", "json", "--holders", "0", code=1))
    assert capped["checks"][0]["holders"] == []
    assert capped["checks"][0]["omitted_holders"] == 1
    assert "self_held=1" in run("examples/exec-alias.json", code=1)
    alias=json.loads(run("examples/exec-alias.json", "--format", "json", code=1))
    assert alias["checks"][0]["holders"][0]["source"]["fd"] == 4
    assert "after_drain=PASS" in run("examples/closed.json", code=0)
    closed=json.loads(run("examples/closed.json", "--format", "json", code=0))
    assert not closed["gate_failed"]
    assert "--holders" in run("--help", code=0)
    print("8 CLI examples passed, including expected finding exits")


if __name__ == "__main__": main()
