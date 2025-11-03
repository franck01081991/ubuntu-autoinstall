#!/usr/bin/env python3
"""Fail if YAML files contain password-like keys with cleartext values."""
from __future__ import annotations

import re
import sys
from pathlib import Path

pattern = re.compile(r"^(?P<indent>\s*)(?P<key>password|ansible_become_pass)\s*:\s*(?P<value>.+)?$", re.IGNORECASE)
EMPTY_MARKERS = {"", "''", '""'}
MULTILINE_MARKERS = {"|", "|-", ">", ">-"}


def main() -> int:
    status = 0
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if path.suffix.lower() not in {".yml", ".yaml"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:  # pragma: no cover
            print(f"pre-commit: unable to read {path}: {exc}", file=sys.stderr)
            status = 1
            continue
        for idx, line in enumerate(lines, start=1):
            if line.lstrip().startswith("#"):
                continue
            match = pattern.search(line)
            if not match:
                continue
            value = (match.group("value") or "").strip()
            if value in EMPTY_MARKERS or value in MULTILINE_MARKERS:
                continue
            print(
                f"{path}:{idx}: plaintext password-like key '{match.group('key')}' detected; encrypt it with sops",
                file=sys.stderr,
            )
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
