# Contributing to the CVBI Registry

Thank you for contributing to the CVBI Registry.

## Before You Start

You must fork this repository.

Do not directly modify another user's registry.

Your registry must follow:

cvbi-registry/<owner>/<package>/

## Owner

The first directory is your owner/username.

Example:

cvbi-registry/komandan/

The owner directory must contain package directories.

Correct:

cvbi-registry/
└── komandan/
    └── arch/

Incorrect:

cvbi-registry/
└── arch/
    └── komandan/

## Package

Create a package directory with any valid name.

Example:

cvbi-registry/komandan/arch/

Do not end the package name with:

-<number>

Examples that are forbidden:

arch-1
ubuntu-2
debian-123

Use VERSION for versions instead.

## Required MANIFEST

Every package must contain:

MANIFEST

It must be completely empty.

Example:

cvbi-registry/komandan/arch/MANIFEST

Do not put text inside it.

## CVBI

Every package must contain at least one `.cvbi` file.

Example:

cvbi-registry/komandan/arch/
├── MANIFEST
└── arch-linux.cvbi

The maximum CVBI file size is 10 GiB.

## VERSION

VERSION is optional.

When present, it must contain a valid semantic
version.

Example:

1.0.0

For a beta release:

1.0.0-beta.1

The version is used when creating the final filename.

For example:

VERSION:

1.0.0

may produce:

arch-1.0.0.cvbi

## LATEST

LATEST is optional.

When VERSION exists, LATEST may be used to identify
the latest release.

Example:

VERSION:

1.0.0

LATEST:

1.0.0

Beta versions are supported:

LATEST:

1.1.0-beta.1

## Pull Request Validation

When your Pull Request is checked, the workflow
validates your registry.

An invalid package does not necessarily invalidate
the entire registry.

For example:

cvbi-registry/
├── komandan/
│   ├── valid/
│   └── broken/
│
└── zoder/
    └── valid/

If `komandan/broken` is invalid, it is skipped.

The workflow can continue with:

komandan/valid
zoder/valid

## Duplicate Versions

If a version already exists, the registry entry is
skipped.

Example:

ERROR: version 1.0.0 already exists, skipping to other registry

The workflow continues looking for other valid
registry entries.

## Pull Request Checklist

Before opening a Pull Request, verify:

- [ ] Correct owner directory
- [ ] Correct package directory
- [ ] `MANIFEST` exists
- [ ] `MANIFEST` is empty
- [ ] At least one `.cvbi` exists
- [ ] CVBI files are <= 10 GiB
- [ ] Package name does not end in `-<number>`
- [ ] `VERSION` is valid if present
- [ ] `LATEST` is valid if present
- [ ] `LATEST` matches `VERSION` when both exist
- [ ] No unsupported files are present

## Final Packaging

After validation, valid CVBI packages are combined
into one:

cvbi.conv

The final archive uses this structure:

cvbi/
└── <owner>/
    └── <file>.cvbi

The package directory is intentionally removed from
the final structure.

Users can extract it with:

conv cvbi.conv -to ./output