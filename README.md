# CVBI Converter

Community registry and distribution system for
Vectras VM `.cvbi` files.

The registry is packaged into a single archive:

cvbi.conv

The `conv` CLI can then extract the registry locally.

## Registry Structure

Contributors add their CVBI packages under:

cvbi-registry/<owner>/<package>/

Example:

cvbi-registry/
└── komandan/
    ├── arch/
    │   ├── MANIFEST
    │   ├── VERSION
    │   ├── LATEST
    │   └── arch-linux.cvbi
    │
    └── ubuntu/
        ├── MANIFEST
        └── ubuntu.cvbi

The owner directory must come before the package
directory.

This is invalid:

cvbi-registry/
└── arch/
    └── komandan/

The workflow will skip invalid registry entries.

## MANIFEST

Every package must contain:

MANIFEST

The file must exist and must be completely empty.

## VERSION

VERSION is optional.

If VERSION exists, it must contain a valid semantic
version.

Example:

1.0.0

The version is used when generating the final CVBI
filename.

Example:

debian-1.0.0.cvbi

## LATEST

LATEST is optional.

When used together with VERSION, it contains the
same version.

Example:

VERSION
1.0.0

LATEST
1.0.0

Pre-release versions are supported.

Example:

1.0.0-beta.1

## Package Names

Package names must not end with:

-<number>

For example:

ubuntu-1
debian-2
arch-123

These names are forbidden.

Version numbers belong in VERSION/LATEST, not in the
package directory name.

## CVBI Files

A package must contain at least one `.cvbi` file.

Only these files are allowed:

- MANIFEST
- VERSION
- LATEST
- *.cvbi

The maximum size of an individual CVBI file is
10 GiB.

## Pull Requests

1. Fork this repository.
2. Enter `cvbi-registry/`.
3. Create a directory using your username.
4. Create a package directory inside it.
5. Add `MANIFEST`.
6. Add your `.cvbi` file.
7. Optionally add `VERSION`.
8. Optionally add `LATEST`.
9. Commit your changes.
10. Open a Pull Request.

The GitHub Actions workflow automatically validates
the registry.

Invalid owners or packages are skipped.

Other valid registry entries can still be published.

## Generated Archive

The registry is distributed as one file:

cvbi.conv

The archive contains:

cvbi/
├── <owner>/
│   ├── <file>.cvbi
│   └── ...
└── ...

The original `cvbi-registry/` structure is not exposed
inside the final archive.

## Using cvbi.conv

After downloading `cvbi.conv`, use the `conv` CLI:

conv cvbi.conv -to ./output

The extracted result will look like:

output/
└── cvbi/
    ├── komandan/
    │   ├── arch-linux.cvbi
    │   └── ubuntu.cvbi
    └── zoder/
        └── debian-0.1.0.cvbi

Verify an archive with:

conv verify cvbi.conv

## Releases

Every successful registry build creates a GitHub
Release containing:

- cvbi.conv
- REGISTRY.txt
- SHA256SUMS

The release is identified by the source commit.

## Security

The generated archive is checked for unsafe paths
before publication.

Paths such as:

../file

or absolute paths are rejected.

The final archive must only contain files under:

cvbi/

## LICENSE

we use [MIT - LICENSE](./LICENSE)

## More info

for more info how to use cvbi-converter, see [More Info](./docs/more-info.md)