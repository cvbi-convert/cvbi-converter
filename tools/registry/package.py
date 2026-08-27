from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path


REGISTRY_NAME = "cvbi-registry"
OUTPUT_NAME = "cvbi.conv"

MAX_ARCHIVE_SIZE = 10 * 1024**3

VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)"
    r"\."
    r"(0|[1-9]\d*)"
    r"\."
    r"(0|[1-9]\d*)$"
)

FORBIDDEN_NUMBER_SUFFIX = re.compile(
    r"^.+-\d+$"
)


def log(message: str) -> None:
    print(message)


def error(message: str) -> None:
    print(f"ERROR: {message}")


def is_safe_name(name: str) -> bool:
    if not name:
        return False

    if name in {".", ".."}:
        return False

    if name.startswith("."):
        return False

    if "/" in name or "\\" in name:
        return False

    if any(char.isspace() for char in name):
        return False

    return True


def is_valid_package_name(name: str) -> bool:
    if not is_safe_name(name):
        return False

    if FORBIDDEN_NUMBER_SUFFIX.fullmatch(name):
        return False

    return True


def read_version(package: Path) -> str | None:
    path = package / "VERSION"

    if not path.is_file():
        return None

    try:
        value = path.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return None

    if not VERSION_PATTERN.fullmatch(value):
        return None

    return value


def read_latest(package: Path) -> str | None:
    path = package / "LATEST"

    if not path.is_file():
        return None

    try:
        value = path.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return None

    if not VERSION_PATTERN.fullmatch(value):
        return None

    return value


def package_is_valid(package: Path) -> bool:

    if not is_valid_package_name(
        package.name
    ):
        return False

    if not (package / "MANIFEST").is_file():
        return False

    if not (package / "VERSION").is_file():
        return False

    if not (package / "LATEST").is_file():
        return False

    version = read_version(package)
    latest = read_latest(package)

    if version is None:
        return False

    if latest is None:
        return False

    if version != latest:
        return False

    cvbi_files = list(
        package.glob("*.cvbi")
    )

    if not cvbi_files:
        return False

    return True


def find_owners(
    registry: Path,
) -> list[Path]:

    owners = []

    for entry in registry.iterdir():

        if not entry.is_dir():
            continue

        if not is_safe_name(
            entry.name
        ):
            continue

        owners.append(entry)

    return sorted(
        owners,
        key=lambda p: p.name.lower()
    )


def find_packages(
    owner: Path,
) -> list[Path]:

    packages = []

    for entry in owner.iterdir():

        if not entry.is_dir():
            continue

        if not is_valid_package_name(
            entry.name
        ):
            continue

        packages.append(entry)

    return sorted(
        packages,
        key=lambda p: p.name.lower()
    )


def add_cvbi(
    archive: zipfile.ZipFile,
    owner: str,
    cvbi: Path,
) -> None:

    # IMPORTANT:
    #
    # Package directory is NOT included.
    #
    # Result:
    #
    # cvbi/<owner>/<file>.cvbi
    #
    archive_name = (
        f"cvbi/"
        f"{owner}/"
        f"{cvbi.name}"
    )

    log(
        f"  ADD: {archive_name}"
    )

    archive.write(
        cvbi,
        arcname=archive_name,
    )


def build_registry(
    registry: Path,
    output: Path,
) -> int:

    if not registry.is_dir():
        error(
            f"registry not found: {registry}"
        )
        return 2

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Never append to an existing archive.
    # --------------------------------------------------------

    output.unlink(
        missing_ok=True
    )

    owners = find_owners(
        registry
    )

    if not owners:
        log(
            "No owners found."
        )
        return 0

    added_files: set[str] = set()

    valid_packages = 0
    skipped_packages = 0
    added_cvbi = 0

    try:

        with zipfile.ZipFile(
            output,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:

            for owner_path in owners:

                owner = owner_path.name

                log("")
                log(
                    f"OWNER: {owner}"
                )

                packages = find_packages(
                    owner_path
                )

                if not packages:
                    log(
                        f"SKIP OWNER: {owner} "
                        "has no valid packages"
                    )
                    continue

                owner_had_valid_package = False

                for package in packages:

                    package_name = (
                        package.name
                    )

                    log(
                        f"CHECK: "
                        f"{owner}/{package_name}"
                    )

                    if not package_is_valid(
                        package
                    ):
                        log(
                            f"SKIP: "
                            f"{owner}/"
                            f"{package_name}"
                        )

                        skipped_packages += 1
                        continue

                    owner_had_valid_package = True
                    valid_packages += 1

                    cvbi_files = sorted(
                        package.glob(
                            "*.cvbi"
                        ),
                        key=lambda p:
                            p.name.lower(),
                    )

                    for cvbi in cvbi_files:

                        archive_name = (
                            f"cvbi/"
                            f"{owner}/"
                            f"{cvbi.name}"
                        )

                        # ------------------------------------
                        # Same filename inside the same owner
                        # cannot exist in the final archive.
                        # ------------------------------------

                        if archive_name in added_files:
                            error(
                                f"{archive_name} "
                                "already exists, "
                                "skipping file"
                            )
                            continue

                        add_cvbi(
                            archive,
                            owner,
                            cvbi,
                        )

                        added_files.add(
                            archive_name
                        )

                        added_cvbi += 1

                if not owner_had_valid_package:
                    log(
                        f"SKIP OWNER: {owner}"
                    )

    except (
        OSError,
        zipfile.BadZipFile,
    ) as exc:

        output.unlink(
            missing_ok=True
        )

        error(
            f"failed to create {output}: {exc}"
        )

        return 1

    # --------------------------------------------------------
    # Check resulting archive size.
    # --------------------------------------------------------

    try:
        size = output.stat().st_size
    except OSError as exc:

        error(
            f"cannot determine output size: {exc}"
        )

        output.unlink(
            missing_ok=True
        )

        return 1

    if size > MAX_ARCHIVE_SIZE:

        error(
            f"{OUTPUT_NAME} exceeds "
            "10 GiB"
        )

        output.unlink(
            missing_ok=True
        )

        return 1

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("")
    print(
        "========================================"
    )
    print(
        "CVBI CONTAINER BUILD SUMMARY"
    )
    print(
        "========================================"
    )

    print(
        f"Valid packages : {valid_packages}"
    )

    print(
        f"Skipped packages: {skipped_packages}"
    )

    print(
        f"CVBI files      : {added_cvbi}"
    )

    print(
        f"Output          : {output}"
    )

    print(
        f"Size            : {size:,} bytes"
    )

    print("")
    print(
        f"CREATED: {output}"
    )

    return 0


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Build the unified cvbi.conv "
            "container"
        )
    )

    parser.add_argument(
        "registry",
        nargs="?",
        type=Path,
        default=Path(REGISTRY_NAME),
    )

    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path(
            "build/releases"
        ) / OUTPUT_NAME,
    )

    args = parser.parse_args()

    return build_registry(
        args.registry,
        args.output,
    )


if __name__ == "__main__":
    sys.exit(main())