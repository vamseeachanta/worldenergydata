"""Record resolving public citation URLs; retain only the small receipt."""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


def main():
    root = Path(__file__).resolve().parent
    basis = yaml.safe_load((root / "cost_basis.yml").read_text(encoding="utf-8"))
    rows = []
    for key, source in basis["sources"].items():
        receipt = dict(
            source=key,
            url=source["url"],
            checked_utc=datetime.now(timezone.utc).isoformat(),
        )
        request = urllib.request.Request(
            source["url"], headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            digest, size = hashlib.sha256(), 0
            if "pdf" not in response.headers.get("Content-Type", "").lower():
                raise ValueError(f"citation did not resolve to PDF: {key}")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
            receipt.update(
                http_status=response.status,
                resolved_url=response.url,
                bytes=size,
                sha256=digest.hexdigest(),
            )
        rows.append(receipt)
        print(key, receipt["http_status"], size, flush=True)
    (root / "output/cost_source_manifest.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
