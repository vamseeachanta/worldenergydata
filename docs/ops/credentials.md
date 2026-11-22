# Scheduler credentials

## EIA US module

The EIA API v2 endpoints used by `eia_us_refresh` require an API key.
Register for a free key at [EIA Open Data](https://www.eia.gov/opendata/).
EIA documents the `api_key` request parameter in its
[API documentation](https://www.eia.gov/opendata/documentation.php).

Supply `EIA_API_KEY` in the environment of the scheduler process. An exported
variable in an interactive shell does not configure a separate scheduled service.
The scheduler does not load a `.env` file automatically. A nonempty `api_key`
setting in the job configuration takes precedence over `EIA_API_KEY`; an empty
setting falls back to the environment. Keep actual keys out of tracked files,
command history, logs and shared run evidence.

If neither source supplies a key, the job logs a warning and returns `skipped`,
zero updated records and `error_msg: credential_absent`. This is terminal for
that invocation: no ingestion request, output write or success manifest occurs.
A skip is not evidence of fresh data. Invalid supplied keys still follow the
normal ingestion failure path.

## Output and run evidence

The shipped `config/scheduler/scheduler_config.yml` explicitly sets
`output_dir: data/modules/eia_us`. Without a configured override, the adapter's
legacy default remains `data/modules/eia`. See the
[output directory guide](../guides/scheduler-output-directories.md) for data-root
overrides and timestamped output snapshots.

Once the key is supplied securely, run:

```bash
python -m worldenergydata.scheduler run-job eia_us_refresh \
  --config config/scheduler/scheduler_config.yml
```

The CLI has no `--dry-run` option. Use an isolated output directory and monitoring
paths in a local configuration when testing without updating operational data.
A real run can make API requests and write incremental JSONL, Parquet snapshots,
`_metadata.json`, and a scheduler `manifest.json`. Preserve the reported status,
record count, output file counts and successful manifest timestamp as evidence;
exclude credentials and local absolute paths. Tests with synthetic responses do
not establish a successful live refresh.
