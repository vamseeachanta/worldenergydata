# Print-to-logging migration

The migration previews conservative changes from standalone `print(value)`
expressions to logging calls. Setup uses complete AST statement boundaries so
multiline imports remain valid. Review the diff before saving it.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-22 | Document AST insertion, explicit writes and unsupported calls. |

## Run the migration

From the repository root, preview a file or directory:

```sh
python scripts/migrate_print_to_logging.py src/worldenergydata
```

Preview is the default and prints a unified diff. To save validated candidates:

```sh
python scripts/migrate_print_to_logging.py src/worldenergydata --write
```

The script parses the original and candidate before writing. A syntax or
encoding error prints a skip message and leaves the original bytes intact.
A failed write attempts to restore the original bytes; a persistent storage
failure still requires recovery by the caller. Existing encoding cookies,
line endings, strings and comments are preserved.

## Worked example

Input `example.py`:

```python
from pathlib import (
    Path,
)
print("ready")
```

Preview from `python scripts/migrate_print_to_logging.py example.py`:

```diff
--- example.py
+++ example.py
@@ -1,4 +1,8 @@
 from pathlib import (
     Path,
 )
-print("ready")
+
+from worldenergydata.common.logging import get_logger
+
+logger = get_logger(__name__)
+logger.info("ready")
```

The hunk counts follow by hand: the input has four lines; replacing its final
line with a blank line, an import, a blank line, setup and a logging call gives
eight output lines. The parenthesised import retains its closing line.

Output after adding `--write`:

```python
from pathlib import (
    Path,
)

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)
logger.info("ready")
```

## Scope and limits

- Setup follows the module docstring and the last top-level import, including
  future imports. Conditional imports remain inside their original block.
- Without a docstring or imports, setup follows leading comments, the shebang
  and encoding cookie.
- Files that bind `logger` are unchanged, including on a second run. A plain
  existing `get_logger` import can be reused.
- Only standalone calls to an unshadowed `print` with one non-starred argument
  and no keywords are converted. Calls using `file`, `sep`, `end`, `flush`,
  multiple arguments or a used return value are left for manual migration.
- An f-string starting with `ERROR` or `Error` selects error logging;
  `Warning` or `WARN` selects warning logging. Other eligible calls use info.
- A binding named `print` in any scope or a wildcard import skips the file
  conservatively. Dynamic
  rebinding cannot be resolved statically. A print before a later top-level
  import also skips the file so it cannot execute before logger setup.
- Logging has its configured filtering and destination; converting a console
  interface still requires a behavior review.

Check source syntax without importing source modules:

```sh
python scripts/check_python_syntax.py
```

This scans every `.py` file under `src/` and `packages/`, prints the current
count and every parse failure, and exits unsuccessfully when a file fails.

## Source and tests

[Python 3.11 `ast.AST` node positions](https://docs.python.org/3.11/library/ast.html#ast.AST)
defines line positions as one-indexed and column offsets as UTF-8 byte offsets.
The migration uses `end_lineno` for insertion and byte offsets for replacing
only the function name. Tests contain independent literal input/output pairs,
including the worked example, rather than deriving expected output from the
migration implementation.

```sh
uv run --no-project --with pytest python -m pytest \
  tests/unit/scripts/test_migrate_print_to_logging.py \
  tests/unit/scripts/test_check_python_syntax.py \
  --noconftest -o addopts='' -q -rA -p no:cacheprovider
```
