# Independent package artifact checks

## Summary

The existing workspace already builds independently versioned domain wheels.
The ownership check validates those artifacts together before CI uploads them.
It detects namespace initializer conflicts and files that would overwrite each
other during installation, without importing domain code or its dependencies.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add artifact ownership checks because source imports can hide overlapping wheels. |

## Contract

The rules extend [ADR 0001](../adr/0001-domain-package-split.md), especially its
namespace-root ownership risk:

- The `worldenergydata` distribution alone may ship
  `worldenergydata/__init__.py`. A selection containing only namespace member
  wheels does not require the root distribution.
- A file under `worldenergydata/` belongs to a single selected distribution.
  This includes package data, even when duplicate files have identical contents:
  uninstalling either distribution could remove the other's file.
- Library files under a wheel's `.data/purelib/` or `.data/platlib/` directory
  are checked at their installed destinations, following
  [PEP 427 (2013), File contents and The .data directory](https://peps.python.org/pep-0427/).
  Both library destinations are conservatively treated as shared.
- Distribution names are compared using
  [PEP 503 (2015), Normalized Names](https://peps.python.org/pep-0503/#normalized-names).
  Multiple versions of the same distribution are rejected in a co-installation
  selection. Versions of different distributions remain independent.
- Missing or ambiguous top-level `METADATA`, missing identity fields, unreadable
  archives and an empty selection fail the check.

Run the checker on exactly the wheels intended for a shared installation:

```sh
python scripts/ci/check_wheel_ownership.py dist/*.whl
```

The CI build checks all workspace wheels after its existing build command and
before artifact upload. Packaging unit tests construct archive member lists
independently: expected collisions are their installed-path intersections.
There are no engineering equations, coefficients or acceptance tolerances.

## Validation evidence

The packaging suite passes 21 cases, covering independent member selections,
root ownership, relocated library files, data collisions, normalized identities,
malformed metadata, invalid archives and command exit status. All 39 workspace
wheels were built from tracked inputs in a separate build tree and passed the
ownership check. These counts describe this revision's observed outputs.

An isolated environment containing the built core and EIA wheels plus `requests`
and its dependencies imported `worldenergydata.eia` without the root distribution
or any other domain. The smoke check confirmed separate distribution metadata,
implicit namespace discovery and an ingestion-state persistence round trip.
Expected versions came from the member manifests; the persisted value was a
synthetic input compared with itself after reloading. No network feed was called.

## Limits and later slices

This check covers library files under `worldenergydata/`. It is not a complete
wheel-format validator, dependency resolver or compatibility check. It does not
verify RECORD hashes, scripts or data installed outside the namespace. It also
does not detect omitted payloads or missing artifacts in a selected release.

The isolated smoke installed the member wheels without resolving their complete
runtime dependency closure; it did not import the shared core's public API.
The aggregate distribution's regular namespace root and editable installs remain
covered separately by `tests/unit/common/test_namespace_workspace.py`.

Later work includes independent release selection and version constraints,
complete dependency closure checks, broader installed-domain smoke coverage and
downstream consumer validation. No distribution was published or version changed.
