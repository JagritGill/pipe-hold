"""Exact release inventory, local links, syntax and heuristic source checks."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import stat

FILES = frozenset("""
.github/workflows/ci.yml .gitignore AGENTS.md LICENSE NOTICE.md README.md
docs/architecture.md docs/related-work.md
examples/parent-hold.json examples/parent-hold.txt examples/exec-alias.json examples/closed.json
pipe_hold/__init__.py pipe_hold/__main__.py pipe_hold/model.py pipe_hold/core.py pipe_hold/io.py
scripts/check_examples.py scripts/check_release.py
tests/test_core.py tests/test_cli_io.py tests/test_release.py
""".split())
PATTERNS = [r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"/(?:Users|home)/[A-Za-z0-9_.-]+/"]


def check(root):
    root=Path(root).resolve()
    actual=set()
    for path in root.rglob("*"):
        relative=path.relative_to(root)
        if relative.parts[0] == ".git": continue
        if path.is_symlink(): raise ValueError("release symlink")
        if path.is_dir(): continue
        if not path.is_file(): raise ValueError("release non-regular file")
        actual.add(relative.as_posix())
    if actual != FILES: raise ValueError("release inventory mismatch")
    hashes={}
    links=syntax=0
    for name in sorted(FILES):
        path=root/name
        if stat.S_IMODE(path.stat().st_mode) != 0o644: raise ValueError("unexpected file mode")
        raw=path.read_bytes(); text=raw.decode("utf-8")
        if any(b < 32 and b not in (9,10) for b in raw): raise ValueError("raw control byte")
        if any(re.search(p,text) for p in PATTERNS): raise ValueError("credential-like or private-path pattern")
        if path.suffix == ".py":
            ast.parse(text, filename=name); syntax += 1
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if target.startswith(("https://","http://","#")): continue
                destination=(path.parent/target.split("#",1)[0]).resolve()
                if not destination.is_relative_to(root) or not destination.is_file():
                    raise ValueError("broken or external local link")
                links += 1
        hashes[name]=hashlib.sha256(raw).hexdigest()
    return dict(files=len(hashes),local_links=links,python_syntax_files=syntax,sha256=hashes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    try: result=check(Path(__file__).resolve().parents[1])
    except (OSError,ValueError,SyntaxError) as exc: parser.exit(1,f"release check failed: {exc}\n")
    if args.json: print(json.dumps(result,indent=2,sort_keys=True))
    else: print(f"release checks passed: {result['files']} files, {result['local_links']} local links, "
                f"{result['python_syntax_files']} Python syntax files; heuristic scan only")


if __name__ == "__main__": main()
