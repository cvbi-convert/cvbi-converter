from __future__ import annotations

import argparse
import json
import posixpath
import struct
import sys
import zipfile
from pathlib import Path


MAX_CVBI_SIZE = 10 * 1024**3
MAX_ENTRY_COUNT = 100_000
MAX_METADATA_SIZE = 16 * 1024**2

QCOW_MAGIC = b"QFI\xfb"

REQUIRED_METADATA_FIELDS = {
    "author",
    "icon",
    "qemu",
    "arch",
    "title",
    "drive",
    "versioncode",
    "cdrom",
    "desc",
}


def safe_name(name: str) -> bool:
    """
    Reject absolute paths and path traversal.
    """

    if not name:
        return False

    if name.startswith("/"):
        return False

    normalized = posixpath.normpath(name)

    if normalized == "..":
        return False

    if normalized.startswith("../"):
        return False

    if "/../" in normalized:
        return False

    return True


def is_encrypted(info: zipfile.ZipInfo) -> bool:
    """
    ZIP general-purpose flag bit 0 means encrypted.
    """

    return bool(info.flag_bits & 0x1)


def validate_qcow2(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
) -> list[str]:

    errors: list[str] = []

    if info.file_size < 72:
        errors.append(
            f"{info.filename}: QCOW2 file is too small"
        )
        return errors

    try:
        with archive.open(info) as file:
            header = file.read(72)

    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(
            f"{info.filename}: cannot read QCOW2 "
            f"header: {exc}"
        )
        return errors

    if header[:4] != QCOW_MAGIC:
        errors.append(
            f"{info.filename}: invalid QCOW2 magic"
        )
        return errors

    version = struct.unpack(
        ">I",
        header[4:8],
    )[0]

    if version not in (2, 3):
        errors.append(
            f"{info.filename}: unsupported "
            f"QCOW2 version {version}"
        )

    return errors


def validate_webp(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
) -> list[str]:

    errors: list[str] = []

    if info.file_size < 12:
        errors.append(
            f"{info.filename}: WebP file is too small"
        )
        return errors

    try:
        with archive.open(info) as file:
            header = file.read(12)

    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(
            f"{info.filename}: cannot read WebP "
            f"header: {exc}"
        )
        return errors

    if header[:4] != b"RIFF":
        errors.append(
            f"{info.filename}: missing RIFF header"
        )
        return errors

    if header[8:12] != b"WEBP":
        errors.append(
            f"{info.filename}: missing WEBP signature"
        )

    return errors


def read_json(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
) -> tuple[dict | None, list[str]]:

    errors: list[str] = []

    if info.file_size > MAX_METADATA_SIZE:
        errors.append(
            f"{info.filename}: metadata exceeds "
            f"{MAX_METADATA_SIZE} bytes"
        )
        return None, errors

    try:
        with archive.open(info) as file:
            raw = file.read(MAX_METADATA_SIZE + 1)

    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(
            f"{info.filename}: cannot read JSON: {exc}"
        )
        return None, errors

    if len(raw) > MAX_METADATA_SIZE:
        errors.append(
            f"{info.filename}: metadata is too large"
        )
        return None, errors

    try:
        data = json.loads(
            raw.decode("utf-8")
        )

    except UnicodeDecodeError as exc:
        errors.append(
            f"{info.filename}: invalid UTF-8: {exc}"
        )
        return None, errors

    except json.JSONDecodeError as exc:
        errors.append(
            f"{info.filename}: invalid JSON: {exc}"
        )
        return None, errors

    if not isinstance(data, dict):
        errors.append(
            f"{info.filename}: JSON root must "
            f"be an object"
        )
        return None, errors

    return data, errors


def validate_metadata(
    data: dict,
    filenames: set[str],
) -> list[str]:

    errors: list[str] = []

    missing = (
        REQUIRED_METADATA_FIELDS - data.keys()
    )

    for field in sorted(missing):
        errors.append(
            f"rom-data.json: missing field "
            f"'{field}'"
        )

    if missing:
        return errors

    if not isinstance(data["author"], str):
        errors.append(
            "rom-data.json: 'author' must be string"
        )

    if not isinstance(data["title"], str):
        errors.append(
            "rom-data.json: 'title' must be string"
        )

    if not isinstance(data["qemu"], str):
        errors.append(
            "rom-data.json: 'qemu' must be string"
        )

    if not isinstance(data["desc"], str):
        errors.append(
            "rom-data.json: 'desc' must be string"
        )

    if not isinstance(data["arch"], str):
        errors.append(
            "rom-data.json: 'arch' must be string"
        )

    if not isinstance(
        data["versioncode"],
        int,
    ) or isinstance(
        data["versioncode"],
        bool,
    ):
        errors.append(
            "rom-data.json: 'versioncode' "
            "must be integer"
        )

    icon = data["icon"]

    if not isinstance(icon, str):
        errors.append(
            "rom-data.json: 'icon' must be string"
        )

    elif icon not in filenames:
        errors.append(
            f"rom-data.json: icon '{icon}' "
            "does not exist in archive"
        )

    return errors


def validate(path: Path) -> int:

    if not path.is_file():
        print(
            f"ERROR: file does not exist: {path}"
        )
        return 2

    size = path.stat().st_size

    if size == 0:
        print(
            "INVALID: CVBI file is empty"
        )
        return 1

    try:
        archive = zipfile.ZipFile(path)

    except (OSError, zipfile.BadZipFile) as exc:
        print(
            f"INVALID: not a valid ZIP CVBI: {exc}"
        )
        return 1

    errors: list[str] = []

    try:
        infos = archive.infolist()

        if len(infos) > MAX_ENTRY_COUNT:
            errors.append(
                f"too many archive entries: "
                f"{len(infos)}"
            )

        total_uncompressed = 0

        filenames: set[str] = set()

        qcow_files: list[zipfile.ZipInfo] = []
        metadata_info: zipfile.ZipInfo | None = None
        webp_files: list[zipfile.ZipInfo] = []

        for info in infos:

            name = info.filename

            if not safe_name(name):
                errors.append(
                    f"unsafe archive path: {name}"
                )
                continue

            filenames.add(name)

            if is_encrypted(info):
                errors.append(
                    f"encrypted entry is not allowed: "
                    f"{name}"
                )
                continue

            total_uncompressed += info.file_size

            if total_uncompressed > MAX_CVBI_SIZE:
                errors.append(
                    "archive exceeds 10 GiB "
                    "uncompressed limit"
                )
                break

            lower = name.lower()

            if lower.endswith(".qcow2"):
                qcow_files.append(info)

            elif lower == "rom-data.json":
                if metadata_info is not None:
                    errors.append(
                        "multiple rom-data.json files"
                    )
                else:
                    metadata_info = info

            elif lower.endswith(".webp"):
                webp_files.append(info)

        if not qcow_files:
            errors.append(
                "no QCOW2 image found"
            )

        if metadata_info is None:
            errors.append(
                "rom-data.json is missing"
            )

        if not webp_files:
            errors.append(
                "no WebP thumbnail found"
            )

        for info in qcow_files:
            errors.extend(
                validate_qcow2(
                    archive,
                    info,
                )
            )

        for info in webp_files:
            errors.extend(
                validate_webp(
                    archive,
                    info,
                )
            )

        if metadata_info is not None:
            data, metadata_errors = read_json(
                archive,
                metadata_info,
            )

            errors.extend(metadata_errors)

            if data is not None:
                errors.extend(
                    validate_metadata(
                        data,
                        filenames,
                    )
                )

    finally:
        archive.close()

    if errors:
        print("INVALID CVBI:")

        for error in errors:
            print(f"  - {error}")

        return 1

    print("VALID CVBI")
    return 0


def main() -> int:

    parser = argparse.ArgumentParser(
        description="Validate a Vectras CVBI file"
    )

    parser.add_argument(
        "cvbi",
        type=Path,
    )

    args = parser.parse_args()

    return validate(args.cvbi)


if __name__ == "__main__":
    sys.exit(main())