import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pipe_hold import TraceError
from pipe_hold.io import MAX_BYTES, load

ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    return subprocess.run([sys.executable, "-B", "-m", "pipe_hold", *map(str,args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=10)


class CliTests(unittest.TestCase):
    def reject(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"trace.json"
            path.write_bytes(raw)
            result = cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_exact_example(self):
        result = cli("examples/parent-hold.json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, (ROOT/"examples/parent-hold.txt").read_text())

    def test_json_provenance_and_caps(self):
        result = cli("examples/exec-alias.json", "--format", "json")
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(data["checks"][0]["holders"][0]["source"]["fd"], 4)
        capped = cli("examples/parent-hold.json", "--format", "json", "--holders", "0")
        self.assertEqual(capped.returncode, 1)
        self.assertEqual(json.loads(capped.stdout)["checks"][0]["omitted_holders"], 1)

    def test_valid_closed_trace(self):
        result = cli("examples/closed.json")
        self.assertEqual(result.returncode, 0)
        self.assertIn("after_drain=PASS", result.stdout)

    def test_malformed_json_and_integer_limits(self):
        for raw in [b"{", b"[]", b"\xff", b"1"*5000, b"["*1500+b"]"*1500,
                    b'{"a":1,"a":2}', b'{"x":NaN}', b"{} trailing"]:
            self.reject(raw)

    def test_late_invalid_trace_has_no_partial_report(self):
        data = json.loads((ROOT/"examples/parent-hold.json").read_text())
        data["events"].append({"op":"close", "process":"reader", "fd":63})
        self.reject(json.dumps(data).encode())

    def test_file_limit_and_special_paths(self):
        self.reject(b" "*(MAX_BYTES+1))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root/"file"; target.write_text("{}")
            link=root/"link"; link.symlink_to(target)
            for path in [root, root/"absent", link]:
                with self.assertRaises(TraceError): load(path)

    def test_usage(self):
        for args in [(), ("examples/closed.json", "--holders", "-1"),
                     ("examples/closed.json", "--format", "xml")]:
            result=cli(*args)
            self.assertEqual(result.returncode,2)
            self.assertEqual(result.stdout,"")
        self.assertEqual(cli("--help").returncode,0)
