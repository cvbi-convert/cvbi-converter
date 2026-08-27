from __future__ import annotations

import json
import zipfile
from pathlib import Path


def create_cvbi(
    output: Path,
    *,
    valid: bool = True,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rom_data = {
        "author": "CVBI Test",
        "icon": "thumbnail.webp",
        "qemu": (
            "-M pc "
            "-m 512M "
            "-drive file=test.qcow2,"
            "if=none,id=hda "
            "-device virtio-blk,drive=hda"
        ),
        "arch": "X86_64",
        "title": "Test CVBI",
        "drive": "",
        "versioncode": 1,
        "cdrom": "",
        "desc": "<p>Test CVBI</p>",
    }

    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        # A tiny fake QCOW2-like payload.
        #
        # For the registry tests we don't need a real
        # virtual disk. validate_cvbi.py can decide
        # whether the fixture is structurally valid.
        if valid:
            qcow2 = (
                b"QFI\xfb"
                + b"\x00\x00\x00\x03"
                + b"\x00" * 64
            )
        else:
            qcow2 = b"INVALID-CVBI"

        archive.writestr(
            "test.qcow2",
            qcow2,
        )

        archive.writestr(
            "rom-data.json",
            json.dumps(
                rom_data,
                ensure_ascii=False,
            ),
        )

        # Minimal valid WebP header.
        thumbnail = (
            b"RIFF"
            + b"\x24\x00\x00\x00"
            + b"WEBP"
            + b"VP8 "
            + b"\x18\x00\x00\x00"
            + b"\x00" * 24
        )

        archive.writestr(
            "thumbnail.webp",
            thumbnail,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "usage: create_test_cvbi.py <output.cvbi>"
        )
        raise SystemExit(2)

    create_cvbi(
        Path(sys.argv[1])
    )

    print(
        f"Created test CVBI: {sys.argv[1]}"
    )