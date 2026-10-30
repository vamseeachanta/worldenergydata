# Saved Explorer visualization API

The Pages Explorer can embed a server-rendered cumulative-oil chart from an
approved, immutable Hugging Face results release. The service checks the exact
bundle bytes and returns the dataset revision, analysis code revision, renderer
code revision and source digests alongside the SVG. Until a public service and
approved release are configured, each field panel shows a visible placeholder
linking [#966](https://github.com/vamseeachanta/worldenergydata/issues/966).

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Added pinned rendering, API, embedding and an offline replay to make saved results traceable. |

## Inputs and method

The service consumes `explorer_results_bundle.json` from the exporter in
`scripts/hf_export/build_explorer_results_bundle.py` (schema `1.0.0`, projection
`field_explorer_results`). It reads `fields[*].performance.cum_oil_mmbbl` in MMbbl
without conversion, interpolation, extrapolation or recalculation. Different
fields have different production histories; this is a snapshot comparison.
Missing values remain **unavailable**, not zero. Negative, Boolean, non-finite
and text-valued cumulative oil are rejected.

The only equation is an authored display rule: bar width = saved value /
maximum known saved value. If every known value is zero, every bar has zero
width. Layout coordinates and colors are presentation choices. No engineering
coefficient or engineering acceptance limit is introduced. The input metric,
unit and schema originate in the committed exporter and results card at
`reports/field-atlas/results/README.md`.

Hugging Face requires the full commit hash when downloading a specific commit;
see the [download guide](https://huggingface.co/docs/huggingface_hub/guides/download).
This API accepts only approved full hexadecimal Git commit hashes and never
resolves a branch, tag, short hash or `latest` reference. Public file download
uses the documented dataset `/resolve/{revision}/{filename}` route.

## Release approval and provenance

A maintainer supplies a manifest, using these required fields:

- `renderer_revision`: full commit hash of the deployed renderer source.
- `limits`: positive integer `request_bytes`, `bundle_bytes`, `timeout_seconds`.
  These are deployment resource choices, not engineering thresholds.
- `releases`: approved public release records, each containing `dataset_id`
  (`namespace/dataset`), full `dataset_revision`, full `source_revision`,
  relative JSON `bundle_path`, `bundle_sha256` and `public_data_approved: true`.

These records are trusted deployment configuration. Request callers cannot
choose a download URL, supply provenance, upload raw data or add a release.
Only listed public releases may be fetched. The service reads no HF token,
credential cache or login state. Private or gated data are unsupported.
The public-data approval field records a maintainer decision; software cannot
establish redistribution rights from a flag alone.

The source revision records the code that produced the saved analysis. It must
be established during publication; the existing bundle does not contain that
commit. The renderer revision records this service's code separately. A dataset
revision must map to exactly one manifest entry. Approval requires matching
public source snapshots, licensing evidence and the unmodified bundle's SHA-256.
Downloads and redirects support HTTPS only, without ambient proxy or
authentication handlers. The service verifies the downloaded byte digest before rendering and passes
through the bundle's source records. It does not independently retrieve and
rehash upstream source snapshots or authenticate the manifest's code claims.

## Service and documented request

The stdlib WSGI application is `create_app` in
`scripts/hf_export/explorer_visualization.py`. To start the included server:

```sh
EXPLORER_RENDER_MANIFEST=approved-releases.json \
  python scripts/hf_export/explorer_visualization.py
```

The manifest is required; missing approvals or floating revisions prevent
startup. The default port is `7860`, as documented in the
[Hugging Face Docker Spaces guide](https://huggingface.co/docs/hub/spaces-sdks-docker).
`PORT` can override it. Binding defaults to `localhost`; set `BIND_HOST`
explicitly for a container service. A Space can use the following files after maintainer
approval; upload only the reviewed service source and public manifest:

```yaml
# README.md front matter in the deployment repository
---
title: Saved Explorer charts
sdk: docker
app_port: 7860
---
```

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY explorer_visualization.py approved-releases.json ./
ENV EXPLORER_RENDER_MANIFEST=approved-releases.json
ENV BIND_HOST=0.0.0.0
CMD ["python", "explorer_visualization.py"]
```

The image version is a deployment compatibility choice, matching the repository's
Python baseline. Production deployment should pin an approved image digest and
provide gateway request limits and timeouts. The included WSGI server handles
one request at a time; hosting, load testing and deployment hardening are outside
this change. No deployment or remote rendering is performed by the example.

After deployment, use the exact approved dataset commit, never a floating ref:

```sh
curl --fail-with-body --request POST "$RENDER_ENDPOINT/render" \
  --header 'Content-Type: application/json' \
  --data "{\"dataset_revision\":\"$DATASET_COMMIT\",\"field_id\":\"$FIELD_ID\"}"
```

`field_id` is optional; it highlights one existing field in the chart. No field
filter changes the comparison population. The response is JSON with `media_type:
"image/svg+xml"`, `svg`, `metric`, `units`, `field_id`, `dataset_id`,
`dataset_revision`, `source_revision`, `renderer_revision`, `bundle_sha256`, and
`sources`. HTTP statuses distinguish invalid requests, unknown paths, excessive
request size, failed saved-data validation and unavailable downloads. Failure
responses always include the issue link and never echo upstream exception text.

The API supports credential-free CORS (`POST` and `OPTIONS`) for static Pages.
Do not put tokens in the endpoint URL or the browser configuration. A service
requiring authentication produces the visible placeholder rather than prompting
for or exposing credentials.

## Explorer embedding

Populate the existing `hf-viz-config` JSON script in
`reports/field-atlas/atlas_template.html` with the approved `endpoint` (full
HTTPS URL ending in `/render`), `dataset_id`, `dataset_revision`,
`source_revision`, `renderer_revision`, `bundle_sha256` and positive integer
`request_timeout_ms`. Then regenerate `reports/field-atlas/index.html` with
`scripts/field_atlas/build_field_atlas.py`. The template is the source of truth;
its empty object is deliberately unconfigured, with no fabricated live release.

The browser sends the pinned revision and current field ID. It compares every
returned provenance field with configuration before embedding the SVG in an
image context, never as remote HTML. The caption displays the revisions and
digest and warns that the saved snapshot can differ from the live field panel.
Missing configuration, timeout, authentication failure, mismatched provenance,
invalid media or metric, and image decoding failure show the issue-linked
placeholder. A response for a detached field panel is ignored after navigation.

## Worked example and answer

Run the executable offline example with an explicit output directory:

```sh
python examples/explorer_visualization_demo.py --output "$EXAMPLE_OUTPUT"
```

Its synthetic input values are 3, 6 and 0 MMbbl, plus an unavailable value.
By independent hand calculation, the maximum is 6 MMbbl, so the widths are
3 / 6 = **0.5**, 6 / 6 = **1.0** and 0 / 6 = **0.0**. The missing field has no bar
and an **unavailable** label. These invented test inputs are not observations.

The example saves `input_bundle.json`, `synthetic_manifest.json`,
`render_response.json` and `chart.svg`. Its fake download returns only the
synthetic bytes; it exercises the same API and digest validation without network
or credentials. Synthetic repeated-character revisions and the approval flag are
fixtures only. They must never be used as publication evidence or production
configuration. Tests independently check the arithmetic, response trace and the
saved SVG. No example output needs to be committed.

## Verification and limits

`tests/unit/site/test_explorer_visualization.py` checks the WSGI contract,
immutable allowlist, byte digest, source trace, numeric validation and worked
example. `tests/unit/site/test_explorer_visualization_embed.py` executes the
actual inline browser script under Node with mocked fetch and a minimal DOM.
The existing site tests cover Pages publication and the field-panel structure.
These tests do not prove a live Space is deployed or that an actual publication
has completed its separate review and rights checks.

The follow-up comment on #966 proposes a different website rendering surface.
This implementation remains specific to the Pages Explorer; it does not alter
that other surface or claim completion of publication work in #927 or #965.
