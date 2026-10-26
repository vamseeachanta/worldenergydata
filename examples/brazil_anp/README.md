# List resources from saved ANP index HTML

This example makes the existing metadata-only discovery fallback runnable against
caller-supplied UTF-8 HTML. It never fetches a URL or downloads production data.
Live REST availability remains outside this example.

From the repository root, with Python available, expose the source packages and
choose the index matching the saved page:

```sh
export PYTHONPATH=src:packages/worldenergydata-brazil_anp/src
python examples/brazil_anp/list_saved_production_resources.py saved-well-index.html --index well
python examples/brazil_anp/list_saved_production_resources.py saved-national-index.html --index national
```

`--index well` selects the existing `WELL_PRODUCTION_INDEX` constant;
`--index national` selects `NATIONAL_PRODUCTION_INDEX`. The example passes the
saved text and selected constant to `parse_production_resources`; it does not
accept an arbitrary index address.

Standard output is a JSON array with `url`, `title`, `format` and `index_url` for
each resource. Relative links resolve against the selected index; titles have
normalized whitespace and decoded HTML entities. Duplicate URLs retain the first
title in document order. Empty or unrelated HTML, unreadable files and invalid
UTF-8 fail with a nonzero exit and no JSON output, rather than emitting a
successful empty dataset.

A parsed publication link establishes neither payload availability nor REST API
existence, units or reuse rights. The declared format comes from the existing
index rules, without checking payload bytes. Saved HTML may be stale, altered or
from another source; selecting an index supplies resolution context and does not
authenticate the saved page. No new dataset, live API finding or transport-policy
change is introduced.
