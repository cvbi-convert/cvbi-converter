from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


CHUNK_SIZE = 8 * 1024 * 1024


def git_blob_sha(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


class HashCache:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(self, blob_sha: str) -> Path:
        return self.directory / f"{blob_sha}.sha256"

    def get(self, blob_sha: str) -> str | None:
        path = self._path(blob_sha)

        if not path.is_file():
            return None

        value = path.read_text(
            encoding="ascii"
        ).strip()

        if len(value) != 64:
            return None

        return value

    def put(
        self,
        blob_sha: str,
        sha256: str,
    ) -> None:
        path = self._path(blob_sha)

        temporary = path.with_suffix(".tmp")

        temporary.write_text(
            sha256 + "\n",
            encoding="ascii",
        )

        temporary.replace(path)