#!/usr/bin/env python3
"""Fetch and OCR BSEE scanned right-of-way (ROW) files and pipeline maps.

Goal: find wall thickness, grade and riser geometry for the riser segments in
``data/modules/bsee/pipeline_risers/riser_segments.csv`` that lack a stated wall
thickness. Each host takes one shard of the documents (DOC_ID modulo N) and runs
this script as a slow, resumable, low-priority background job:

* one request at a time, at least 60 s apart (``--gap``), and only inside the
  fetch window (``--window``, default 01:00-11:00 UTC);
* robots.txt is read before the first fetch and obeyed; a bar stops the job;
* HTTP 403, 429 and 503 are refusals: Retry-After is honoured, otherwise the
  wait starts at 15 min and doubles up to 4 h; ten errors end the UTC day; three
  failures on one document mark it failed and the job moves on;
* OCR (pdftoppm at 300 dpi, then tesseract, one page at a time) runs at the
  lowest CPU and I/O priority and pauses while the 5-minute load is high;
* per-page text goes to ``text/<KIND>/<DOC_ID>/page-NNNN.txt``; page images are
  removed once their text is written; every event adds a JSON line to
  ``manifest.jsonl``;
* state is one SQLite file and downloads are written to ``.part`` names, so a
  killed run loses at most one document; work already done is skipped;
* a ``STOP`` file in the data directory ends the job at the next document or
  page.

Inputs: the public scan index ``ScannedDocsRawData.zip`` (fetched into the data
directory on the first run inside the window, or given with ``--index-zip``) and
the riser segment table (``--segments``). Each host builds its own shard queue.

Pass order (``--max-pass``, default 1): 1 = tier B segments in 1,000 ft of water
or more; 2 = the rest of tier B; 3 = all other riser segments.

Configuration basis: #2086, initial Config and "How it behaves" / "Order",
records a 1,000 ft queue-priority cutoff, a 60 s gap, a 01:00-11:00 UTC window,
10 errors per day, three attempts, 15 min to 4 h backoff, 50 GB free, 100 % used,
load 8 and 300 dpi. These are operating choices, not engineering limits; the
depth cutoff only orders work. The initial grade allowlist (X52, X56, X60, X65,
X70) is a search heuristic assumed, based on previous experience, retained as
the candidate-search configuration in #2086; it is not a complete grade list.
OCR matches require source-page and unit verification before any tier change.
Collector configuration basis: #2086, "Collector configuration basis" comment.
The HTTP timeout is 300 s to bound a stalled
request; each OCR command has 1,800 s to allow a large scan without an unbounded
tool process. Candidate searches span at most 40 characters after "riser" and
20 after an angle label to keep matches near their labels. These are conservative
search and runtime choices for this collector, not source or engineering limits.
Ungrouped riser lengths use two to five digits to reduce single-digit noise and
long identifier matches; comma-grouped lengths retain all groups. This is an
assumed search heuristic, based on previous experience, recorded in the same
configuration decision, not a physical length limit.

Commands::

    row_scan_ocr.py run --data-dir DIR --shard K/N --segments riser_segments.csv
    row_scan_ocr.py status --data-dir DIR
    row_scan_ocr.py findings --data-dir DIR --out findings.csv

Exit codes: 0 done for now; 2 bad arguments or wrong data directory; 3 robots.txt
bars the path; 4 disk floor reached; 5 index or segment input missing or invalid.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

BASE = "https://www.data.bsee.gov"
HOST = "www.data.bsee.gov"
ROBOTS_URL = BASE + "/robots.txt"
INDEX_ZIP_URL = BASE + "/Other/Files/ScannedDocsRawData.zip"
INDEX_ZIP_NAME = "ScannedDocsRawData.zip"
# Links on the Scanned Documents pages look like /PDFDocs/Scan/ROW/32/32733.pdf and
# /PDFDocs/Scan/PIPEMAPS/19/19963.pdf. The folder is read as DOC_ID // 1000 (both
# sample links fit). This URL rule is an assumption. A 404 marks the document
# failed, with its reason.
DOC_URL = BASE + "/PDFDocs/Scan/{kind}/{folder}/{doc_id}.pdf"
INDEX_MEMBERS = {"ROW": "scan_row.txt", "PIPEMAPS": "scan_pipeline_maps.txt"}
USER_AGENT = (
    "WorldEnergyData-public-fetcher/1.0 (public research; one request a minute)"
)
REFUSALS = {403, 429, 503}
GONE = {404, 410}
STOP_FILE = "STOP"
QUEUE_KEY_VERSION = "v2"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Clock:
    """Wall clock; tests pass a fake with the same two methods."""

    def now(self) -> datetime:
        return utcnow()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass
class Response:
    status: int  # 0 = network error
    headers: dict = field(default_factory=dict)  # lower-case names
    body: bytes = b""  # empty when the body was streamed to a file
    error: str = ""


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Defer every redirect: urllib must not issue an unchecked second GET.
        return None


_OPENER = urllib.request.build_opener(_SameHostRedirect)


def http_fetch(url: str, dest: Path | None = None, timeout: float = 300) -> Response:
    """GET one URL; stream the body to ``dest`` when given."""
    p = urlparse(url)
    if p.scheme != "https" or p.hostname != HOST:
        return Response(0, error=f"refused URL outside {HOST}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            if dest is None:
                return Response(resp.status, headers, resp.read())
            with open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh, 1 << 20)
            return Response(resp.status, headers)
    except urllib.error.HTTPError as err:
        headers = {k.lower(): v for k, v in (err.headers or {}).items()}
        return Response(err.code, headers, error=str(err))
    except (urllib.error.URLError, OSError) as err:
        return Response(0, error=str(err))


def run_low(cmd: list[str]) -> tuple[int, str]:
    """Run an OCR tool at low priority with one thread; return (code, stdout)."""
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    # Windows: below-normal priority, and no console window when started from a
    # scheduled task under pythonw.exe.
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) | getattr(
        subprocess, "CREATE_NO_WINDOW", 0
    )
    try:
        done = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            env=env,
            timeout=1800,
            check=False,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError) as err:
        return 1, str(err)
    return done.returncode, done.stdout


def lower_own_priority() -> None:
    """nice 19 and idle I/O class on Linux; below-normal class on Windows."""
    if os.name == "nt":
        try:
            import ctypes

            k32 = ctypes.windll.kernel32
            k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)
        except Exception:  # noqa: BLE001 - best effort only
            pass
        return
    try:
        cur = os.nice(0)
        if cur < 19:
            os.nice(19 - cur)
    except OSError:
        pass
    ionice = shutil.which("ionice")
    if ionice:
        subprocess.run(
            [ionice, "-c", "3", "-p", str(os.getpid())],
            capture_output=True,
            check=False,
        )


def load5() -> float:
    try:
        return os.getloadavg()[1]
    except (AttributeError, OSError):
        return 0.0


def parse_window(text: str) -> tuple[int, int]:
    """'01:00-11:00' -> minutes after 00:00 UTC (start, end)."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", text.strip())
    if not m:
        raise ValueError(f"window must look like 01:00-11:00, got {text!r}")
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    start, end = h1 * 60 + m1, h2 * 60 + m2
    if not (0 <= start < 1440 and 0 < end <= 1440) or start == end:
        raise ValueError(f"bad window {text!r}")
    return start, end


def parse_shard(text: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)/(\d+)", text.strip())
    if not m or not 0 <= int(m.group(1)) < int(m.group(2)):
        raise ValueError(f"shard must be K/N with 0 <= K < N, got {text!r}")
    return int(m.group(1)), int(m.group(2))


def retry_after_s(value: str | None, now: datetime) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - now).total_seconds())


def doc_url(kind: str, doc_id: int) -> str:
    return DOC_URL.format(kind=kind, folder=doc_id // 1000, doc_id=doc_id)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_int(value) -> int | None:
    try:
        return int(float(str(value).strip().replace(",", "")))
    except (TypeError, ValueError):
        return None


def norm_segment(value) -> str | None:
    n = to_int(value)
    return None if n is None else str(n)


def segment_passes(path: Path) -> dict[str, int]:
    """Segment number -> pass (1, 2 or 3) from the riser segment table."""
    out: dict[str, int] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        required = {"segment_num", "max_water_depth_ft", "static_check_tier"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("segment table missing required headers")
        for row in reader:
            seg = norm_segment(row.get("segment_num"))
            if seg is None:
                continue
            tier = (row.get("static_check_tier") or "").strip()
            try:
                depth = float(row.get("max_water_depth_ft") or "nan")
            except ValueError:
                depth = float("nan")
            if tier.startswith("B") and depth >= 1000:
                out[seg] = 1
            elif tier.startswith("B"):
                out[seg] = 2
            else:
                out[seg] = 3
    return out


def read_index(raw: bytes):
    """Rows of one scan index member as dicts (delimiter read from the header)."""
    text = raw.decode("utf-8-sig", errors="replace")
    first = text.split("\n", 1)[0]
    delim = max([",", "|", "\t"], key=first.count)
    reader = csv.DictReader(text.splitlines(), delimiter=delim)
    required = {"DOC_ID", "SEGMENT_NUMBER", "DOC_PAGES", "DOC_FILESIZE"}
    headers = {(k or "").strip().strip('"') for k in reader.fieldnames or []}
    if not required <= headers:
        raise ValueError(
            "index missing required headers: " + ", ".join(sorted(required - headers))
        )
    for row in reader:
        yield {
            (k or "").strip().strip('"'): (v or "").strip()
            for k, v in row.items()
            if not isinstance(v, list)
        }


def index_records(path: Path):
    """Validate required ZIP members and headers, then yield (kind, record)."""
    with zipfile.ZipFile(path) as zf:
        names = {n.rsplit("/", 1)[-1].lower(): n for n in zf.namelist()}
        for member in INDEX_MEMBERS.values():
            if member not in names:
                raise ValueError(f"index member missing: {member}")
        for kind, member in INDEX_MEMBERS.items():
            for rec in read_index(zf.read(names[member])):
                yield kind, rec


@dataclass
class Config:
    data_dir: Path
    shard_k: int = 0
    shard_n: int = 1
    segments: Path | None = None
    index_zip: Path | None = None
    window: tuple[int, int] = (60, 660)
    gap_s: float = 60.0
    max_pass: int = 1
    max_docs: int = 0  # 0 = no cap per run
    max_minutes: float = 0  # 0 = no time cap per run
    max_errors_day: int = 10
    max_attempts: int = 3
    backoff_first_s: float = 900.0
    backoff_max_s: float = 14400.0
    min_free_gb: float = 50.0
    max_used_pct: float = 100.0
    max_load: float = 8.0
    dpi: int = 300
    ocr: bool = True
    tool_path: str | None = None
    log_file: Path | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  kind TEXT NOT NULL, doc_id INTEGER NOT NULL, segments TEXT, pass INTEGER,
  index_pages INTEGER, index_size INTEGER, status TEXT NOT NULL DEFAULT 'queued',
  attempts INTEGER NOT NULL DEFAULT 0, size INTEGER, sha256 TEXT, pages INTEGER,
  last_error TEXT, updated_utc TEXT, PRIMARY KEY (kind, doc_id));
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


class Job:
    def __init__(
        self,
        cfg: Config,
        fetcher=http_fetch,
        runner=run_low,
        clock: Clock | None = None,
        which=shutil.which,
        loadavg=load5,
        disk_usage=shutil.disk_usage,
    ):
        self.cfg = cfg
        self.fetcher = fetcher
        self.runner = runner
        self.clock = clock or Clock()
        self.which = which
        self.loadavg = loadavg
        self.disk_usage = disk_usage
        self.dir = Path(cfg.data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "state.sqlite")
        self.db.executescript(SCHEMA)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(docs)")}
        with self.db:
            if "active" not in columns:
                self.db.execute(
                    "ALTER TABLE docs ADD COLUMN active INTEGER NOT NULL DEFAULT 1"
                )
                # Previous queue keys predate membership reconciliation.
                self.db.execute("DELETE FROM meta WHERE key='queue_key'")
            if "ocr_sha256" not in columns:
                self.db.execute("ALTER TABLE docs ADD COLUMN ocr_sha256 TEXT")
            # Both earlier schemas could retain stale membership under the old key.
            self.db.execute(
                "DELETE FROM meta WHERE key='queue_key' AND value NOT LIKE ?",
                (f"{QUEUE_KEY_VERSION}:%",),
            )
            # Completed text without a matching binding may mix PDF revisions.
            # Leave the text in place for ocr_doc to archive before regeneration.
            self.db.execute(
                "UPDATE docs SET status='fetched' WHERE status='read' AND "
                "(ocr_sha256 IS NULL OR sha256 IS NULL OR ocr_sha256 != sha256)"
            )
        self.started = self.clock.now()
        self.gap_s = cfg.gap_s
        self._robots: RobotFileParser | None = None
        self._tools: dict | None = None

    # -- small helpers -------------------------------------------------------
    def log(self, msg: str) -> None:
        line = f"{self.clock.now():%Y-%m-%dT%H:%M:%SZ} {msg}"
        print(line, flush=True)
        if self.cfg.log_file:
            with open(self.cfg.log_file, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def meta(self, key: str, default: str | None = None) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value) -> None:
        self.db.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.db.commit()

    def manifest(self, event: str, **fields) -> None:
        rec = {"utc": f"{self.clock.now():%Y-%m-%dT%H:%M:%SZ}", "event": event}
        rec.update(fields)
        with open(self.dir / "manifest.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def stop_requested(self) -> bool:
        return (self.dir / STOP_FILE).exists()

    def in_window(self) -> bool:
        now = self.clock.now()
        minute = now.hour * 60 + now.minute
        start, end = self.cfg.window
        if start < end:
            return start <= minute < end
        return minute >= start or minute < end

    def budget_spent(self) -> bool:
        if not self.cfg.max_minutes:
            return False
        spent = (self.clock.now() - self.started).total_seconds() / 60
        return spent >= self.cfg.max_minutes

    def disk_ok(self) -> bool:
        du = self.disk_usage(self.dir)
        free_gb = du.free / 1e9
        used_pct = 100.0 * (du.total - du.free) / du.total if du.total else 0.0
        if free_gb < self.cfg.min_free_gb or used_pct >= self.cfg.max_used_pct:
            self.log(
                f"disk floor: {free_gb:.1f} GB free, {used_pct:.1f} % used "
                f"(floor {self.cfg.min_free_gb} GB, stop at {self.cfg.max_used_pct} %)"
            )
            return False
        return True

    def _today_key(self) -> str:
        return f"errors:{self.clock.now():%Y-%m-%d}"

    def errors_today(self) -> int:
        return int(self.meta(self._today_key(), "0"))

    def add_error(self) -> None:
        self.set_meta(self._today_key(), self.errors_today() + 1)

    def request(self, url: str, dest: Path | None = None) -> Response | None:
        """Spaced request; None defers work without charging an error."""
        last = self.meta("last_request_utc")
        if last:
            elapsed = (self.clock.now() - datetime.fromisoformat(last)).total_seconds()
            if elapsed < self.gap_s:
                self.clock.sleep(self.gap_s - elapsed)
        if self.stop_requested() or self.budget_spent() or not self.may_fetch():
            return None
        if dest is not None and not self.disk_ok():
            return None
        self.set_meta("last_request_utc", self.clock.now().isoformat())
        response = self.fetcher(url, dest)
        if 300 <= response.status < 400:
            self.log(
                f"HTTP {response.status} redirect deferred; no destination fetched"
            )
        return response

    def robots_ok(self, url: str) -> bool | None:
        """True or False from robots.txt; None when it could not be read."""
        if self._robots is None:
            now = self.clock.now()
            cached = self.meta("robots_utc")
            text = None
            if cached and now - datetime.fromisoformat(cached) < timedelta(hours=24):
                text = self.meta("robots_txt", "")
            else:
                r = self.request(ROBOTS_URL)
                if r is None:
                    return None
                rp_status = r.status
                if 300 <= rp_status < 400:
                    return None
                if rp_status == 200:
                    text = r.body.decode("utf-8", errors="replace")
                elif rp_status in GONE:
                    text = ""
                elif rp_status in (401, 403):
                    text = "User-agent: *\nDisallow: /\n"
                else:
                    self.add_error()
                    if rp_status in REFUSALS:
                        self.refused(r)
                    self.log(f"robots.txt not read (status {rp_status} {r.error})")
                    return None
                self.set_meta("robots_txt", text)
                self.set_meta("robots_utc", now.isoformat())
            rp = RobotFileParser()
            rp.parse(text.splitlines())
            delay = rp.crawl_delay(USER_AGENT)
            if delay and float(delay) > self.gap_s:
                self.gap_s = float(delay)
            self._robots = rp
        return self._robots.can_fetch(USER_AGENT, url)

    # -- queue ---------------------------------------------------------------
    def may_fetch(self) -> bool:
        """Inside the window, under the day's error cap and past any back-off."""
        if not self.in_window():
            return False
        if self.errors_today() >= self.cfg.max_errors_day:
            self.log(f"{self.errors_today()} errors today; stopped for the day")
            return False
        until = self.meta("backoff_until")
        return not (until and self.clock.now() < datetime.fromisoformat(until))

    def prepare(self) -> int | None:
        """Prepare the current queue; None means defer the entire batch."""
        shard = f"{self.cfg.shard_k}/{self.cfg.shard_n}"
        held = self.meta("shard")
        if held and held != shard:
            self.log(f"this data directory holds shard {held}, not {shard}")
            return 2
        zip_path = Path(self.cfg.index_zip or self.dir / INDEX_ZIP_NAME)
        if not zip_path.exists():
            if self.cfg.index_zip:
                self.log(f"index file missing: {zip_path}")
                return 5
            if self.stop_requested() or not self.may_fetch():
                return None
            rc = self.fetch_index(zip_path)
            if rc:
                return rc
            if not zip_path.exists():
                return None
        if not self.cfg.segments or not Path(self.cfg.segments).exists():
            self.log(f"segment table missing: {self.cfg.segments}")
            return 5
        key = (
            f"{QUEUE_KEY_VERSION}:{sha256_of(zip_path)}:"
            f"{sha256_of(Path(self.cfg.segments))}:{shard}"
        )
        if self.meta("queue_key") == key:
            return 0
        try:
            added = self.build_queue(zip_path, Path(self.cfg.segments))
        except (ValueError, zipfile.BadZipFile) as err:
            self.log(f"queue input invalid; previous queue retained: {err}")
            return 5
        self.set_meta("queue_key", key)
        self.set_meta("shard", shard)
        self.log(f"queue built for shard {shard}: {added} documents")
        return 0

    def fetch_index(self, zip_path: Path) -> int:
        if not self.disk_ok():
            return 4
        ok = self.robots_ok(INDEX_ZIP_URL)
        if ok is None:
            return 0
        if not ok:
            self.log(f"robots.txt bars {INDEX_ZIP_URL}; stopping")
            self.set_meta("robots_blocked", INDEX_ZIP_URL)
            return 3
        part = zip_path.with_name(zip_path.name + ".part")
        r = self.request(INDEX_ZIP_URL, part)
        if r is None:
            return 0 if self.disk_ok() else 4
        if 300 <= r.status < 400:
            return 0
        if r.status == 200 and part.exists():
            try:
                for _ in index_records(part):
                    pass
            except (ValueError, zipfile.BadZipFile) as err:
                self.add_error()
                self.log(f"downloaded index invalid; not installed: {err}")
                return 5
            size = part.stat().st_size
            digest = sha256_of(part)
            os.replace(part, zip_path)
            self.manifest("index", url=INDEX_ZIP_URL, size=size, sha256=digest)
            self.log(f"scan index fetched ({size} bytes)")
        else:
            part.unlink(missing_ok=True)
            self.add_error()
            if r.status in REFUSALS:
                self.refused(r)
            self.log(f"scan index not fetched (status {r.status} {r.error})")
        return 0

    def build_queue(self, zip_path: Path, segments_path: Path) -> int:
        passes = segment_passes(segments_path)
        docs: dict[tuple[str, int], dict] = {}
        for kind, rec in index_records(zip_path):
            seg = norm_segment(rec.get("SEGMENT_NUMBER"))
            doc_id = to_int(rec.get("DOC_ID"))
            if seg not in passes or doc_id is None:
                continue
            if doc_id % self.cfg.shard_n != self.cfg.shard_k:
                continue
            d = docs.setdefault(
                (kind, doc_id),
                {
                    "segs": set(),
                    "pass": 9,
                    "pages": to_int(rec.get("DOC_PAGES")),
                    "size": to_int(rec.get("DOC_FILESIZE")),
                },
            )
            d["segs"].add(seg)
            d["pass"] = min(d["pass"], passes[seg])
        now = self.clock.now().isoformat()
        # Replace membership atomically; keep downloads, failures and OCR evidence.
        with self.db:
            self.db.execute("UPDATE docs SET active=0")
            for (kind, doc_id), d in docs.items():
                segs = ";".join(sorted(d["segs"], key=int))
                self.db.execute(
                    "INSERT INTO docs(kind, doc_id, segments, pass, index_pages,"
                    " index_size, updated_utc) VALUES(?,?,?,?,?,?,?)"
                    " ON CONFLICT(kind, doc_id) DO UPDATE SET segments=excluded.segments,"
                    " pass=excluded.pass, index_pages=excluded.index_pages,"
                    " index_size=excluded.index_size, active=1",
                    (kind, doc_id, segs, d["pass"], d["pages"], d["size"], now),
                )
        return len(docs)

    def next_doc(self, excluded=()):
        return next(
            (
                doc
                for doc in self.db.execute(
                    "SELECT kind, doc_id, index_size, index_pages, segments FROM docs"
                    " WHERE active=1 AND status='queued' AND pass<=?"
                    " ORDER BY pass, attempts, kind, doc_id",
                    (self.cfg.max_pass,),
                )
                if doc[:2] not in excluded
            ),
            None,
        )

    def set_doc(self, kind: str, doc_id: int, **fields) -> None:
        fields["updated_utc"] = self.clock.now().isoformat()
        cols = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(
            f"UPDATE docs SET {cols} WHERE kind=? AND doc_id=?",
            (*fields.values(), kind, doc_id),
        )
        self.db.commit()

    def pdf_path(self, kind: str, doc_id: int) -> Path:
        return self.dir / "pdf" / kind / f"{doc_id}.pdf"

    def text_dir(self, kind: str, doc_id: int) -> Path:
        return self.dir / "text" / kind / str(doc_id)

    # -- fetching ------------------------------------------------------------
    def refused(self, r: Response) -> None:
        now = self.clock.now()
        wait = retry_after_s(r.headers.get("retry-after"), now)
        if wait is None:
            prev = float(self.meta("backoff_s", "0"))
            wait = self.cfg.backoff_first_s if prev <= 0 else prev * 2
            wait = min(wait, self.cfg.backoff_max_s)
            self.set_meta("backoff_s", wait)
        until = now + timedelta(seconds=wait)
        self.set_meta("backoff_until", until.isoformat())
        self.log(f"refused (HTTP {r.status}); waiting until {until:%H:%M:%SZ}")

    def doc_failure(self, kind: str, doc_id: int, reason: str, final=False) -> None:
        attempts = self.db.execute(
            "SELECT attempts FROM docs WHERE kind=? AND doc_id=?", (kind, doc_id)
        ).fetchone()[0]
        attempts += 1
        self.add_error()
        if final or attempts >= self.cfg.max_attempts:
            self.set_doc(
                kind, doc_id, attempts=attempts, status="failed", last_error=reason
            )
            self.manifest(
                "failed",
                kind=kind,
                doc_id=doc_id,
                url=doc_url(kind, doc_id),
                reason=reason,
                attempts=attempts,
            )
            self.log(f"{kind} {doc_id} failed: {reason}")
        else:
            self.set_doc(kind, doc_id, attempts=attempts, last_error=reason)
            self.log(f"{kind} {doc_id} attempt {attempts} failed: {reason}")

    def fetch_doc(self, doc) -> str:
        kind, doc_id, index_size, index_pages, segments = doc
        url = doc_url(kind, doc_id)
        ok = self.robots_ok(url)
        if ok is None:
            return "robots_unknown"
        if not ok:
            self.log(f"robots.txt bars {url}; stopping")
            self.set_meta("robots_blocked", url)
            return "robots_bar"
        pdf = self.pdf_path(kind, doc_id)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        part = pdf.with_name(pdf.name + ".part")
        r = self.request(url, part)
        if r is None:
            return "deferred"
        if 300 <= r.status < 400:
            return "redirected"
        if r.status == 200:
            problem = ""
            size = part.stat().st_size if part.exists() else 0
            expected = to_int(r.headers.get("content-length"))
            if size == 0:
                problem = "empty body"
            elif expected is not None and expected != size:
                problem = f"truncated: {size} of {expected} bytes"
            else:
                with open(part, "rb") as fh:
                    if fh.read(5) != b"%PDF-":
                        problem = "not a PDF"
            if problem:
                part.unlink(missing_ok=True)
                self.doc_failure(kind, doc_id, problem)
                return "error"
            digest = sha256_of(part)
            os.replace(part, pdf)
            self.set_meta("backoff_s", 0)
            self.set_doc(
                kind, doc_id, status="fetched", size=size, sha256=digest, last_error=""
            )
            self.manifest(
                "fetched",
                kind=kind,
                doc_id=doc_id,
                url=url,
                size=size,
                sha256=digest,
                index_size=index_size,
                index_size_match=(index_size == size),
                index_pages=index_pages,
                segments=segments,
            )
            self.log(f"{kind} {doc_id} fetched ({size} bytes)")
            return "ok"
        part.unlink(missing_ok=True)
        if r.status in REFUSALS:
            self.add_error()
            self.refused(r)
            return "refused"
        reason = f"HTTP {r.status}" if r.status else f"network error: {r.error}"
        self.doc_failure(kind, doc_id, reason, final=r.status in GONE)
        return "error"

    # -- OCR -----------------------------------------------------------------
    def tools(self) -> dict | None:
        if self._tools is None:
            found = {
                name: (
                    self.which(name, path=self.cfg.tool_path)
                    if self.cfg.tool_path
                    else self.which(name)
                )
                for name in ("pdftoppm", "pdfinfo", "tesseract")
            }
            if not (found["pdftoppm"] and found["tesseract"]):
                missing = [k for k in ("pdftoppm", "tesseract") if not found[k]]
                self.log(f"OCR tools missing ({', '.join(missing)}); fetch only")
                found = {}
            self._tools = found
        return self._tools or None

    def wait_load(self) -> bool:
        warned = False
        while self.loadavg() > self.cfg.max_load:
            if self.stop_requested() or self.budget_spent():
                return False
            if not warned:
                self.log(f"load over {self.cfg.max_load}; OCR paused")
                warned = True
            self.clock.sleep(60)
        return True

    def page_count(self, pdf: Path, fallback: int | None) -> int | None:
        tools = self.tools() or {}
        if tools.get("pdfinfo"):
            rc, out = self.runner([tools["pdfinfo"], str(pdf)])
            m = re.search(r"^Pages:\s+(\d+)", out or "", re.M)
            if rc == 0 and m:
                return int(m.group(1))
        return fallback

    def ocr_doc(self, kind: str, doc_id: int) -> bool:
        """OCR one fetched document page by page; True when every page is read."""
        tools = self.tools()
        if not tools:
            return False
        pdf = self.pdf_path(kind, doc_id)
        fallback, expected, bound = self.db.execute(
            "SELECT index_pages, sha256, ocr_sha256 FROM docs WHERE kind=? AND doc_id=?",
            (kind, doc_id),
        ).fetchone()
        try:
            digest = sha256_of(pdf)
        except OSError:
            return self._ocr_failed(kind, doc_id, "saved PDF unavailable")
        if expected and digest != expected:
            return self._ocr_failed(kind, doc_id, "saved PDF digest mismatch")
        tdir = self.text_dir(kind, doc_id)
        if bound != digest and tdir.exists():
            # Preserve unbound or differently bound evidence without reusing it.
            version = 1
            archive = tdir.with_name(f"{doc_id}-unverified-{version}")
            while archive.exists():
                version += 1
                archive = tdir.with_name(f"{doc_id}-unverified-{version}")
            tdir.rename(archive)
            self.manifest("ocr_archived", kind=kind, doc_id=doc_id, sha256=bound)
        self.set_doc(kind, doc_id, sha256=digest, ocr_sha256=digest)
        pages = self.page_count(pdf, fallback)
        if not pages:
            self.set_doc(kind, doc_id, status="ocr_failed", last_error="page count")
            return False
        tdir.mkdir(parents=True, exist_ok=True)
        for page in range(1, pages + 1):
            out = tdir / f"page-{page:04d}.txt"
            if out.exists():
                continue
            if self.stop_requested() or self.budget_spent() or not self.wait_load():
                return False
            if self.stop_requested() or self.budget_spent() or not self.disk_ok():
                return False
            stem = tdir / f".page-{page:04d}"
            png = tdir / f".page-{page:04d}.png"
            rc, _ = self.runner(
                [
                    tools["pdftoppm"],
                    "-r",
                    str(self.cfg.dpi),
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-gray",
                    "-png",
                    "-singlefile",
                    str(pdf),
                    str(stem),
                ]
            )
            if rc != 0 or not png.exists():
                return self._ocr_failed(kind, doc_id, f"pdftoppm page {page}")
            base = tdir / f".page-{page:04d}-ocr"
            txt = tdir / f".page-{page:04d}-ocr.txt"
            rc, _ = self.runner([tools["tesseract"], str(png), str(base)])
            png.unlink(missing_ok=True)
            if rc != 0 or not txt.exists():
                return self._ocr_failed(kind, doc_id, f"tesseract page {page}")
            os.replace(txt, out)
        self.set_doc(kind, doc_id, status="read", pages=pages, last_error="")
        self.manifest("read", kind=kind, doc_id=doc_id, pages=pages, sha256=digest)
        self.log(f"{kind} {doc_id} read ({pages} pages)")
        return True

    def _ocr_failed(self, kind: str, doc_id: int, reason: str) -> bool:
        self.set_doc(kind, doc_id, status="ocr_failed", last_error=reason)
        self.manifest("ocr_failed", kind=kind, doc_id=doc_id, reason=reason)
        self.log(f"{kind} {doc_id} OCR failed: {reason}")
        return False

    def ocr_backlog(self) -> None:
        if not self.cfg.ocr:
            return
        for kind, doc_id in self.db.execute(
            "SELECT kind, doc_id FROM docs WHERE active=1 AND status='fetched'"
            " ORDER BY pass, kind, doc_id"
        ).fetchall():
            if self.stop_requested() or self.budget_spent() or not self.tools():
                return
            self.ocr_doc(kind, doc_id)

    # -- main loop -----------------------------------------------------------
    def run(self) -> int:
        if self.stop_requested():
            self.log("STOP file present; nothing done")
            return 0
        rc = self.prepare()
        if rc is None:
            return 0
        if rc:
            return rc
        self.ocr_backlog()
        if not self.disk_ok():
            return 4
        done = 0
        excluded: set[tuple[str, int]] = set()  # each document once per run
        while not self.stop_requested():
            if not self.may_fetch() or self.budget_spent():
                break
            if not self.disk_ok():
                return 4
            doc = self.next_doc(excluded)
            if doc is None:
                break
            result = self.fetch_doc(doc)
            if result == "robots_bar":
                return 3
            if result == "deferred" and not self.disk_ok():
                return 4
            if result in ("robots_unknown", "refused", "deferred"):
                break
            if result in ("error", "redirected"):
                excluded.add((doc[0], doc[1]))
            if result == "redirected":
                continue
            if result == "ok" and self.cfg.ocr:
                self.ocr_doc(doc[0], doc[1])
            if not self.disk_ok():
                return 4
            done += 1
            if self.cfg.max_docs and done >= self.cfg.max_docs:
                break
        return 0

    def status(self) -> dict:
        rows = self.db.execute(
            "SELECT active, pass, status, COUNT(*), COALESCE(SUM(pages), 0),"
            " COALESCE(SUM(size), 0) FROM docs GROUP BY active, pass, status"
        ).fetchall()
        return {
            "shard": self.meta("shard"),
            "errors_today": self.errors_today(),
            "backoff_until": self.meta("backoff_until"),
            "robots_blocked": self.meta("robots_blocked"),
            "by_pass_status": [
                {"pass": p, "status": s, "docs": n, "pages": pg, "bytes": b}
                for active, p, s, n, pg, b in rows
                if active
            ],
            "archived_by_pass_status": [
                {"pass": p, "status": s, "docs": n, "pages": pg, "bytes": b}
                for active, p, s, n, pg, b in rows
                if not active
            ],
        }

    def requeue_failed(self) -> int:
        cur = self.db.execute(
            "UPDATE docs SET status=CASE WHEN status='ocr_failed' THEN 'fetched'"
            " ELSE 'queued' END, attempts=0"
            " WHERE status IN ('failed', 'ocr_failed')"
        )
        self.db.commit()
        return cur.rowcount


# -- findings -------------------------------------------------------------------
_NUM = r"(?<![\w./+-])(\d+(?:\s*-\s*|\s+)\d+/\d+|\d+/\d+|\d*\.\d+|\d+)(?![\d.,/])"
_UNIT = r"(?:\s*-?\s*(?P<unit>mm\b|millimet(?:er|re)s?\b|\"|''|in(?:ch(?:es)?)?\b\.?))?"
_WALL = r"(?:w\.\s?t\.?|\bwt\b|wall\s+thickness|wall\b)"
FINDING_PATTERNS = {
    "wall_thickness": [
        re.compile(_NUM + _UNIT + r"\s*-?\s*" + _WALL, re.I),
        re.compile(_WALL + r"\s*(?:of|=|:|is)?\s*" + _NUM + _UNIT, re.I),
    ],
    "grade": [re.compile(r"\b(?:grade\s*)?(X\s?-?(?:52|56|60|65|70))\b", re.I)],
    "riser_length_ft": [
        re.compile(
            r"riser[^.\n]{0,40}?\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{2,5}(?:\.\d+)?)"
            r"\s*(?:ft\b|feet|')",
            re.I,
        )
    ],
    "hang_off_angle_deg": [
        re.compile(
            r"(?:hang[\s-]*off|departure|top)\s+angle[^\d.+\-−\n]{0,20}?"
            r"([+\-−]?\d+(?:\.\d+)?)\s*(?:°|deg(?:rees?)?\b)",
            re.I,
        )
    ],
}


def find_values(text: str):
    """(quantity, value, line) for each match, line cut to 200 characters."""
    for line in text.splitlines():
        for quantity, patterns in FINDING_PATTERNS.items():
            for rx in patterns:
                for m in rx.finditer(line):
                    value = re.sub(r"\s+", " ", m.group(1)).strip().upper()
                    if quantity == "wall_thickness":
                        value = re.sub(r"\s*-\s*", "-", value)
                    if quantity == "grade":
                        value = value.replace(" ", "")
                    matched_quantity = quantity
                    if quantity == "wall_thickness":
                        unit = (m.group("unit") or "").lower()
                        suffix = (
                            "mm"
                            if unit.startswith(("mm", "milli"))
                            else ("in" if unit else "unknown_unit")
                        )
                        matched_quantity = f"wall_thickness_{suffix}"
                    if quantity == "grade":
                        value = value.replace("-", "")
                    if quantity == "hang_off_angle_deg":
                        value = value.replace("−", "-")
                    yield matched_quantity, value, line.strip()[:200]


def write_findings(job: Job, out: Path) -> int:
    """Raw OCR matches. Remove company and facility names before publishing."""
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["segments", "kind", "doc_id", "page", "quantity", "value", "line"])
        for kind, doc_id, segments in job.db.execute(
            "SELECT kind, doc_id, segments FROM docs WHERE active=1 AND status='read'"
            " AND sha256 IS NOT NULL AND ocr_sha256=sha256"
            " ORDER BY kind, doc_id"
        ):
            for page_file in sorted(job.text_dir(kind, doc_id).glob("page-*.txt")):
                page = int(page_file.stem.split("-")[1])
                text = page_file.read_text(encoding="utf-8", errors="replace")
                for quantity, value, line in find_values(text):
                    w.writerow([segments, kind, doc_id, page, quantity, value, line])
                    n += 1
    return n


# -- command line ----------------------------------------------------------------
@contextmanager
def single_run(path: Path):
    """Yield True when this process holds the run lock, else False."""
    fh = open(path, "a+")
    held = False
    try:
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = True
        except OSError:
            held = False
        yield held
    finally:
        fh.close()


def build_parser() -> argparse.ArgumentParser:
    # "@file" reads one argument per line, which keeps a scheduled task's
    # command short.
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0], fromfile_prefix_chars="@"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="one batch: fetch and OCR, then exit")
    run.add_argument("--data-dir", type=Path, required=True)
    run.add_argument("--shard", default="0/1", help="K/N: DOC_ID modulo N equals K")
    run.add_argument("--segments", type=Path, help="riser_segments.csv")
    run.add_argument("--index-zip", type=Path, help="local ScannedDocsRawData.zip")
    run.add_argument("--window", default="01:00-11:00", help="fetch window, UTC")
    run.add_argument("--gap", type=float, default=60.0, help="seconds, at least 60")
    run.add_argument("--max-pass", type=int, default=1, choices=(1, 2, 3))
    run.add_argument("--max-docs", type=int, default=0)
    run.add_argument("--max-minutes", type=float, default=0)
    run.add_argument("--max-errors-day", type=int, default=10)
    run.add_argument("--min-free-gb", type=float, default=50.0)
    run.add_argument("--max-used-pct", type=float, default=100.0)
    run.add_argument("--max-load", type=float, default=8.0)
    run.add_argument("--dpi", type=int, default=300)
    run.add_argument("--no-ocr", action="store_true")
    run.add_argument("--tool-path", help="search path for pdftoppm and tesseract")
    run.add_argument("--log", type=Path, help="also append log lines here")
    run.add_argument("--requeue-failed", action="store_true")
    st = sub.add_parser("status", help="counts by pass and status, as JSON")
    st.add_argument("--data-dir", type=Path, required=True)
    fi = sub.add_parser("findings", help="matched values from the OCR text, as CSV")
    fi.add_argument("--data-dir", type=Path, required=True)
    fi.add_argument("--out", type=Path, required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd != "run":
        job = Job(Config(data_dir=args.data_dir))
        if args.cmd == "status":
            print(json.dumps(job.status(), indent=2))
        else:
            print(f"{write_findings(job, args.out)} matches written to {args.out}")
        return 0
    try:
        k, n = parse_shard(args.shard)
        window = parse_window(args.window)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 2
    if not math.isfinite(args.gap) or args.gap < 60:
        print("--gap must be finite and at least 60 seconds", file=sys.stderr)
        return 2
    cfg = Config(
        data_dir=args.data_dir,
        shard_k=k,
        shard_n=n,
        segments=args.segments,
        index_zip=args.index_zip,
        window=window,
        gap_s=args.gap,
        max_pass=args.max_pass,
        max_docs=args.max_docs,
        max_minutes=args.max_minutes,
        max_errors_day=args.max_errors_day,
        min_free_gb=args.min_free_gb,
        max_used_pct=args.max_used_pct,
        max_load=args.max_load,
        dpi=args.dpi,
        ocr=not args.no_ocr,
        tool_path=args.tool_path,
        log_file=args.log,
    )
    args.data_dir.mkdir(parents=True, exist_ok=True)
    lower_own_priority()
    with single_run(args.data_dir / ".run.lock") as held:
        if not held:
            print("another run holds the lock; nothing done")
            return 0
        job = Job(cfg)
        if args.requeue_failed:
            job.log(f"{job.requeue_failed()} failed documents queued again")
        return job.run()


if __name__ == "__main__":
    sys.exit(main())
