from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path


MAX_ARCHIVE_SIZE = 10 * 1024**3

OWNER_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]+$"
)

CVBI_PATTERN = re.compile(
    r"^.+\.cvbi$"
)


def error(message: str) -> None:
    print(f"ERROR: {message}")


def success(message: str) -> None:
    print(f"OK: {message}")


def is_safe_path(path: str) -> bool:
    """
    Prevent absolute paths and path traversal.
    """

    if not path:
        return False

    if path.startswith("/"):
        return False

    if path.startswith("\\"):
        return False

    if ":" in path.split("/")[0]:
        return False

    parts = Path(path).parts

    if ".." in parts:
        return False

    return True


def verify_archive(
    archive_path: Path,
) -> int:

    if not archive_path.is_file():
        error(
            f"file not found: {archive_path}"
        )
        return 2

    try:
        size = archive_path.stat().st_size
    except OSError as exc:
        error(
            f"cannot read file size: {exc}"
        )
        return 2

    if size > MAX_ARCHIVE_SIZE:
        error(
            "cvbi.conv exceeds the 10 GiB limit"
        )
        return 1

    if not zipfile.is_zipfile(
        archive_path
    ):
        error(
            "cvbi.conv is not a valid ZIP archive"
        )
        return 1

    try:
        with zipfile.ZipFile(
            archive_path,
            "r",
            allowZip64=True,
        ) as archive:

            members = archive.infolist()

            if not members:
                error(
                    "cvbi.conv is empty"
                )
                return 1

            cvbi_files = 0
            owners: set[str] = set()

            for member in members:

                name = member.filename

                # ----------------------------------------
                # Security checks
                # ----------------------------------------

                if not is_safe_path(name):
                    error(
                        f"unsafe archive path: {name}"
                    )
                    return 1

                # ----------------------------------------
                # Directories
                # ----------------------------------------

                if member.is_dir():

                    if name == "cvbi/":
                        continue

                    # Directory entries are not required.
                    # They are allowed as long as they
                    # remain inside cvbi/.
                    if not name.startswith(
                        "cvbi/"
                    ):
                        error(
                            f"invalid directory: {name}"
                        )
                        return 1

                    continue

                # ----------------------------------------
                # Every file must be inside cvbi/
                # ----------------------------------------

                if not name.startswith(
                    "cvbi/"
                ):
                    error(
                        f"file outside cvbi/: {name}"
                    )
                    return 1

                relative = name[
                    len("cvbi/"):
                ]

                parts = relative.split("/")

                # Required:
                #
                # cvbi/<owner>/<file>.cvbi
                #
                if len(parts) != 2:
                    error(
                        f"invalid CVBI path: {name}"
                    )
                    return 1

                owner = parts[0]
                filename = parts[1]

                if not owner:
                    error(
                        f"missing owner: {name}"
                    )
                    return 1

                if not OWNER_PATTERN.fullmatch(
                    owner
                ):
                    error(
                        f"invalid owner name: {owner}"
                    )
                    return 1

                if not CVBI_PATTERN.fullmatch(
                    filename
                ):
                    error(
                        f"non-CVBI file found: {name}"
                    )
                    return 1

                owners.add(owner)
                cvbi_files += 1

            if cvbi_files == 0:
                error(
                    "cvbi.conv contains no .cvbi files"
                )
                return 1

            # ----------------------------------------
            # Check duplicate archive paths
            # ----------------------------------------

            names = [
                member.filename
                for member in members
                if not member.is_dir()
            ]

            if len(names) != len(set(names)):
                error(
                    "duplicate archive paths detected"
                )
                return 1

            # ----------------------------------------
            # Test every compressed member
            # ----------------------------------------

            bad_member = archive.testzip()

            if bad_member is not None:
                error(
                    f"corrupted archive member: "
                    f"{bad_member}"
                )
                return 1

    except (
        OSError,
        zipfile.BadZipFile,
        RuntimeError,
    ) as exc:

        error(
            f"failed to verify archive: {exc}"
        )
        return 1

    print()
    print(
        "========================================"
    )
    print(
        "CVBI ARCHIVE VERIFICATION"
    )
    print(
        "========================================"
    )

    print(
        f"Owners     : {len(owners)}"
    )

    print(
        f"CVBI files : {cvbi_files}"
    )

    print(
        f"Size       : {size:,} bytes"
    )

    print()

    success(
        "cvbi.conv is valid"
    )

    return 0


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Verify a cvbi.conv archive"
        )
    )

    parser.add_argument(
        "archive",
        type=Path,
        help="Path to cvbi.conv",
    )

    args = parser.parse_args()

    return verify_archive(
        args.archive
    )


if __name__ == "__main__":
    sys.exit(main())