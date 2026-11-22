# Scheduler retry policy

Scheduler jobs return `JobResult.retryable` to distinguish failures that can
recover during the current run from failures that require configuration or
source-contract repair. Deterministic failures produce source-specific status
without consuming the remaining scheduler backoff. Unknown failures retain
retries. This completes the retry-policy scope of issue #460; it does not
establish live source freshness.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Document terminal source failures and a reproducible retry example. |

## Classification and method

| Outcome | Scheduler action | Evidence and repair |
| --- | --- | --- |
| `success` or `skipped` | Return immediately | Stubs remain skipped; implement the adapter before expecting freshness. |
| `failure`, `retryable=False` | Return immediately | Correct credentials, configuration, endpoint or static payload contract before another run. |
| `failure`, `retryable=True` | Retry within the configured attempt budget | Transient network/server errors and unclassified failures may recover. |
| Uncaught exception | Retry within the configured attempt budget | Unknown exceptions retain the existing policy; their messages are not classified by substring. |

Source adapters apply these contracts:

- EIA's typed `EIAKeyError` is terminal. Missing credentials cannot be supplied
  by waiting within the same run.
- LNG's unimplemented adapter returns `skipped`, which is terminal regardless
  of the retry flag.
- ANP's typed HTTP Not Found response and invalid ZIP are terminal. An invalid
  cached archive would otherwise be opened again. Explicit dates must contain
  `year` and either `month` or legacy `semester`; invalid or incomplete dates
  fail before constructing the download client. Omit all date fields to use
  the adapter's existing automatic selection.
- BSEE's scheduler opts into `raise_on_not_found=True` on
  `BSEEWebScraper.download_zip_to_memory`. A typed HTTP Not Found response
  escapes the scraper's retry loop and becomes a deterministic dataset failure.
  The default scraper API retains its previous retry-and-return-`None` behavior
  for other callers. HTML, empty bodies and static archive-member contract
  failures already have deterministic classification. Corrupt ZIP downloads,
  unknown bodies, timeouts and server errors retain transient classification.

HTTP status meanings follow [RFC 9110 (2022), section 15.5.5 (Not Found)
and section 15.6 (Server Error)](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.5).
Stopping a configured Not Found endpoint is a policy for the current run.
The standard explicitly does not establish whether that absence is permanent.
No other HTTP client error is made terminal by this change.

BSEE processes datasets independently. If every remaining failure is
deterministic, scheduler backoff stops. If a transient failure remains, the job
still retries. Existing deterministic partial-success semantics are retained.

`JobLogger` and `StatusReporter` persist `retryable` alongside the source name,
status and error. A failed or skipped run does not write a success manifest.
An earlier success manifest, if present, continues to describe the earlier run.

## Worked example

All retry budgets and delays in this example are explicit synthetic inputs,
not recommended operating limits. The method is the existing
`RetryManager.backoff_delay`: for initial delay `b` and zero-based failed attempt
`a`, delay is `b * 2**a`. The general exponential-backoff method is described in
[AWS Architecture Blog, “Exponential Backoff And Jitter” (2015)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/).
The scheduler retains its existing doubling rule, without introducing that
article's cap or jitter.

Inputs: `max_retries=3` (the total attempt budget), `backoff_seconds=1`, and a
callable that returns a failed `JobResult` on every invocation. Hand calculation:

- For a terminal failure: call once, then return; no delay is incurred.
- For a retryable failure: call, sleep `1 * 2**0 = 1` second, call, sleep
  `1 * 2**1 = 2` seconds, call, then return the last failure.
- Total retryable backoff is `1 + 2 = 3` seconds; no sleep follows the last call.

The following example uses simulated results and a sleep spy, so it performs
neither downloads nor real waits:

```python
from datetime import datetime
from unittest.mock import Mock, patch

from worldenergydata.scheduler.jobs.base import JobResult
from worldenergydata.scheduler.monitor import RetryManager

# Synthetic example inputs; expected counts are derived above.
for retryable in (False, True):
    now = datetime.now()
    failure = JobResult(
        "example_refresh", now, now, "failure", 0, "example", retryable=retryable
    )
    run = Mock(return_value=failure)
    with patch("worldenergydata.scheduler.monitor.time.sleep") as sleep:
        RetryManager(max_retries=3, backoff_seconds=1).run_with_retry(run)
    print(retryable, run.call_count, [args.args[0] for args in sleep.call_args_list])
```

Answer:

```text
False 1 []
True 3 [1, 2]
```

`tests/unit/bsee/test_bsee_web_retry.py` traces actual typed scraper errors,
legacy behavior and transient recovery. The additional cases in
`tests/unit/scheduler/test_retry_classification.py` trace invalid ANP dates and
the real BSEE scraper through `DataScheduler.run_once`, structured logs and
status output, with sleeps intercepted. Existing tests in that module cover
missing EIA credentials, stubs, ANP endpoint/archive failures and BSEE HTML.

## Limits and next steps

No live refresh, credential provisioning, endpoint repair, automatic cache
deletion or scheduler-service restart is performed here. For a terminal failure,
inspect the source status, repair its reported configuration or payload contract,
and trigger another run. For a transient failure, inspect the final error after
the configured attempts. Live freshness and source implementation remain the
scope of the linked source-health issues.
