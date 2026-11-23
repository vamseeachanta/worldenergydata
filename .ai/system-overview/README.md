# System overview

This repository aggregates and analyses energy market data, including BSEE
(offshore production and drilling) and EIA (energy statistics). This page is a
navigation index; the [repository contract](../../AGENTS.md) governs task
execution.

## Repository map

- [Root source tree](../../src/worldenergydata/): shared orchestration, analysis
  and application entry points.
- [Workspace packages](../../packages/): domain distributions contributing to the
  `worldenergydata` namespace.
- [BSEE source](../../packages/worldenergydata-bsee/src/worldenergydata/bsee/):
  offshore data collection, processing and analysis.
- [EIA source](../../packages/worldenergydata-eia/src/worldenergydata/eia/):
  energy-statistics data access.
- [CLI entry point](../../src/worldenergydata/cli/main.py): the application behind
  the `worldenergydata` command declared in the package configuration.

## Development and checks

Python `>=3.10` is required by the [package configuration](../../pyproject.toml).
That file also declares dependencies, workspace members, the CLI binding and
pytest settings. Workspace packages need to be installed for domain imports;
adding only the root source directory does not expose all domains.

1. Read the repository contract and the task's acceptance criteria, inspect the
   affected code and data, and plan a bounded change before implementation.
2. Write a failing test for the intended behaviour, then make the change and run
   the affected tests. The [test collection guide](../../docs/development/test-collection.md)
   explains package imports, collection rules and remaining limitations.
3. Use the formatters, lint checks and file checks declared in the
   [hook configuration](../../.pre-commit-config.yaml). Consult the package
   configuration for tool settings rather than assuming versions or thresholds.
4. Preserve source inputs and existing behaviour outside the task's scope.
   Separate data access from calculations and make required inputs explicit;
   the [refactoring guide](../../docs/development/refactoring_guide.md) provides
   testability patterns. Its examples and target lists are historical guidance,
   not evidence of current APIs or coverage.
5. Review the diff against the acceptance criteria and record the checks run,
   their results and any unresolved limitations.

The [development index](../../docs/development/index.md) provides additional
background. Setup commands and tool claims in older prose need to be checked
against the package and hook configurations before use.

## Remaining documentation drift

The broader [AI guidelines](../AI_GUIDELINES.md) and
[development workflow](../workflows/development-process.md) remain follow-up work
under issue #48. Their older tool and instruction-file references are not
endorsed by this index. This update covers the system overview only; it does not
establish that all repository guidance is current.
