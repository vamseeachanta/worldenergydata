"""Replay recorded NDBC/CO-OPS days; --live opts into current public requests.

Input dates, stations and publisher evidence are described in
 docs/data-sources/metocean-endpoint-audit.md. Offline replay traverses the same
request construction and parsers as live retrieval, using the committed samples.
Recorded-sample sha256 digests cover text bytes with CRLF normalized to LF;
all other bytes remain significant. Publisher raw_sha256 values describe the
original responses, before the recorded-sample transformations.
"""

import argparse
import csv
import hashlib
import io
import json
from datetime import date
from pathlib import Path

import httpx

from worldenergydata.metocean.station_day import fetch_station_day, summarize_day


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    # These defaults are observed inputs, not engineering constants; provenance
    # is tests/fixtures/metocean/endpoints/provenance.json.
    parser.add_argument("--ndbc-station", default="42001")
    parser.add_argument("--coops-station", default="9414290")
    parser.add_argument(
        "--ndbc-day", type=date.fromisoformat, default=date(2026, 10, 21)
    )
    parser.add_argument(
        "--coops-day", type=date.fromisoformat, default=date(2025, 1, 1)
    )
    parser.add_argument("--user-agent")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.live and (not args.user_agent or args.timeout is None):
        parser.error("--live requires --user-agent and --timeout")
    fixtures = Path(__file__).resolve().parents[2] / "tests/fixtures/metocean/endpoints"
    payloads = {}
    recorded_urls = {}
    if not args.live:
        manifest = json.loads(
            (fixtures / "provenance.json").read_text(encoding="utf-8")
        )
        for entry in manifest["samples"]:
            content = (fixtures / entry["file"]).read_bytes()
            normalized = content.replace(b"\r\n", b"\n")
            if hashlib.sha256(normalized).hexdigest() != entry["sha256"]:
                raise ValueError("Recorded sample digest mismatch")
            payloads[entry["source"]] = content
            recorded_urls[entry["source"]] = httpx.URL(entry["url"])

    def replay(request):
        source = "ndbc_realtime" if request.url.host == "www.ndbc.noaa.gov" else "coops"
        if source == "ndbc_realtime" and request.url != recorded_urls[source]:
            raise ValueError("Offline request does not match recorded sample")
        return httpx.Response(200, content=payloads[source])

    options = {"trust_env": False}
    if args.live:
        options["timeout"] = args.timeout
    else:
        options["transport"] = httpx.MockTransport(replay)
    with httpx.Client(**options) as http:
        rows = [
            summarize_day(
                fetch_station_day(
                    source,
                    station,
                    day,
                    http=http,
                    user_agent=args.user_agent or "recorded-example (offline replay)",
                )
            )
            for source, station, day in [
                ("ndbc_realtime", args.ndbc_station, args.ndbc_day),
                ("coops", args.coops_station, args.coops_day),
            ]
        ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    if args.output:
        args.output.write_text(output.getvalue(), encoding="utf-8", newline="\n")
    else:
        print(output.getvalue(), end="")


if __name__ == "__main__":
    main()
