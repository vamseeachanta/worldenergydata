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
from pathlib import Path

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
    job.set_doc("PIPEMAPS", 19963, status="fetched")
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
