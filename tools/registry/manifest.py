from __future__ import annotations

import argparse
import sys
from pathlib import Path


def error(message: str) -> None:
    print(f"ERROR: {message}")


def generate_manifest(
    registry: Path,
    output: Path,
) -> int:

    if not registry.is_dir():
        error(
            f"registry not found: {registry}"
        )
        return 2

    entries: list[str] = []

    for owner in sorted(
        registry.iterdir(),
        key=lambda p: p.name.lower(),
    ):

        if not owner.is_dir():
            continue

        for package in sorted(
            owner.iterdir(),
            key=lambda p: p.name.lower(),
        ):

            if not package.is_dir():
                continue

            for cvbi in sorted(
                package.glob("*.cvbi"),
                key=lambda p: p.name.lower(),
            ):

                # Manifest represents the FINAL
                # cvbi.conv path, not the registry path.
                #
                # registry:
                #
                # owner/package/file.cvbi
                #
                # becomes:
                #
                # cvbi/owner/file.cvbi
                #
                entries.append(
                    f"{owner.name}/{cvbi.name}"
                )

    entries = sorted(
        set(entries),
        key=str.lower,
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:

            file.write(
                "# CVBI Registry Manifest\n"
            )

            file.write(
                "# Generated automatically.\n"
            )

            file.write(
                "#\n"
            )

            file.write(
                f"# CVBI files: {len(entries)}\n"
            )

            file.write(
                "\n"
            )

            for entry in entries:
                file.write(
                    f"cvbi/{entry}\n"
                )

    except OSError as exc:
        error(
            f"failed to write manifest: {exc}"
        )
        return 1

    print(
        f"Generated {output}"
    )

    print(
        f"Entries: {len(entries)}"
    )

    return 0


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Generate a CVBI registry manifest"
        )
    )

    parser.add_argument(
        "registry",
        type=Path,
    )

    parser.add_argument(
        "output",
        type=Path,
    )

    args = parser.parse_args()

    return generate_manifest(
        args.registry,
        args.output,
    )


if __name__ == "__main__":
    sys.exit(main())