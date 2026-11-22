"""scripts/bsee/row_scan_ocr.py with a fake fetcher, clock and OCR runner.

No network and no OCR tools are used.
"""

import importlib.util
import io
import json
import sys
import zipfile
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from urllib.response import addinfourl

import pytest

_PATH = Path(__file__).resolve().parents[3] / "scripts" / "bsee" / "row_scan_ocr.py"
_spec = importlib.util.spec_from_file_location("row_scan_ocr", _PATH)
rso = importlib.util.module_from_spec(_spec)
sys.modules["row_scan_ocr"] = rso  # dataclasses look the module up
_spec.loader.exec_module(rso)

PDF = b"%PDF-1.4\n fake scan body\n"
Usage = namedtuple("Usage", "total used free")
NIGHT = datetime(2026, 11, 22, 2, 0, tzinfo=timezone.utc)
DAY = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)

SEGMENTS = """segment_num,max_water_depth_ft,static_check_tier
100,4000,B_needs_assumed_wt
200,300,B_needs_assumed_wt
300,5000,A_ready_od_wt_depth
"""
# ROW index (comma) and pipeline map index (pipe) with documents for segments
# 100 (pass 1), 200 (pass 2), 300 (pass 3) and 999 (not a riser segment).
ROW_TXT = (
    "DOC_ID,REGION,DOC_IMPORTED_DATE,DOC_PAGES,DOC_FILESIZE,ROW_NUMBER,"
    "SEGMENT_NUMBER,DOC_TYPE,DOC_NOTES,DOC_DATE\n"
    '32733,G,2001-01-01,2,25,G1,100,ROW,"note, with comma",2001-01-01\n'
    "32734,G,2001-01-01,1,25,G2,200,ROW,,2001-01-01\n"
    "32735,G,2001-01-01,3,25,G3,300,ROW,,2001-01-01\n"
    "32736,G,2001-01-01,3,25,G4,999,ROW,,2001-01-01\n"
    "32737,G,2001-01-01,2,25,G5,100,ROW,,2001-01-01\n"
    "32737,G,2001-01-01,2,25,G5,300,ROW,,2001-01-01\n"
)
MAPS_TXT = (
    "DOC_ID|REGION|DOC_IMPORTED_DATE|DOC_PAGES|DOC_FILESIZE|SEGMENT_NUMBER|"
    "ORIG_AREA_CODE|ORIG_BLOCK_NUMBER|ORIG_LEASE_NUMBER|DEST_AREA_CODE|"
    "DEST_BLOCK_NUMBER|DEST_LEASE_NUMBER|PPL_SIZE_CODE|DOC_TYPE|DOC_DATE\n"
    "19963|G|2001|1|25|100|SS|1|L1|SS|2|L2|08|MAP|2001\n"
    "19964|G|2001|1|25|300|SS|1|L1|SS|2|L2|08|MAP|2001\n"
)


def make_zip(path: Path) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ScannedDocsRawData/scan_row.txt", ROW_TXT)
        zf.writestr("ScannedDocsRawData/scan_pipeline_maps.txt", MAPS_TXT)
        zf.writestr("ScannedDocsRawData/scan_plans.txt", "DOC_ID\n1\n")
    path.write_bytes(buf.getvalue())
    return path


class FakeClock:
    def __init__(self, start):
        self.t = start
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += timedelta(seconds=seconds)


class FakeFetcher:
    """Serves robots.txt, the index zip and PDFs; records (time, url)."""

    def __init__(self, clock, robots=b"User-agent: Wget\nDisallow: /\n", zip_bytes=b""):
        self.clock = clock
        self.calls = []
        self.robots = robots
        self.zip_bytes = zip_bytes
        self.script = {}  # url -> list of Response to return first

    def __call__(self, url, dest=None):
        self.calls.append((self.clock.now(), url))
        queued = self.script.get(url)
        if queued:
            r = queued.pop(0)
            if r.status == 200 and dest is not None:
                dest.write_bytes(r.body)
                return rso.Response(200, r.headers)
            return r
        if url == rso.ROBOTS_URL:
            return rso.Response(200, {}, self.robots)
        if url == rso.INDEX_ZIP_URL:
            dest.write_bytes(self.zip_bytes)
            return rso.Response(200, {})
        dest.write_bytes(PDF)
        return rso.Response(200, {"content-length": str(len(PDF))})

    def doc_urls(self):
        return [u for _, u in self.calls if u.endswith(".pdf")]


def fake_runner(calls):
    """pdftoppm writes <stem>.png, tesseract writes <base>.txt, pdfinfo says 2."""

    def run(cmd):
        calls.append(cmd)
        tool = Path(cmd[0]).name
        if tool == "pdfinfo":
            return 0, "Title: x\nPages:          2\n"
        if tool == "pdftoppm":
            Path(cmd[-1] + ".png").write_bytes(b"png")
            return 0, ""
        if tool == "tesseract":
            page = Path(cmd[1]).stem
            Path(cmd[2] + ".txt").write_text(f'{page}: 12.750 x 0.500" W.T. X-65\n')
            return 0, ""
        return 1, ""

    return run


def no_tools(name, path=None):
    return None


def all_tools(name, path=None):
    return f"/usr/bin/{name}"


@pytest.fixture
def env(tmp_path):
    seg = tmp_path / "riser_segments.csv"
    seg.write_text(SEGMENTS)
    zp = make_zip(tmp_path / "index.zip")
    return tmp_path, seg, zp


def make_job(tmp_path, seg, zp, clock, fetcher, k=0, n=1, which=no_tools, **cfg):
    runner_calls = []
    config = rso.Config(
        data_dir=tmp_path / f"data-{k}-{n}",
        shard_k=k,
        shard_n=n,
        segments=seg,
        index_zip=zp,
        **cfg,
    )
    job = rso.Job(
        config,
        fetcher=fetcher,
        runner=fake_runner(runner_calls),
        clock=clock,
        which=which,
        loadavg=lambda: 0.5,
        disk_usage=lambda p: Usage(1000e9, 500e9, 500e9),
    )
    job.runner_calls = runner_calls
    return job


def test_segment_passes(env):
    _, seg, _ = env
    assert rso.segment_passes(seg) == {"100": 1, "200": 2, "300": 3}


def test_doc_url_folder():
    assert rso.doc_url("ROW", 32733).endswith("/PDFDocs/Scan/ROW/32/32733.pdf")
    assert rso.doc_url("PIPEMAPS", 19963).endswith("/PIPEMAPS/19/19963.pdf")


@pytest.mark.parametrize("bad", ["3/3", "1", "a/b", "-1/2"])
def test_bad_shard(bad):
    with pytest.raises(ValueError):
        rso.parse_shard(bad)


def test_window_parse_and_wrap():
    assert rso.parse_window("01:00-11:00") == (60, 660)
    assert rso.parse_window("22:00-02:00") == (1320, 120)
    with pytest.raises(ValueError):
        rso.parse_window("1-11")


def test_shards_disjoint_and_complete(env):
    tmp_path, seg, zp = env
    keys = []
    for k in range(3):
        clock = FakeClock(DAY)
        job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock), k=k, n=3)
        assert job.prepare() == 0
        rows = job.db.execute("SELECT kind, doc_id FROM docs").fetchall()
        assert all(doc_id % 3 == k for _, doc_id in rows)
        keys.extend(rows)
    assert len(keys) == len(set(keys))
    assert sorted(keys) == sorted(
        [("ROW", 32733), ("ROW", 32734), ("ROW", 32735), ("ROW", 32737)]
        + [("PIPEMAPS", 19963), ("PIPEMAPS", 19964)]
    )


def test_doc_on_two_segments_takes_lower_pass(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    job.prepare()
    row = job.db.execute(
        "SELECT segments, pass FROM docs WHERE doc_id=32737"
    ).fetchone()
    assert row == ("100;300", 1)


def test_outside_window_fetches_nothing(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.run() == 0
    assert fetcher.calls == []


def test_robots_first_pass_order_and_gap(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_pass=3)
    assert job.run() == 0
    urls = [u for _, u in fetcher.calls]
    assert urls[0] == rso.ROBOTS_URL
    # pass 1 first (PIPEMAPS sorts before ROW inside a pass), then 2, then 3
    ids = [int(u.rsplit("/", 1)[1][:-4]) for u in urls[1:]]
    assert ids == [19963, 32733, 32737, 32734, 19964, 32735]
    times = [t for t, _ in fetcher.calls]
    assert all((b - a).total_seconds() >= 60 for a, b in zip(times, times[1:]))
    st = {(r["pass"], r["status"]): r["docs"] for r in job.status()["by_pass_status"]}
    assert st == {(1, "fetched"): 3, (2, "fetched"): 1, (3, "fetched"): 2}
    lines = (job.dir / "manifest.jsonl").read_text().splitlines()
    assert [json.loads(x)["event"] for x in lines] == ["fetched"] * 6


def test_max_pass_one_by_default(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    job.run()
    assert len(fetcher.doc_urls()) == 3


def test_gap_kept_across_runs(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1).run()
    clock.t += timedelta(seconds=5)
    make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1).run()
    times = [t for t, u in fetcher.calls if u.endswith(".pdf")]
    assert (times[1] - times[0]).total_seconds() >= 60


def test_robots_bar_stops(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, robots=b"User-agent: *\nDisallow: /PDFDocs/\n")
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.run() == 3
    assert fetcher.doc_urls() == []
    assert job.meta("robots_blocked")


def test_robots_crawl_delay_raises_gap(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, robots=b"User-agent: *\nCrawl-delay: 120\n")
    make_job(tmp_path, seg, zp, clock, fetcher).run()
    times = [t for t, u in fetcher.calls if u.endswith(".pdf")]
    assert all((b - a).total_seconds() >= 120 for a, b in zip(times, times[1:]))


def test_resume_skips_done_work(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    make_job(tmp_path, seg, zp, clock, fetcher, max_docs=2).run()
    first = fetcher.doc_urls()
    make_job(tmp_path, seg, zp, clock, fetcher).run()
    later = fetcher.doc_urls()[len(first) :]
    assert len(first) == 2 and len(later) == 1
    assert not set(first) & set(later)


def test_stop_file(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    (job.dir / "STOP").write_text("")
    assert job.run() == 0
    assert fetcher.calls == []


def test_retry_after_honoured(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(429, {"retry-after": "1200"})]
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.run() == 0
    assert fetcher.doc_urls() == [url]
    until = datetime.fromisoformat(job.meta("backoff_until"))
    assert (until - clock.now()).total_seconds() == pytest.approx(1200)
    clock.t += timedelta(seconds=600)
    make_job(tmp_path, seg, zp, clock, fetcher).run()
    assert fetcher.doc_urls() == [url]  # still waiting
    clock.t += timedelta(seconds=700)
    make_job(tmp_path, seg, zp, clock, fetcher).run()
    assert fetcher.doc_urls()[1] == url  # same document again, not failed


def test_backoff_doubles_without_retry_after(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(503) for _ in range(6)]
    waits = []
    for _ in range(6):
        job = make_job(tmp_path, seg, zp, clock, fetcher, max_errors_day=99)
        job.run()
        until = datetime.fromisoformat(job.meta("backoff_until"))
        waits.append((until - clock.now()).total_seconds())
        clock.t = until
    assert waits == [900, 1800, 3600, 7200, 14400, 14400]


def test_not_found_fails_at_once_and_errors_retry(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    gone = rso.doc_url("PIPEMAPS", 19963)
    flaky = rso.doc_url("ROW", 32733)
    fetcher.script[gone] = [rso.Response(404)]
    fetcher.script[flaky] = [rso.Response(500), rso.Response(0, error="reset")]
    fetcher.script[flaky] += [rso.Response(500)]
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    job.run()
    rows = dict(
        job.db.execute("SELECT doc_id, status FROM docs WHERE pass=1").fetchall()
    )
    assert rows[19963] == "failed"
    assert rows[32733] == "queued"  # one failure so far
    for _ in range(2):
        make_job(tmp_path, seg, zp, clock, fetcher).run()
    rows = dict(job.db.execute("SELECT doc_id, status FROM docs").fetchall())
    assert rows[32733] == "failed"
    assert fetcher.doc_urls().count(gone) == 1
    assert fetcher.doc_urls().count(flaky) == 3


def test_truncated_body_not_kept(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(200, {"content-length": "999"}, PDF)]
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1)
    job.run()
    assert not job.pdf_path("PIPEMAPS", 19963).exists()
    assert not list(job.dir.rglob("*.part"))
    row = job.db.execute(
        "SELECT status, attempts, last_error FROM docs WHERE doc_id=19963"
    ).fetchone()
    assert row[0] == "queued" and row[1] == 1 and "truncated" in row[2]


def test_ten_errors_end_the_day(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_errors_day=2)
    for kind, doc_id in [("PIPEMAPS", 19963), ("ROW", 32733)]:
        fetcher.script[rso.doc_url(kind, doc_id)] = [rso.Response(500)]
    job.run()
    assert len(fetcher.doc_urls()) == 2
    make_job(tmp_path, seg, zp, clock, fetcher, max_errors_day=2).run()
    assert len(fetcher.doc_urls()) == 2


def test_disk_floor_stops(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_used_pct=40)
    assert job.run() == 4
    assert fetcher.calls == []


def test_index_fetched_inside_window_when_missing(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(tmp_path, seg, None, clock, fetcher, max_docs=1)
    assert job.run() == 0
    urls = [u for _, u in fetcher.calls]
    assert urls[:2] == [rso.ROBOTS_URL, rso.INDEX_ZIP_URL]
    assert (job.dir / rso.INDEX_ZIP_NAME).exists()
    assert len(fetcher.doc_urls()) == 1


def test_wrong_shard_in_data_dir_refused(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    make_job(tmp_path, seg, zp, clock, FakeFetcher(clock)).prepare()
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    job.cfg.shard_n = 2
    assert job.run() == 2


def test_ocr_writes_pages_and_removes_images(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    job.run()
    tdir = job.text_dir("PIPEMAPS", 19963)
    assert sorted(p.name for p in tdir.iterdir()) == ["page-0001.txt", "page-0002.txt"]
    row = job.db.execute("SELECT status, pages FROM docs WHERE doc_id=19963").fetchone()
    assert row == ("read", 2)
    events = [
        json.loads(x)["event"]
        for x in (job.dir / "manifest.jsonl").read_text().splitlines()
    ]
    assert events == ["fetched", "read"]
    tools = [Path(c[0]).name for c in job.runner_calls]
    assert tools == ["pdfinfo", "pdftoppm", "tesseract", "pdftoppm", "tesseract"]
    assert "300" in job.runner_calls[1]


def test_ocr_resumes_at_missing_page(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools)
    job.prepare()
    pdf = job.pdf_path("PIPEMAPS", 19963)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(PDF)
    digest = rso.sha256_of(pdf)
    job.set_doc("PIPEMAPS", 19963, status="fetched", sha256=digest, ocr_sha256=digest)
    tdir = job.text_dir("PIPEMAPS", 19963)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text("done before")
    job.run()  # outside the window: OCR backlog only
    assert fetcher.calls == []
    assert (tdir / "page-0001.txt").read_text() == "done before"
    assert (tdir / "page-0002.txt").exists()
    assert [Path(c[0]).name for c in job.runner_calls].count("tesseract") == 1


def test_ocr_waits_while_load_high(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    loads = iter([9.0, 9.0, 1.0])
    job.loadavg = lambda: next(loads, 1.0)
    job.run()
    assert clock.slept == [60, 60, 60]  # one request gap, two load pauses


def test_findings(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    job.run()
    out = tmp_path / "findings.csv"
    assert rso.write_findings(job, out) == 4
    text = out.read_text()
    assert "wall_thickness_in,0.500" in text and "grade,X65" in text


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            '16" O.D. x 0.750" W.T. API 5L X-65',
            {("wall_thickness_in", "0.750"), ("grade", "X65")},
        ),
        ("wall thickness of 0.875 in", {("wall_thickness_in", "0.875")}),
        ("steel catenary riser 6,200 ft long", {("riser_length_ft", "6,200")}),
        ("hang-off angle of 12.5 deg", {("hang_off_angle_deg", "12.5")}),
        ("no values here", set()),
    ],
)
def test_find_values(line, expected):
    assert {(q, v) for q, v, _ in rso.find_values(line)} == expected


def test_retry_after_date():
    now = datetime(2026, 11, 22, 2, 0, tzinfo=timezone.utc)
    assert rso.retry_after_s("Sun, 22 Nov 2026 02:10:00 GMT", now) == 600
    assert rso.retry_after_s("30", now) == 30
    assert rso.retry_after_s("soon", now) is None


def test_index_fetch_refusal_respects_backoff(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    fetcher.script[rso.INDEX_ZIP_URL] = [rso.Response(429)]
    make_job(tmp_path, seg, None, clock, fetcher).run()
    clock.t += timedelta(minutes=10)
    make_job(tmp_path, seg, None, clock, fetcher).run()
    assert [u for _, u in fetcher.calls].count(rso.INDEX_ZIP_URL) == 1
    clock.t += timedelta(minutes=10)
    make_job(tmp_path, seg, None, clock, fetcher, max_docs=1).run()
    assert [u for _, u in fetcher.calls].count(rso.INDEX_ZIP_URL) == 2
    assert len(fetcher.doc_urls()) == 1


def test_single_run_lock(tmp_path):
    lock = tmp_path / ".run.lock"
    with rso.single_run(lock) as first:
        with rso.single_run(lock) as second:
            assert first is True and second is False
    with rso.single_run(lock) as again:
        assert again is True


def test_args_file(tmp_path):
    args = tmp_path / "job.args"
    args.write_text(f"run\n--data-dir\n{tmp_path / 'd'}\n--shard\n2/3\n--gap\n180\n")
    ns = rso.build_parser().parse_args([f"@{args}"])
    assert (ns.cmd, ns.shard, ns.gap) == ("run", "2/3", 180.0)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("wall thickness of 9.50 mm", {("wall_thickness_mm", "9.50")}),
        ("departure angle 120 deg", {("hang_off_angle_deg", "120")}),
        ("wall thickness of 12.500 inches", {("wall_thickness_in", "12.500")}),
        ("9.50 mm wall thickness", {("wall_thickness_mm", "9.50")}),
        ("wall thickness of 0.500", {("wall_thickness_unknown_unit", "0.500")}),
        ("departure angle 120.25 deg", {("hang_off_angle_deg", "120.25")}),
    ],
)
def test_find_values_full_number_and_unit(line, expected):
    assert {(q, v) for q, v, _ in rso.find_values(line)} == expected


@pytest.mark.parametrize("target", ["index", "document", "robots"])
@pytest.mark.parametrize("reason", ["window", "stop", "budget"])
def test_fetch_defers_after_gap(env, target, reason):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT.replace(hour=10, minute=59, second=30))
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(
        tmp_path,
        seg,
        None if target == "index" else zp,
        clock,
        fetcher,
        max_minutes=0.5 if reason == "budget" else 0,
    )
    if target == "document":
        job.prepare()
    if target != "robots":
        job.set_meta("robots_utc", clock.now().isoformat())
        job.set_meta("robots_txt", "User-agent: *\nAllow: /\n")
    if reason != "window":
        job.cfg.window = (0, 1440)
    job.set_meta("last_request_utc", clock.now().isoformat())
    sleep = clock.sleep

    def during_gap(seconds):
        sleep(seconds)
        if reason == "stop":
            (job.dir / "STOP").touch()

    clock.sleep = during_gap
    assert job.run() == 0
    assert fetcher.calls == []
    assert job.errors_today() == 0
    if target == "document":
        assert job.db.execute("SELECT SUM(attempts) FROM docs").fetchone()[0] == 0
    assert (
        job.meta("last_request_utc")
        == NIGHT.replace(hour=10, minute=59, second=30).isoformat()
    )


@pytest.mark.parametrize("status", [429, 503])
def test_robots_refusal_persists_retry_after(env, status):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    fetcher.script[rso.ROBOTS_URL] = [rso.Response(status, {"retry-after": "7200"})]
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.run() == 0
    assert job.meta("backoff_until") == (NIGHT + timedelta(hours=2)).isoformat()
    assert job.errors_today() == 1
    clock.t += timedelta(hours=1)
    assert make_job(tmp_path, seg, zp, clock, fetcher).run() == 0
    assert len(fetcher.calls) == 1
    clock.t += timedelta(hours=1)
    assert make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1).run() == 0
    assert len(fetcher.doc_urls()) == 1


def fetched_backlog(env, **cfg):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock), which=all_tools, **cfg)
    job.prepare()
    pdf = job.pdf_path("PIPEMAPS", 19963)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(PDF)
    job.set_doc("PIPEMAPS", 19963, status="fetched")
    job.db.execute("UPDATE docs SET status='failed' WHERE doc_id != 19963")
    job.db.commit()
    assert job.next_doc() is None
    return job, clock


@pytest.mark.parametrize("stage", ["page_count", "first_page", "load_wait"])
def test_ocr_deadline_leaves_pages_resumable(env, stage):
    job, clock = fetched_backlog(env, max_minutes=1)
    runner = job.runner

    def timed_runner(cmd):
        result = runner(cmd)
        if (stage == "page_count" and Path(cmd[0]).name == "pdfinfo") or (
            stage == "first_page" and Path(cmd[0]).name == "tesseract"
        ):
            clock.t += timedelta(seconds=60)
        return result

    job.runner = timed_runner
    if stage == "load_wait":
        loads = iter([9, 0])
        job.loadavg = lambda: next(loads, 0)
    assert job.run() == 0
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "fetched",
    )
    renders = [c for c in job.runner_calls if Path(c[0]).name == "pdftoppm"]
    assert len(renders) == (1 if stage == "first_page" else 0)
    job.cfg.max_minutes = 0
    assert job.run() == 0
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "read",
    )
    assert len([c for c in job.runner_calls if Path(c[0]).name == "pdftoppm"]) == 2


def test_disk_floor_before_missing_index(env):
    tmp_path, seg, zp = env
    seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(tmp_path, seg, None, clock, fetcher)
    job.disk_usage = lambda p: Usage(100e9, 99e9, 1e9)
    assert job.run() == 4
    assert fetcher.calls == []
    assert job.next_doc() is None


@pytest.mark.parametrize("full_after_first", [False, True])
def test_disk_floor_before_each_backlog_page(env, full_after_first):
    job, _ = fetched_backlog(env)
    job.disk_usage = lambda p: (
        Usage(100e9, 99e9, 1e9)
        if (
            not full_after_first
            or any(Path(c[0]).name == "tesseract" for c in job.runner_calls)
        )
        else Usage(1000e9, 500e9, 500e9)
    )
    assert job.run() == 4
    assert len([c for c in job.runner_calls if Path(c[0]).name == "pdftoppm"]) == int(
        full_after_first
    )
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "fetched",
    )
    assert job.errors_today() == 0


def test_rebuild_deactivates_stale_queue_preserving_evidence(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    job.prepare()
    job.set_doc("ROW", 32733, status="fetched", size=25, sha256="evidence", attempts=1)
    before = job.db.execute(
        "SELECT status, size, sha256, attempts FROM docs WHERE doc_id=32733"
    ).fetchone()
    seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
    assert job.prepare() == 0
    assert job.next_doc() is None
    assert job.run() == 0
    assert job.fetcher.calls == []
    after = job.db.execute(
        "SELECT status, size, sha256, attempts FROM docs WHERE doc_id=32733"
    ).fetchone()
    assert after == before
    seg.write_text(SEGMENTS)
    job.prepare()
    assert job.db.execute(
        "SELECT status, size, sha256, attempts FROM docs WHERE doc_id=32733"
    ).fetchone() == ("fetched", 25, "evidence", 1)
    assert job.next_doc() is not None


@pytest.mark.parametrize("gap", ["nan", "inf", "-inf", "59.9"])
def test_cli_rejects_invalid_gap(tmp_path, capsys, gap):
    assert (
        rso.main(["run", "--data-dir", str(tmp_path / "unused"), f"--gap={gap}"]) == 2
    )
    assert "--gap must be finite and at least 60 seconds" in capsys.readouterr().err
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize(
    "line, expected",
    [
        ('1-1/2" W.T.', {("wall_thickness_in", "1-1/2")}),
        ("wall thickness 0.500-in", {("wall_thickness_in", "0.500")}),
    ],
)
def test_wall_fraction_and_hyphenated_unit(line, expected):
    assert {(q, v) for q, v, _ in rso.find_values(line)} == expected


def test_existing_database_gains_active_membership(env):
    tmp_path, seg, zp = env
    data = tmp_path / "data-0-1"
    data.mkdir()
    with rso.sqlite3.connect(data / "state.sqlite") as db:
        db.executescript(rso.SCHEMA)
        db.execute(
            "INSERT INTO docs(kind, doc_id, status, sha256) "
            "VALUES('ROW', 32733, 'fetched', 'evidence')"
        )
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.db.execute("SELECT status, sha256, active FROM docs").fetchone() == (
        "fetched",
        "evidence",
        1,
    )
    job.prepare()
    assert job.db.execute(
        "SELECT status, sha256, active FROM docs WHERE doc_id=32733"
    ).fetchone() == ("fetched", "evidence", 1)


def test_queue_membership_rolls_back_on_failure(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    job.prepare()
    before = job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
    job.db.execute(
        "CREATE TRIGGER reject_refresh BEFORE UPDATE OF active ON docs "
        "WHEN NEW.active=1 BEGIN SELECT RAISE(ABORT, 'refresh failed'); END"
    )
    job.db.commit()
    with pytest.raises(rso.sqlite3.IntegrityError, match="refresh failed"):
        job.build_queue(zp, seg)
    assert (
        job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall() == before
    )


def test_run_low_forwards_windows_flags(monkeypatch):
    calls = []
    monkeypatch.setattr(
        rso.subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x4000, raising=False
    )
    monkeypatch.setattr(rso.subprocess, "CREATE_NO_WINDOW", 0x8000000, raising=False)

    def run(cmd, **kwargs):
        calls.append(kwargs)
        return rso.subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr(rso.subprocess, "run", run)
    assert rso.run_low(["tesseract", "input", "output"]) == (0, "ok")
    assert calls[0]["creationflags"] == 0x8004000
    assert calls[0]["env"]["OMP_THREAD_LIMIT"] == "1"


@pytest.mark.parametrize(
    "line, quantity, value",
    [
        ("wall thickness 1 1/2 in", "wall_thickness_in", "1 1/2"),
        ("departure angle -12.5 degrees", "hang_off_angle_deg", "-12.5"),
        ("departure angle −12.5 degrees", "hang_off_angle_deg", "-12.5"),
    ],
)
def test_findings_csv_preserves_mixed_fraction_and_sign(env, line, quantity, value):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    job.prepare()
    job.set_doc(
        "ROW",
        32733,
        status="read",
        sha256="fixture digest",
        ocr_sha256="fixture digest",
    )
    tdir = job.text_dir("ROW", 32733)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text(line, encoding="utf-8")
    out = tmp_path / "findings.csv"
    assert rso.write_findings(job, out) == 1
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(rso.csv.reader(fh))
    assert rows == [
        ["segments", "kind", "doc_id", "page", "quantity", "value", "line"],
        ["100", "ROW", "32733", "1", quantity, value, line],
    ]


def test_failed_ocr_retry_keeps_saved_pdf_and_page_digest(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    runner = job.runner

    def fail_second_page(cmd):
        if Path(cmd[0]).name == "tesseract" and "0002" in cmd[1]:
            return 1, "page two failed"
        return runner(cmd)

    job.runner = fail_second_page
    assert job.run() == 0
    page_one = job.text_dir("PIPEMAPS", 19963) / "page-0001.txt"
    first_text = page_one.read_text()
    # SHA-256 pinned independently with sha256sum for the literal PDF fixture.
    original_digest = "fba53e3eb0e2cec344bfd441e032a5b69eaf589e3150d54b93f4be45c25d3ee2"
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(200, {}, PDF + b"replacement")]
    retry = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    assert retry.requeue_failed() == 1
    # Leave no other document eligible; only the failed OCR must resume.
    retry.db.execute("UPDATE docs SET active=0 WHERE doc_id != 19963")
    retry.db.commit()
    assert retry.run() == 0
    assert fetcher.doc_urls() == [url]
    assert page_one.read_text() == first_text
    assert retry.db.execute(
        "SELECT status, sha256, ocr_sha256 FROM docs WHERE doc_id=19963"
    ).fetchone() == ("read", original_digest, original_digest)
    renders = [c for c in retry.runner_calls if Path(c[0]).name == "pdftoppm"]
    assert [c[c.index("-f") + 1] for c in renders] == ["2"]


def test_ocr_refuses_changed_saved_pdf(env):
    job, _ = fetched_backlog(env)
    pdf = job.pdf_path("PIPEMAPS", 19963)
    job.set_doc("PIPEMAPS", 19963, sha256=rso.sha256_of(pdf))
    pdf.write_bytes(PDF + b"changed")
    assert job.ocr_doc("PIPEMAPS", 19963) is False
    assert job.runner_calls == []
    assert job.db.execute(
        "SELECT status, last_error FROM docs WHERE doc_id=19963"
    ).fetchone() == ("ocr_failed", "saved PDF digest mismatch")


def test_legacy_unbound_pages_are_archived_before_ocr(env):
    job, _ = fetched_backlog(env)
    tdir = job.text_dir("PIPEMAPS", 19963)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text("unbound evidence")
    assert job.ocr_doc("PIPEMAPS", 19963) is True
    assert (tdir / "page-0001.txt").read_text() != "unbound evidence"
    archives = list(tdir.parent.glob("19963-unverified-*"))
    assert len(archives) == 1
    assert (archives[0] / "page-0001.txt").read_text() == "unbound evidence"


@pytest.mark.parametrize("has_active", [False, True])
def test_original_schema_matching_key_is_invalidated(env, has_active):
    tmp_path, seg, zp = env
    data = tmp_path / "data-0-1"
    data.mkdir()
    # Original schema, not the current module's schema constant.
    with rso.sqlite3.connect(data / "state.sqlite") as db:
        db.executescript(
            """
            CREATE TABLE docs (
              kind TEXT NOT NULL, doc_id INTEGER NOT NULL, segments TEXT, pass INTEGER,
              index_pages INTEGER, index_size INTEGER,
              status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
              size INTEGER, sha256 TEXT, pages INTEGER, last_error TEXT,
              updated_utc TEXT, PRIMARY KEY (kind, doc_id));
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        """
        )
        if has_active:
            db.execute("ALTER TABLE docs ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        db.execute(
            "INSERT INTO docs(kind, doc_id, pass, status, sha256) "
            "VALUES('ROW', 32733, 1, 'queued', 'retained evidence')"
        )
        seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
        key = f"{rso.sha256_of(zp)}:{rso.sha256_of(seg)}:0/1"
        db.execute("INSERT INTO meta VALUES('queue_key', ?)", (key,))
        db.execute("INSERT INTO meta VALUES('shard', '0/1')")
    clock = FakeClock(NIGHT)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.meta("queue_key") is None
    assert job.run() == 0
    assert job.fetcher.calls == []
    assert job.next_doc() is None
    assert job.db.execute("SELECT sha256, active FROM docs").fetchone() == (
        "retained evidence",
        0,
    )
    status = job.status()
    assert status["by_pass_status"] == []
    assert status["archived_by_pass_status"] == [
        {"pass": 1, "status": "queued", "docs": 1, "pages": 0, "bytes": 0}
    ]


@pytest.mark.parametrize("invalid", ["missing_both", "missing_one", "headers", "empty"])
def test_invalid_index_keeps_membership_and_key(env, invalid):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.prepare() == 0
    before = job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
    key = job.meta("queue_key")
    with zipfile.ZipFile(zp, "w") as zf:
        if invalid == "missing_both":
            zf.writestr("unrelated.txt", "DOC_ID,SEGMENT_NUMBER\n1,100\n")
        else:
            zf.writestr("scan_row.txt", ROW_TXT)
            if invalid != "missing_one":
                zf.writestr(
                    "scan_pipeline_maps.txt",
                    "WRONG,HEADER\n1,100\n" if invalid == "headers" else "",
                )
    assert job.prepare() == 5
    assert job.meta("queue_key") == key
    assert (
        job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall() == before
    )
    assert job.fetcher.calls == []


def test_disk_floor_after_download_with_max_docs_one(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools, max_docs=1)
    job.disk_usage = lambda p: (
        Usage(100e9, 99e9, 1e9) if fetcher.doc_urls() else Usage(1000e9, 500e9, 500e9)
    )
    assert job.run() == 4
    assert len(fetcher.doc_urls()) == 1
    assert not any(Path(c[0]).name == "pdftoppm" for c in job.runner_calls)
    assert job.errors_today() == 0


@pytest.mark.parametrize("destination", [rso.doc_url("ROW", 32733), rso.ROBOTS_URL])
def test_http_redirect_never_issues_second_get(monkeypatch, tmp_path, destination):
    calls = []

    class RedirectTransport(rso.urllib.request.HTTPSHandler):
        def https_open(self, req):
            calls.append(req.full_url)
            headers = Message()
            headers["Location"] = destination
            response = addinfourl(io.BytesIO(b""), headers, req.full_url, 302)
            response.msg = "Found"
            return response

    monkeypatch.setattr(
        rso,
        "_OPENER",
        rso.urllib.request.build_opener(rso._SameHostRedirect, RedirectTransport),
    )
    result = rso.http_fetch(rso.INDEX_ZIP_URL, tmp_path / "unused")
    assert result.status == 302
    assert calls == [rso.INDEX_ZIP_URL]
    assert not (tmp_path / "unused").exists()


def test_redirect_defers_without_charging_error(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(302, {"location": url})]
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1)
    assert job.run() == 0
    assert fetcher.doc_urls() == [url, rso.doc_url("ROW", 32733)]
    assert job.errors_today() == 0
    assert job.db.execute(
        "SELECT status, attempts FROM docs WHERE doc_id=19963"
    ).fetchone() == ("queued", 1)


@pytest.mark.parametrize("has_binding_column", [False, True])
def test_completed_unbound_ocr_is_excluded_until_regenerated(env, has_binding_column):
    job, clock = fetched_backlog(env)
    pdf = job.pdf_path("PIPEMAPS", 19963)
    job.set_doc("PIPEMAPS", 19963, status="read", sha256=rso.sha256_of(pdf), pages=2)
    tdir = job.text_dir("PIPEMAPS", 19963)
    tdir.mkdir(parents=True)
    old = tdir / "page-0001.txt"
    old.write_text("wall thickness 9 mm")
    if not has_binding_column:
        job.db.execute("ALTER TABLE docs DROP COLUMN ocr_sha256")
        job.db.commit()
    job.db.close()
    retry = make_job(env[0], env[1], env[2], clock, FakeFetcher(clock), which=all_tools)
    assert retry.db.execute(
        "SELECT status FROM docs WHERE doc_id=19963"
    ).fetchone() == ("fetched",)
    assert old.read_text() == "wall thickness 9 mm"
    out = env[0] / "findings.csv"
    assert rso.write_findings(retry, out) == 0
    assert retry.run() == 0
    assert rso.write_findings(retry, out) == 4
    assert "wall_thickness_mm,9" not in out.read_text()
    archives = list(tdir.parent.glob("19963-unverified-*"))
    assert len(archives) == 1
    assert (archives[0] / old.name).read_text() == "wall thickness 9 mm"
    assert retry.fetcher.calls == []


@pytest.mark.parametrize("bound", [None, "different digest"])
def test_export_excludes_unbound_completed_rows(env, bound):
    job, _ = fetched_backlog(env)
    job.set_doc(
        "PIPEMAPS", 19963, status="read", sha256="saved digest", ocr_sha256=bound
    )
    tdir = job.text_dir("PIPEMAPS", 19963)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text("wall thickness 9 mm")
    assert rso.write_findings(job, env[0] / "findings.csv") == 0


@pytest.mark.parametrize("invalid", ["missing_members", "headers", "not_zip"])
def test_invalid_download_is_not_installed_and_next_batch_retries(env, invalid):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("unrelated.txt", "unused")
        if invalid == "headers":
            zf.writestr("scan_row.txt", ROW_TXT)
            zf.writestr("scan_pipeline_maps.txt", "WRONG,HEADER\n")
    payload = b"not a zip" if invalid == "not_zip" else bad.getvalue()
    fetcher.script[rso.INDEX_ZIP_URL] = [rso.Response(200, {}, payload)]
    job = make_job(tmp_path, seg, None, clock, fetcher, max_docs=1)
    assert job.run() == 5
    assert not (job.dir / rso.INDEX_ZIP_NAME).exists()
    assert job.meta("queue_key") is None
    assert fetcher.doc_urls() == []
    assert make_job(tmp_path, seg, None, clock, fetcher, max_docs=1).run() == 0
    assert [u for _, u in fetcher.calls].count(rso.INDEX_ZIP_URL) == 2
    assert len(fetcher.doc_urls()) == 1


@pytest.mark.parametrize("defer", ["redirect", "robots", "network", "gap"])
def test_missing_index_deferral_does_not_process_stale_queue(env, defer):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools)
    assert job.prepare() == 0
    # Include fetched OCR work as well as queued downloads from the old selection.
    pdf = job.pdf_path("PIPEMAPS", 19963)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(PDF)
    job.set_doc("PIPEMAPS", 19963, status="fetched")
    seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
    job.cfg.index_zip = None
    if defer == "robots":
        fetcher.script[rso.ROBOTS_URL] = [rso.Response(0, error="unavailable")]
    elif defer in ("redirect", "network"):
        fetcher.script[rso.INDEX_ZIP_URL] = [
            rso.Response(302 if defer == "redirect" else 0)
        ]
    else:
        clock.t = NIGHT.replace(hour=10, minute=59, second=30)
        job.set_meta("last_request_utc", clock.now().isoformat())
    assert job.run() == 0
    assert fetcher.doc_urls() == []
    assert job.runner_calls == []
    assert job.next_doc() is not None  # evidence retained, but not processed


@pytest.mark.parametrize(
    "header", ["wrong,header", "segment_num", "segment_num,max_water_depth_ft", ""]
)
def test_invalid_segment_headers_preserve_queue_and_key(env, header):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.prepare() == 0
    before = job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
    key = job.meta("queue_key")
    seg.write_text(header + "\n")
    assert job.run() == 5
    assert job.meta("queue_key") == key
    assert (
        job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall() == before
    )
    assert job.fetcher.calls == []


def test_permanent_pdf_redirect_does_not_block_other_documents(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(301, {"location": url}) for _ in range(2)]
    for _ in range(2):
        job = make_job(tmp_path, seg, zp, clock, fetcher)
        assert job.run() == 0
    assert fetcher.doc_urls() == [
        url,
        rso.doc_url("ROW", 32733),
        rso.doc_url("ROW", 32737),
    ]
    assert job.errors_today() == 0
    assert job.db.execute(
        "SELECT status, attempts FROM docs WHERE doc_id=19963"
    ).fetchone() == ("queued", 1)
    assert all(
        (b[0] - a[0]).total_seconds() >= 60
        for a, b in zip(fetcher.calls, fetcher.calls[1:])
    )


@pytest.mark.parametrize(
    "line, expected",
    [
        ("riser length 120''", []),
        ("riser length 100 15/16 ft", [("riser_length_ft", "100 15/16")]),
        ("riser length 100-15/16 ft", [("riser_length_ft", "100-15/16")]),
        ("riser length 100 15/16''", []),
        ("riser length 100' 6\"", []),
        ("riser length 100'-6\"", []),
        ("riser length 100'6\"", []),
        ("riser length 100 ft 6 in", []),
        ("riser length 100 ft. 6 in.", []),
        ("riser length 100 feet 6 inches", []),
        ("riser length 100 ft 6-1/2 inches", []),
        ('riser length 100 ft 1/2"', []),
        ("riser length 100 ft 6.5''", []),
        ("riser length 100 ft of 6 in pipe", [("riser_length_ft", "100")]),
    ],
)
def test_riser_dimension_csv_requires_entire_value_and_feet(env, line, expected):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.prepare() == 0
    job.set_doc("ROW", 32733, status="read", sha256="bound", ocr_sha256="bound")
    tdir = job.text_dir("ROW", 32733)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text(line, encoding="utf-8")
    out = tmp_path / "dimensions.csv"
    assert rso.write_findings(job, out) == len(expected)
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(rso.csv.DictReader(fh))
    assert [(r["quantity"], r["value"]) for r in rows] == expected


@pytest.mark.parametrize("interrupted_key", ["queue_key", "shard"])
def test_queue_key_and_membership_roll_back_together_on_restart(env, interrupted_key):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    original = "segment_num,max_water_depth_ft,static_check_tier\n"
    seg.write_text(original)
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.prepare() == 0
    old_key = job.meta("queue_key")
    job.db.execute(
        "CREATE TRIGGER interrupt_key BEFORE INSERT ON meta "
        f"WHEN NEW.key='{interrupted_key}' "
        "BEGIN SELECT RAISE(ABORT, 'interrupted key write'); END"
    )
    job.db.commit()
    seg.write_text(SEGMENTS)
    with pytest.raises(rso.sqlite3.IntegrityError, match="interrupted key write"):
        job.prepare()
    assert job.meta("queue_key") == old_key
    assert job.db.execute("SELECT COUNT(*) FROM docs WHERE active=1").fetchone() == (0,)
    seg.write_text(original)
    job.db.close()
    retry = make_job(tmp_path, seg, zp, clock, fetcher)
    assert retry.run() == 0
    assert fetcher.calls == []


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("invalid", ["not_zip", "members", "headers"])
def test_preexisting_invalid_index_retries_only_managed_copy(env, explicit, invalid):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(tmp_path, seg, zp, clock, fetcher, max_docs=1)
    assert job.prepare() == 0
    before = job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
    old_key = job.meta("queue_key")
    target = zp if explicit else job.dir / rso.INDEX_ZIP_NAME
    if invalid == "not_zip":
        target.write_bytes(b"invalid cached archive")
    else:
        with zipfile.ZipFile(target, "w") as zf:
            zf.writestr("scan_row.txt", ROW_TXT)
            if invalid == "headers":
                zf.writestr("scan_pipeline_maps.txt", "WRONG,HEADER\n")
    invalid_bytes = target.read_bytes()
    job.cfg.index_zip = target if explicit else None
    assert job.run() == (5 if explicit else 0)
    if explicit:
        assert target.read_bytes() == invalid_bytes
        assert fetcher.calls == []
        assert job.meta("queue_key") == old_key
        assert (
            job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
            == before
        )
    else:
        assert target.read_bytes() == fetcher.zip_bytes
        quarantined = list(job.dir.glob(rso.INDEX_ZIP_NAME + ".invalid-*"))
        assert len(quarantined) == 1
        assert quarantined[0].read_bytes() == invalid_bytes
        assert [u for _, u in fetcher.calls].count(rso.INDEX_ZIP_URL) == 1
        assert len(fetcher.doc_urls()) == 1


def test_redirect_deferral_survives_short_batches_and_expires(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    leading = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[leading] = [rso.Response(301, {"location": leading})] * 3
    seed = make_job(tmp_path, seg, zp, clock, fetcher)
    assert seed.prepare() == 0
    assert seed.robots_ok(leading)
    clock.sleep(60)
    for _ in range(2):
        job = make_job(tmp_path, seg, zp, clock, fetcher, max_minutes=1)
        assert job.run() == 0
    assert fetcher.doc_urls()[:2] == [leading, rso.doc_url("ROW", 32733)]
    assert fetcher.doc_urls().count(leading) == 1
    assert job.errors_today() == 0
    assert job.db.execute(
        "SELECT status, attempts FROM docs WHERE doc_id=19963"
    ).fetchone() == ("queued", 1)
    clock.sleep(24 * 3600)
    # Refreshing the day-old robots cache needs its own spaced request.
    retry = make_job(tmp_path, seg, zp, clock, fetcher, max_minutes=2)
    assert retry.run() == 0
    # The untried document precedes the redirect within the same pass.
    assert fetcher.doc_urls() == [
        leading,
        rso.doc_url("ROW", 32733),
        rso.doc_url("ROW", 32737),
    ]
    retry = make_job(tmp_path, seg, zp, clock, fetcher, max_minutes=1)
    assert retry.run() == 0
    assert fetcher.doc_urls().count(leading) == 2
    for _ in range(2):
        clock.sleep(24 * 3600)
        job = make_job(tmp_path, seg, zp, clock, fetcher)
        assert job.run() == 0
        assert fetcher.doc_urls().count(leading) == 3
        assert job.db.execute(
            "SELECT status, attempts, last_error FROM docs WHERE doc_id=19963"
        ).fetchone() == ("failed", 3, "HTTP 301 redirect")
        assert job.errors_today() == 0


def test_wrong_shard_requeue_leaves_failed_attempts_unchanged(env, monkeypatch):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.prepare() == 0
    job.set_doc("ROW", 32733, status="failed", attempts=3)
    monkeypatch.setattr(rso, "lower_own_priority", lambda: None)
    assert (
        rso.main(
            [
                "run",
                "--data-dir",
                str(job.dir),
                "--shard",
                "1/2",
                "--segments",
                str(seg),
                "--index-zip",
                str(zp),
                "--requeue-failed",
            ]
        )
        == 2
    )
    assert job.db.execute(
        "SELECT status, attempts FROM docs WHERE doc_id=32733"
    ).fetchone() == ("failed", 3)


def test_ocr_backlog_obeys_selected_pass(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock), which=all_tools)
    assert job.prepare() == 0
    for doc_id in (32733, 32735):
        pdf = job.pdf_path("ROW", doc_id)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(PDF)
        job.set_doc("ROW", doc_id, status="fetched")
    assert job.run() == 0
    assert job.db.execute(
        "SELECT doc_id, status FROM docs WHERE kind='ROW' AND status!='queued' ORDER BY doc_id"
    ).fetchall() == [(32733, "read"), (32735, "fetched")]
    job.cfg.max_pass = 3
    assert job.run() == 0
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=32735").fetchone() == (
        "read",
    )


def test_robots_403_keeps_long_retry_after_across_restart(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    fetcher.script[rso.ROBOTS_URL] = [rso.Response(403, {"retry-after": "172800"})]
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.run() == 3
    assert job.meta("backoff_until") == (NIGHT + timedelta(hours=48)).isoformat()
    clock.sleep(25 * 3600)
    assert make_job(tmp_path, seg, zp, clock, fetcher).run() == 0
    assert len(fetcher.calls) == 1
    clock.sleep(23 * 3600)
    assert make_job(tmp_path, seg, zp, clock, fetcher).run() == 0
    assert len(fetcher.calls) > 1


@pytest.mark.parametrize("unknown", [None, float("nan"), float("inf")])
def test_unknown_load_defers_ocr_without_rendering(env, unknown):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    job = make_job(
        tmp_path,
        seg,
        zp,
        clock,
        FakeFetcher(clock),
        which=all_tools,
        max_docs=1,
        max_minutes=5,
    )
    job.loadavg = lambda: unknown
    assert job.run() == 0
    assert not any(Path(c[0]).name == "pdftoppm" for c in job.runner_calls)
    assert (clock.now() - NIGHT).total_seconds() <= 60
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "fetched",
    )
    job.loadavg = lambda: 0.5
    assert job.run() == 0
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "read",
    )


@pytest.mark.parametrize("error", [AttributeError, OSError])
def test_unavailable_system_load_is_unknown(monkeypatch, error):
    def unavailable():
        raise error("load unavailable")

    monkeypatch.setattr(rso.os, "getloadavg", unavailable, raising=False)
    assert rso.load5() is None


@pytest.mark.parametrize("opt_in, expected", [(False, "fetched"), (True, "read")])
def test_cli_ocr_without_system_load(env, monkeypatch, opt_in, expected):
    job, _ = fetched_backlog(env)
    monkeypatch.delattr(rso.os, "getloadavg", raising=False)
    job.loadavg = rso.load5

    def offline_job(cfg):
        job.cfg = cfg
        return job

    monkeypatch.setattr(rso, "Job", offline_job)
    monkeypatch.setattr(rso, "lower_own_priority", lambda: None)
    args = [
        "run",
        "--data-dir",
        str(job.dir),
        "--segments",
        str(job.cfg.segments),
        "--index-zip",
        str(job.cfg.index_zip),
    ]
    if opt_in:
        args.append("--allow-missing-load")
    assert rso.main(args) == 0
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        expected,
    )


@pytest.mark.parametrize("load", [9.0, float("inf"), float("nan")])
def test_missing_load_opt_in_keeps_measured_load_guard(env, load):
    job, _ = fetched_backlog(env, allow_missing_load=True, max_minutes=1)
    job.loadavg = lambda: load
    assert job.run() == 0
    assert job.runner_calls == []
    assert job.db.execute("SELECT status FROM docs WHERE doc_id=19963").fetchone() == (
        "fetched",
    )


def test_unknown_load_defers_entire_backlog_before_hashing(env, monkeypatch):
    job, _ = fetched_backlog(env)
    job.set_doc("ROW", 32733, status="fetched")
    readings = []

    def unknown_load():
        readings.append(None)
        return None

    job.loadavg = unknown_load
    monkeypatch.setattr(rso, "sha256_of", lambda pdf: pytest.fail("PDF was hashed"))
    job.ocr_backlog()
    assert readings == [None]
    assert job.runner_calls == []
    assert job.db.execute(
        "SELECT count(*) FROM docs WHERE status='fetched'"
    ).fetchone() == (2,)


def test_long_line_csv_excerpt_contains_value_and_unit(env):
    tmp_path, seg, zp = env
    clock = FakeClock(DAY)
    job = make_job(tmp_path, seg, zp, clock, FakeFetcher(clock))
    assert job.prepare() == 0
    job.set_doc("ROW", 32733, status="read", sha256="bound", ocr_sha256="bound")
    tdir = job.text_dir("ROW", 32733)
    tdir.mkdir(parents=True)
    (tdir / "page-0001.txt").write_text(
        "prefix " * 40 + "wall thickness 9.50 mm " + "suffix " * 40
    )
    out = tmp_path / "excerpt.csv"
    assert rso.write_findings(job, out) == 1
    with out.open() as fh:
        (row,) = rso.csv.DictReader(fh)
    assert row["quantity"] == "wall_thickness_mm"
    assert row["value"] == "9.50"
    assert "wall thickness 9.50 mm" in row["line"]
    assert len(row["line"]) == 200


def test_previous_version_key_forces_rebuild_after_interrupted_membership(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.prepare() == 0
    seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
    # The earlier version could commit new membership but keep an older key.
    job.set_meta("queue_key", f"v2:{rso.sha256_of(zp)}:{rso.sha256_of(seg)}:0/1")
    job.db.close()
    retry = make_job(tmp_path, seg, zp, clock, fetcher)
    assert retry.meta("queue_key") is None
    assert retry.run() == 0
    assert fetcher.calls == []
    assert retry.status()["by_pass_status"] == []
    assert retry.db.execute("SELECT COUNT(*) FROM docs").fetchone() == (6,)


@pytest.mark.parametrize("defer", ["outside_window", "index_redirect"])
def test_invalid_managed_index_replacement_deferral_retains_evidence(env, defer):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock, zip_bytes=zp.read_bytes())
    job = make_job(tmp_path, seg, zp, clock, fetcher, which=all_tools)
    assert job.prepare() == 0
    before = job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall()
    key = job.meta("queue_key")
    job.cfg.index_zip = None
    (job.dir / rso.INDEX_ZIP_NAME).write_bytes(b"invalid cached archive")
    seg.write_text("segment_num,max_water_depth_ft,static_check_tier\n")
    if defer == "outside_window":
        clock.t = DAY
    else:
        fetcher.script[rso.INDEX_ZIP_URL] = [rso.Response(301)]
    assert job.run() == 0
    assert fetcher.doc_urls() == []
    assert job.runner_calls == []
    assert job.meta("queue_key") == key
    assert (
        job.db.execute("SELECT * FROM docs ORDER BY kind, doc_id").fetchall() == before
    )


def test_pdf_redirect_retry_after_sets_document_deadline(env):
    tmp_path, seg, zp = env
    clock = FakeClock(NIGHT)
    fetcher = FakeFetcher(clock)
    url = rso.doc_url("PIPEMAPS", 19963)
    fetcher.script[url] = [rso.Response(302, {"retry-after": "172800"})]
    job = make_job(tmp_path, seg, zp, clock, fetcher)
    assert job.prepare() == 0
    assert job.fetch_doc(job.next_doc()) == "redirected"
    assert job.db.execute(
        "SELECT deferred_until FROM docs WHERE doc_id=19963"
    ).fetchone() == ((NIGHT + timedelta(seconds=60, hours=48)).isoformat(),)
    assert job.next_doc()[1] == 32733
    assert job.errors_today() == 0
