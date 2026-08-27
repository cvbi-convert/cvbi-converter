from __future__ import annotations

import fnmatch
from pathlib import Path


class IgnoreRules:
    def __init__(self, root: Path, ignore_file: Path):
        self.root = root
        self.ignore_file = ignore_file
        self.patterns = self._load()

    def _load(self) -> list[str]:
        if not self.ignore_file.is_file():
            return []

        patterns: list[str] = []

        for line in self.ignore_file.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            patterns.append(line.replace("\\", "/"))

        return patterns

    def matches(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.root).as_posix()
        except ValueError:
            relative = path.as_posix()

        basename = path.name

        for pattern in self.patterns:
            if fnmatch.fnmatch(relative, pattern):
                return True

            if fnmatch.fnmatch(basename, pattern):
                return True

        return False