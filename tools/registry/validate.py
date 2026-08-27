from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from validate_cvbi import validate as validate_cvbi


# ============================================================
# Configuration
# ============================================================

REGISTRY_NAME = "cvbi-registry"

VERSION_FILE = "VERSION"
LATEST_FILE = "LATEST"
MANIFEST_FILE = "MANIFEST"

MAX_VERSION_LENGTH = 128
MAX_PACKAGE_NAME_LENGTH = 128
MAX_OWNER_NAME_LENGTH = 128

# Maximum size of one .cvbi file.
MAX_CVBI_SIZE = 10 * 1024 * 1024 * 1024

# Package names ending in "-<number>" are forbidden.
#
# Examples:
#   ubuntu-1
#   debian-2
#   arch-123
#
FORBIDDEN_NUMBER_SUFFIX = re.compile(
    r"^.+-\d+$"
)

# Strict SemVer:
#
# 1.0.0
# 10.20.30
#
VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)"
    r"\."
    r"(0|[1-9]\d*)"
    r"\."
    r"(0|[1-9]\d*)"
    r"$"
)


# ============================================================
# Result types
# ============================================================

@dataclass
class RegistryResult:
    owner: str
    package: str
    path: Path
    valid: bool
    reason: str | None = None
    version: str | None = None


# ============================================================
# Basic helpers
# ============================================================

def error(message: str) -> None:
    print(f"ERROR: {message}")


def warning(message: str) -> None:
    print(f"WARNING: {message}")


def is_safe_name(name: str) -> bool:
    """
    Registry names must be simple directory names.

    Forbidden:
      /
      \
      ..
      whitespace
      hidden names
    """

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


def is_valid_owner_name(name: str) -> bool:
    if len(name) > MAX_OWNER_NAME_LENGTH:
        return False

    return is_safe_name(name)


def is_valid_package_name(name: str) -> bool:
    if len(name) > MAX_PACKAGE_NAME_LENGTH:
        return False

    if not is_safe_name(name):
        return False

    if FORBIDDEN_NUMBER_SUFFIX.fullmatch(name):
        return False

    return True


# ============================================================
# VERSION
# ============================================================

def read_version(package: Path) -> str | None:
    path = package / VERSION_FILE

    if not path.is_file():
        error(
            f"{package}: VERSION is missing"
        )
        return None

    try:
        value = path.read_text(
            encoding="utf-8"
        ).strip()

    except OSError as exc:
        error(
            f"cannot read {path}: {exc}"
        )
        return None

    if not value:
        error(
            f"{package}: VERSION is empty"
        )
        return None

    if len(value) > MAX_VERSION_LENGTH:
        error(
            f"{package}: VERSION is too long"
        )
        return None

    if not VERSION_PATTERN.fullmatch(value):
        error(
            f"{package}: invalid VERSION "
            f"'{value}'"
        )
        return None

    return value


# ============================================================
# LATEST
# ============================================================

def validate_latest(
    package: Path,
    version: str,
) -> bool:

    path = package / LATEST_FILE

    if not path.is_file():
        error(
            f"{package}: LATEST is missing"
        )
        return False

    try:
        latest = path.read_text(
            encoding="utf-8"
        ).strip()

    except OSError as exc:
        error(
            f"{package}: cannot read LATEST: {exc}"
        )
        return False

    if not latest:
        error(
            f"{package}: LATEST is empty"
        )
        return False

    if len(latest) > MAX_VERSION_LENGTH:
        error(
            f"{package}: LATEST is too long"
        )
        return False

    if not VERSION_PATTERN.fullmatch(latest):
        error(
            f"{package}: invalid LATEST "
            f"'{latest}'"
        )
        return False

    if latest != version:
        error(
            f"{package}: LATEST '{latest}' "
            f"does not match VERSION '{version}'"
        )
        return False

    return True


# ============================================================
# MANIFEST
# ============================================================

def validate_manifest(package: Path) -> bool:

    path = package / MANIFEST_FILE

    if not path.is_file():
        error(
            f"{package}: MANIFEST is missing"
        )
        return False

    try:
        size = path.stat().st_size

    except OSError as exc:
        error(
            f"{package}: cannot stat MANIFEST: {exc}"
        )
        return False

    # MANIFEST MUST be completely empty.
    if size != 0:
        error(
            f"{package}: MANIFEST must be empty"
        )
        return False

    return True


# ============================================================
# CVBI discovery
# ============================================================

def find_cvbi_files(
    package: Path,
) -> list[Path]:

    result: list[Path] = []

    try:
        entries = package.iterdir()

    except OSError as exc:
        error(
            f"{package}: cannot read directory: {exc}"
        )
        return result

    for entry in entries:

        if not entry.is_file():
            continue

        if entry.suffix.lower() != ".cvbi":
            continue

        result.append(entry)

    return sorted(
        result,
        key=lambda path: path.name.lower(),
    )


# ============================================================
# Package content validation
# ============================================================

def validate_package_contents(
    package: Path,
) -> bool:

    allowed_files = {
        MANIFEST_FILE,
        VERSION_FILE,
        LATEST_FILE,
    }

    try:
        entries = list(package.iterdir())

    except OSError as exc:
        error(
            f"{package}: cannot read directory: {exc}"
        )
        return False

    for entry in entries:

        # Nested directories inside a package are not
        # allowed. The structure is:
        #
        # owner/package/*.cvbi
        #
        if entry.is_dir():
            error(
                f"{package}: nested directory is not "
                f"allowed: {entry.name}"
            )
            return False

        if entry.name in allowed_files:
            continue

        if entry.suffix.lower() == ".cvbi":
            continue

        error(
            f"{package}: unsupported file "
            f"'{entry.name}'"
        )
        return False

    return True


# ============================================================
# CVBI size validation
# ============================================================

def validate_cvbi_size(
    cvbi: Path,
) -> bool:

    try:
        size = cvbi.stat().st_size

    except OSError as exc:
        error(
            f"{cvbi}: cannot determine size: {exc}"
        )
        return False

    if size == 0:
        error(
            f"{cvbi}: CVBI file is empty"
        )
        return False

    if size > MAX_CVBI_SIZE:
        error(
            f"{cvbi}: exceeds the 10 GiB limit"
        )
        return False

    return True


# ============================================================
# Package validation
# ============================================================

def validate_package(
    owner: str,
    package: Path,
) -> RegistryResult:

    package_name = package.name

    print()
    print(
        f"==> Checking "
        f"{owner}/{package_name}"
    )

    # --------------------------------------------------------
    # Package name
    # --------------------------------------------------------

    if not is_valid_package_name(
        package_name
    ):
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="invalid package name",
        )

    # --------------------------------------------------------
    # Required files
    # --------------------------------------------------------

    version = read_version(package)

    if version is None:
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="invalid VERSION",
        )

    if not validate_latest(
        package,
        version,
    ):
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="invalid LATEST",
            version=version,
        )

    if not validate_manifest(package):
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="invalid MANIFEST",
            version=version,
        )

    # --------------------------------------------------------
    # Package contents
    # --------------------------------------------------------

    if not validate_package_contents(
        package
    ):
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="invalid package contents",
            version=version,
        )

    # --------------------------------------------------------
    # CVBI discovery
    # --------------------------------------------------------

    cvbi_files = find_cvbi_files(package)

    if not cvbi_files:
        return RegistryResult(
            owner=owner,
            package=package_name,
            path=package,
            valid=False,
            reason="no .cvbi file found",
            version=version,
        )

    # --------------------------------------------------------
    # Package information
    # --------------------------------------------------------

    print(
        f"    VERSION: {version}"
    )

    print(
        f"    CVBI files: {len(cvbi_files)}"
    )

    # --------------------------------------------------------
    # Validate each CVBI
    # --------------------------------------------------------

    for cvbi in cvbi_files:

        print(
            f"    Validating CVBI: "
            f"{cvbi.name}"
        )

        # 10 GiB size limit.
        if not validate_cvbi_size(cvbi):
            return RegistryResult(
                owner=owner,
                package=package_name,
                path=package,
                valid=False,
                reason=(
                    f"invalid CVBI: "
                    f"{cvbi.name}"
                ),
                version=version,
            )

        # Actual Vectras CVBI format validation.
        result = validate_cvbi(cvbi)

        if result != 0:
            return RegistryResult(
                owner=owner,
                package=package_name,
                path=package,
                valid=False,
                reason=(
                    f"invalid CVBI: "
                    f"{cvbi.name}"
                ),
                version=version,
            )

    print(
        f"    VALID: "
        f"{owner}/{package_name}"
    )

    return RegistryResult(
        owner=owner,
        package=package_name,
        path=package,
        valid=True,
        version=version,
    )


# ============================================================
# Owner validation
# ============================================================

def discover_packages(
    owner_path: Path,
) -> list[Path]:

    packages: list[Path] = []

    try:
        entries = owner_path.iterdir()

    except OSError as exc:
        error(
            f"{owner_path}: cannot read owner: {exc}"
        )
        return packages

    for entry in entries:

        if not entry.is_dir():
            continue

        if not is_valid_package_name(
            entry.name
        ):
            print(
                f"SKIP: invalid package directory "
                f"'{entry.name}'"
            )
            continue

        packages.append(entry)

    return sorted(
        packages,
        key=lambda path: path.name.lower(),
    )


def validate_owner(
    owner_path: Path,
) -> list[RegistryResult]:

    owner = owner_path.name

    print()
    print(
        f"######## OWNER: {owner} ########"
    )

    if not is_valid_owner_name(owner):
        print(
            f"SKIP OWNER: invalid owner name "
            f"'{owner}'"
        )
        return []

    packages = discover_packages(
        owner_path
    )

    if not packages:
        print(
            f"SKIP OWNER: no valid packages "
            f"found in {owner}"
        )
        return []

    results: list[RegistryResult] = []

    for package in packages:

        result = validate_package(
            owner,
            package,
        )

        results.append(result)

        if not result.valid:
            print(
                f"SKIP: {owner}/{package.name}"
                f" — {result.reason}"
            )

    return results


# ============================================================
# Registry validation
# ============================================================

def discover_owners(
    registry: Path,
) -> list[Path]:

    owners: list[Path] = []

    try:
        entries = registry.iterdir()

    except OSError as exc:
        error(
            f"cannot read registry: {exc}"
        )
        return owners

    for entry in entries:

        if not entry.is_dir():
            continue

        if not is_valid_owner_name(
            entry.name
        ):
            print(
                f"SKIP: invalid owner directory "
                f"'{entry.name}'"
            )
            continue

        owners.append(entry)

    return sorted(
        owners,
        key=lambda path: path.name.lower(),
    )


# ============================================================
# Duplicate version handling
# ============================================================

def check_duplicate_versions(
    results: list[RegistryResult],
) -> None:

    versions: dict[str, RegistryResult] = {}

    for result in results:

        if not result.valid:
            continue

        if result.version is None:
            continue

        version = result.version

        if version not in versions:
            versions[version] = result
            continue

        # Duplicate version.
        #
        # The first valid registry keeps the version.
        # The later registry is skipped.
        error(
            f"version {version} already exists, "
            f"skipping to other registry"
        )

        result.valid = False
        result.reason = (
            f"version {version} already exists"
        )


# ============================================================
# Registry validation
# ============================================================

def validate_registry(
    registry: Path,
) -> int:

    if not registry.is_dir():
        error(
            f"registry directory does not exist: "
            f"{registry}"
        )
        return 2

    owners = discover_owners(
        registry
    )

    if not owners:
        print(
            "No valid owners found."
        )
        return 0

    all_results: list[RegistryResult] = []

    for owner in owners:

        results = validate_owner(
            owner
        )

        all_results.extend(results)

    # --------------------------------------------------------
    # Duplicate versions
    # --------------------------------------------------------

    check_duplicate_versions(
        all_results
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    valid = [
        result
        for result in all_results
        if result.valid
    ]

    skipped = [
        result
        for result in all_results
        if not result.valid
    ]

    print()
    print(
        "========================================"
    )
    print(
        "CVBI REGISTRY VALIDATION SUMMARY"
    )
    print(
        "========================================"
    )

    print(
        f"Owners scanned: "
        f"{len(owners)}"
    )

    print(
        f"Packages scanned: "
        f"{len(all_results)}"
    )

    print(
        f"Valid packages: "
        f"{len(valid)}"
    )

    print(
        f"Skipped packages: "
        f"{len(skipped)}"
    )

    if skipped:
        print()
        print("Skipped:")

        for result in skipped:

            print(
                f"  - "
                f"{result.owner}/"
                f"{result.package}: "
                f"{result.reason}"
            )

    print()

    if not valid:
        warning(
            "no valid CVBI packages found"
        )

    print(
        "Validation complete."
    )

    # IMPORTANT:
    #
    # Invalid entries do NOT fail the entire workflow.
    #
    # The caller can continue processing other owners
    # and packages.
    #
    return 0


# ============================================================
# CLI
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Validate the CVBI registry"
        )
    )

    parser.add_argument(
        "registry",
        nargs="?",
        default=REGISTRY_NAME,
        type=Path,
        help=(
            "path to cvbi-registry "
            "(default: cvbi-registry)"
        ),
    )

    args = parser.parse_args()

    return validate_registry(
        args.registry
    )


if __name__ == "__main__":
    sys.exit(main())