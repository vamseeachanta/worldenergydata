# worldenergydata-core

Shared cross-cutting core for the [`worldenergydata`](https://github.com/vamseeachanta/worldenergydata)
namespace. First member of the uv workspace introduced by the domain-package
split (ADR 0001 / epic #526, issue #529).

Ships `worldenergydata.common` — configuration, logging, exceptions, constants,
type aliases, units, the data resolver, and the `common.legacy` helpers — the
fan-in-26 shared infrastructure every domain depends on.

This distribution is **namespace-only**: it contributes `worldenergydata.common`
to the shared `worldenergydata` PEP 420 / `pkgutil` namespace but does **not**
own the namespace root `worldenergydata/__init__.py`. The root `worldenergydata`
distribution remains the sole owner of that root module (version, `_compat`
legacy redirect, lazy `__getattr__`, `pkgutil.extend_path`).

Installed automatically as a workspace member when you `uv sync` the root repo;
the root `worldenergydata` package depends on it via `[tool.uv.sources]`.
