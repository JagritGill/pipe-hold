from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.check_release import check

ROOT=Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_inventory(self):
        self.assertEqual(check(ROOT)["files"],22)

    def mutate(self, action):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"release"
            shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns(".git","__pycache__"))
            action(root)
            with self.assertRaises((ValueError,SyntaxError)): check(root)

    def test_file_scope_and_modes(self):
        self.mutate(lambda r:(r/"extra").write_text("extra"))
        self.mutate(lambda r:(r/"README.md").unlink())
        self.mutate(lambda r:(r/"link").symlink_to(r/"README.md"))
        self.mutate(lambda r:(r/"README.md").chmod(0o755))

    def test_links_syntax_and_scan(self):
        self.mutate(lambda r:(r/"README.md").write_text("[bad](missing.md)"))
        self.mutate(lambda r:(r/"pipe_hold/core.py").write_text("def bad(:"))
        self.mutate(lambda r:(r/"README.md").write_text("AKIA"+"0"*16))
        self.mutate(lambda r:(r/"README.md").write_text("/"+"Users"+"/fixture/data"))
        self.mutate(lambda r:(r/"README.md").write_bytes(bytes([27])+b"[2J"))
