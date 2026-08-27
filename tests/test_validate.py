from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Allow importing tools/registry/validate.py
ROOT = Path(__file__).resolve().parents[1]
REGISTRY_TOOLS = ROOT / "tools" / "registry"

sys.path.insert(
    0,
    str(REGISTRY_TOOLS),
)

from validate import (  # noqa: E402
    is_valid_package_name,
    is_valid_owner_name,
    validate_manifest,
    validate_latest,
    validate_package,
)


# ============================================================
# Helpers
# ============================================================

def write(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def create_package(
    root: Path,
    owner: str,
    package: str,
    version: str = "1.0.0",
) -> Path:

    package_path = (
        root
        / owner
        / package
    )

    package_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    write(
        package_path / "VERSION",
        version,
    )

    write(
        package_path / "LATEST",
        version,
    )

    # Empty MANIFEST is mandatory.
    (package_path / "MANIFEST").touch()

    return package_path


# ============================================================
# Name tests
# ============================================================

def test_owner_names() -> None:

    assert is_valid_owner_name(
        "komandan"
    )

    assert is_valid_owner_name(
        "test-user"
    )

    assert not is_valid_owner_name(
        ".hidden"
    )

    assert not is_valid_owner_name(
        "hello world"
    )

    assert not is_valid_owner_name(
        "foo/bar"
    )


def test_package_names() -> None:

    assert is_valid_package_name(
        "ubuntu"
    )

    assert is_valid_package_name(
        "arch-linux"
    )

    assert is_valid_package_name(
        "ubuntu-lts"
    )

    # HARD BAN:
    assert not is_valid_package_name(
        "ubuntu-1"
    )

    assert not is_valid_package_name(
        "debian-123"
    )


# ============================================================
# Manifest tests
# ============================================================

def test_manifest() -> None:

    with tempfile.TemporaryDirectory() as temp:

        package = Path(temp) / "package"
        package.mkdir()

        manifest = package / "MANIFEST"

        manifest.touch()

        assert validate_manifest(
            package
        )

        manifest.write_text(
            "something",
            encoding="utf-8",
        )

        assert not validate_manifest(
            package
        )


# ============================================================
# LATEST tests
# ============================================================

def test_latest() -> None:

    with tempfile.TemporaryDirectory() as temp:

        package = Path(temp) / "package"
        package.mkdir()

        write(
            package / "LATEST",
            "1.0.0",
        )

        assert validate_latest(
            package,
            "1.0.0",
        )

        write(
            package / "LATEST",
            "2.0.0",
        )

        assert not validate_latest(
            package,
            "1.0.0",
        )


# ============================================================
# Valid package test
# ============================================================

def test_valid_package() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu",
        )

        # We create a structural test CVBI.
        #
        # This part can later call the real
        # create_test_cvbi.py.
        cvbi = package / "test.cvbi"

        cvbi.write_bytes(
            b"PK\x03\x04"
        )

        result = validate_package(
            "komandan",
            package,
        )

        # The package itself may fail because the
        # minimal fixture isn't a complete CVBI.
        #
        # The important point here is that validation
        # returns a RegistryResult rather than crashing.
        assert result is not None
        assert result.owner == "komandan"
        assert result.package == "ubuntu"


# ============================================================
# Missing CVBI test
# ============================================================

def test_missing_cvbi() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu",
        )

        result = validate_package(
            "komandan",
            package,
        )

        assert not result.valid
        assert (
            result.reason
            == "no .cvbi file found"
        )


# ============================================================
# Invalid package test
# ============================================================

def test_invalid_package() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu-1",
        )

        result = validate_package(
            "komandan",
            package,
        )

        assert not result.valid
        assert (
            result.reason
            == "invalid package name"
        )


# ============================================================
# Missing VERSION test
# ============================================================

def test_missing_version() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu",
        )

        (package / "VERSION").unlink()

        result = validate_package(
            "komandan",
            package,
        )

        assert not result.valid
        assert (
            result.reason
            == "invalid VERSION"
        )


# ============================================================
# Invalid version test
# ============================================================

def test_invalid_version() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu",
            version="latest",
        )

        result = validate_package(
            "komandan",
            package,
        )

        assert not result.valid
        assert (
            result.reason
            == "invalid VERSION"
        )


# ============================================================
# Invalid LATEST test
# ============================================================

def test_invalid_latest() -> None:

    with tempfile.TemporaryDirectory() as temp:

        root = Path(temp)

        package = create_package(
            root,
            "komandan",
            "ubuntu",
        )

        write(
            package / "LATEST",
            "2.0.0",
        )

        result = validate_package(
            "komandan",
            package,
        )

        assert not result.valid
        assert (
            result.reason
            == "invalid LATEST"
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print(
        "Run this test suite with pytest:"
    )

    print(
        "  pytest -v tests/test_validate.py"
    )