"""Fetch only links confirmed on the BSEE raw-data page; retain a receipt."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PAGE = "https://www.data.bsee.gov/Main/RawData.aspx"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="snapshot folder under data/modules/bsee/zip (default: today, UTC)",
    )
    snapshot = parser.parse_args(argv).snapshot
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", snapshot):
        raise ValueError("snapshot must be a YYYY-MM-DD folder name")
    repo_root = Path(__file__).resolve().parents[3]
    root = repo_root / "data/modules/bsee/zip" / snapshot
    # A retained snapshot is evidence for published outputs; never replace it.
    if (root / "manifest.json").exists():
        raise FileExistsError(f"snapshot {snapshot} already has a manifest")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}
    }
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", str(root / "BoreholeRawData.zip")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if ignored.returncode != 0:
        raise ValueError("raw download directory must be gitignored before writing")
    root.mkdir(parents=True, exist_ok=True)
    page = urllib.request.urlopen(PAGE, timeout=120).read().decode()
    files = []
    for name in (
        "BoreholeRawData.zip",
        "eWellAPMRawData.zip",
        "eWellEORRawData.zip",
        "eWellWARRawData.zip",
    ):
        row = next(
            r for r in re.findall(r"<tr.*?</tr>", page, re.S | re.I) if name in r
        )
        href = re.search(r'href=["\']([^"\']*' + name + r')["\']', row, re.I)[1]
        url = urllib.request.urljoin(PAGE, href)
        date = re.search(r"\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M", row)[0]
        receipt = dict(
            name=name,
            url=url,
            page_last_updated=date,
            download_utc=datetime.now(timezone.utc).isoformat(),
        )
        try:
            path = root / name
            with (
                urllib.request.urlopen(url, timeout=600) as response,
                path.open("wb") as out,
            ):
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            with zipfile.ZipFile(path) as archive:
                print(name, path.stat().st_size, archive.namelist(), flush=True)
            receipt.update(
                bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                status="downloaded",
            )
        except Exception as exc:
            receipt.update(status="failed", error=str(exc))
        files.append(receipt)
        (root / "manifest.json").write_text(
            json.dumps(
                dict(source_id="bsee-data-center", page=PAGE, files=files), indent=2
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )


if __name__ == "__main__":
    main()
