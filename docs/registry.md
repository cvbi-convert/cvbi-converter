# CVBI Registry Specification

## Root

All registry entries must exist under:

cvbi-registry/

The first directory is the owner.

cvbi-registry/<owner>/

The package path follows the owner and may contain nested directories.

cvbi-registry/<owner>/<package>/

or:

cvbi-registry/<owner>/<category>/<package>/

Package Contents

A valid package contains:

MANIFEST
*.cvbi

It may additionally contain:

VERSION
LATEST

## MANIFEST

"MANIFEST" is required.

It must:

- have no extension
- exist inside the package directory
- contain zero bytes
- not contain user-defined metadata

An invalid "MANIFEST" causes the package to be skipped.

## CVBI

At least one ".cvbi" file must exist in a package.

A package without a ".cvbi" file is skipped.

CVBI files must not exceed:

10 GiB

The size check must be performed before expensive processing.

## VERSION

"VERSION" is optional.

When present, it must contain a valid version identifier.

The version is used when generating the published CVBI filename.

Example:

VERSION
1.0.0

Result:

package-1.0.0.cvbi

## LATEST

"LATEST" is optional.

When present, it identifies the release channel.

Supported channels include:

LTS
BETA

Example:

VERSION
1.0.0

LATEST
LTS

Result:

package-1.0.0-LTS.cvbi

Beta:

VERSION
1.1.0

LATEST
BETA

Result:

package-1.1.0-BETA.cvbi

Invalid Registries
Registry processing is isolated.
An invalid owner causes that owner to be skipped.
An invalid package causes that package to be skipped.
The workflow then continues with the next valid owner or package.

Example:

```Code
cvbi-registry/
├── komandan/
│   ├── arch/       → VALID
│   └── broken/     → SKIPPED
├── zoder/          → SKIPPED
└── nasa/
    └── debian/     → VALID
```

A single invalid registry must never prevent unrelated valid registries from being processed.

## SHA-256

Every processed CVBI must be hashed using SHA-256.
Hashing must be performed using streaming I/O so that large CVBI files do not need to be loaded into memory.
The SHA-256 result is used for integrity checking, caching, and deterministic packaging.

## Filename Collisions

CVBI filenames are not required to match package directory names.
The package path is the source of package identity.
If multiple packages contain CVBI files with the same filename, the packaging system must use the package identity when creating ".conv" releases so unrelated packages do not collide.

## Version Collisions

If a version already exists, processing that registry is skipped.
The workflow reports:

ERROR: version 1.0.0 already exists, skipping to other registry

Processing then continues with the next registry.

## Forbidden Names

Registry paths must follow strict naming rules.
Path traversal, separators inside individual path components, whitespace where prohibited, and other invalid path forms are rejected.
Names ending in the forbidden **-<number>** pattern are not permitted.