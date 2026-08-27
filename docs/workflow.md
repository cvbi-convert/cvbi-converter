# CVBI Converter Workflow

The repository uses GitHub Actions to validate and publish CVBI registry entries.

## Pull Request Validation

A Pull Request triggers registry validation.
The workflow scans:

cvbi-registry/
It processes each owner independently.

owner A → VALID → process
owner B → INVALID → SKIP
owner C → VALID → process

Inside a valid owner, packages are also processed independently.

package A → VALID → process
package B → INVALID → SKIP
package C → VALID → process

## Validation Order

Validation should perform inexpensive checks before expensive processing.

Recommended order:

1. Validate path structure.
2. Identify owner.
3. Identify package.
4. Check package contents.
5. Check for ".cvbi".
6. Check CVBI size.
7. Validate "MANIFEST".
8. Validate "VERSION".
9. Validate "LATEST".
10. Calculate SHA-256.
11. Perform CVBI validation.
12. Mark the registry as valid.

The 10 GiB size check must happen before expensive CVBI processing.

## SHA-256 Cache

SHA-256 hashes may be cached between workflow runs.

If an unchanged CVBI has already been processed, the workflow may reuse its cached result instead of repeating expensive work.

Cache invalidation must be based on the CVBI content hash.

## Skip Behavior

A failure inside one registry must not terminate processing of unrelated registries.

Example:

komandan → VALID
zoder    → INVALID → SKIP
nasa     → VALID
test     → INVALID → SKIP

Processing continues until all registries have been examined.

## Actions Summary

Every validation or publish run must generate a GitHub Actions Summary.

The summary should contain:

- valid registries
- skipped registries
- skip reasons
- processed CVBI count
- skipped CVBI count
- published packages
- version collisions
- total processing result

## Publishing

Publishing occurs only after the appropriate registry changes have passed validation and are available on the publishing branch.

The publishing process:

Registry
   ↓
Validate
   ↓
SHA-256
   ↓
Build deterministic .conv
   ↓
Generate metadata
   ↓
Generate checksum
   ↓
Optional signature
   ↓
GitHub Release

## Deterministic Packaging

The same registry input must produce the same ".conv" output.

The packaging process must therefore control:

- file ordering
- metadata ordering
- timestamps
- padding
- compression settings
- path encoding
- checksum calculation

## Version Collision

If a release version already exists:

ERROR: version 1.0.0 already exists, skipping to other registry

The current registry is skipped and processing continues.

## Release Metadata

Each release must include metadata describing:

- number of owners
- number of packages
- number of processed registries
- number of skipped registries
- CVBI count
- total size
- skipped registry reasons
- release version

".conv"

The ".conv" binary format is specified separately in the format specification.

The format must support:

- deterministic packaging
- CVBI metadata
- SHA-256
- large files
- optional signatures
- integrity verification