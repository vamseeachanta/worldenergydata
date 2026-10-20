"""Render public saved Explorer results through a stdlib WSGI API.

Only release records in a maintainer-supplied manifest may be fetched. This
service neither reads credentials nor publishes data. See the deployment guide
in docs/guides/explorer-visualization-api.md for the trust boundary and API.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from http import HTTPStatus
from http.client import HTTPException
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import (
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    HTTPRedirectHandler,
    HTTPSHandler,
    OpenerDirector,
    UnknownHandler,
)
from wsgiref.simple_server import make_server
from xml.etree import ElementTree as ET

ISSUE = "https://github.com/vamseeachanta/worldenergydata/issues/966"
# Full Git SHA-1, not a short hash/tag/branch: HF download guide (accessed 2026):
# https://huggingface.co/docs/huggingface_hub/guides/download#download-a-single-file
COMMIT = re.compile(r"[0-9a-f]{40}")
# SHA-256 hexadecimal representation, as used by the existing bundle exporter.
DIGEST = re.compile(r"[0-9a-f]{64}")
DATASET = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*")


def strict_json(raw):
    """Reject non-JSON numbers and duplicate keys rather than losing evidence."""

    def invalid(_):
        raise ValueError("Invalid JSON number")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(raw, parse_constant=invalid, object_pairs_hook=pairs)


def fullmatch(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def validate_config(config):
    """Fail at startup if release approval or immutable provenance is absent."""
    if not isinstance(config, dict) or not fullmatch(
        COMMIT, config.get("renderer_revision")
    ):
        raise ValueError("A full renderer code revision is required")
    limits = config.get("limits", {})
    if not isinstance(limits, dict):
        raise TypeError("Resource limits must be an object")
    for name in ("request_bytes", "bundle_bytes", "timeout_seconds"):
        if type(limits.get(name)) is not int or limits[name] <= 0:
            raise ValueError("Positive integer resource limits are required")
    releases = config.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ValueError("At least one approved public release is required")
    approved = {}
    for release in releases:
        if not isinstance(release, dict):
            raise TypeError("Invalid release record")
        for name in ("dataset_revision", "source_revision"):
            if not fullmatch(COMMIT, release.get(name)):
                raise ValueError("Full dataset and source code revisions are required")
        if (
            not fullmatch(DATASET, release.get("dataset_id"))
            or not fullmatch(DIGEST, release.get("bundle_sha256"))
            or release.get("public_data_approved") is not True
        ):
            raise ValueError("Approved public dataset and bundle digest are required")
        path = release.get("bundle_path")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or any(p in ("", ".", "..") for p in path.split("/"))
            or "\\" in path
            or PurePosixPath(path).suffix != ".json"
        ):
            raise ValueError("Bundle must be a relative JSON path")
        revision = release["dataset_revision"]
        if revision in approved:
            raise ValueError("Ambiguous dataset revision")
        approved[revision] = dict(release)
    return approved, dict(limits)


def public_opener():
    """Support HTTPS downloads and redirects only, with no ambient proxy/auth.

    OpenerDirector starts without handlers. In particular, adding no file,
    FTP or plain HTTP handler prevents redirects from crossing those schemes.
    """
    opener = OpenerDirector()
    for handler in (
        HTTPSHandler(),
        HTTPRedirectHandler(),
        HTTPDefaultErrorHandler(),
        HTTPErrorProcessor(),
        UnknownHandler(),
    ):
        opener.add_handler(handler)
    return opener


def download(url, *, max_bytes, timeout):
    """Read public HF bytes only; bound memory without a Content-Length."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "huggingface.co"
        or not parsed.path.startswith("/datasets/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only public HF dataset URLs are accepted")
    with public_opener().open(url, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Bundle exceeds configured byte limit")
    return raw


def render_svg(bundle, field_id):
    """Plot saved cumulative oil in MMbbl; no forecast or unit conversion.

    Equation (authored display rule): width = value / max(known values).
    Missing stays unavailable; an all-zero population has zero-width bars.
    Layout coordinates below are UI choices, not engineering coefficients.
    """
    if (
        not isinstance(bundle, dict)
        or bundle.get("schema_version") != "1.0.0"
        or bundle.get("projection") != "field_explorer_results"
        or bundle.get("hf_dataset") != "worldenergydata"
    ):
        raise ValueError("Unsupported results bundle")
    fields = bundle.get("fields")
    sources = bundle.get("sources")
    if (
        not isinstance(fields, dict)
        or not fields
        or not isinstance(sources, list)
        or not sources
        or any(
            not isinstance(s, dict) or not fullmatch(DIGEST, s.get("sha256"))
            for s in sources
        )
    ):
        raise ValueError("Missing saved fields or source digests")
    if field_id is not None and field_id not in fields:
        raise ValueError("Unknown field")
    rows = []
    for key, field in sorted(fields.items()):
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            raise TypeError("Invalid saved field")
        performance = field.get("performance")
        if performance is not None and not isinstance(performance, dict):
            raise ValueError("Invalid saved performance")
        value = (performance or {}).get("cum_oil_mmbbl")
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
        ):
            raise ValueError("Invalid saved cumulative oil")
        rows.append((key, field["name"], value))
    maximum = max((v for _, _, v in rows if v is not None), default=0)
    svg = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        role="img",
        viewBox=f"0 0 960 {80 + 36 * len(rows)}",
    )
    ET.SubElement(svg, "title").text = "Saved cumulative oil by field (MMbbl)"
    ET.SubElement(svg, "desc").text = (
        "Snapshot comparison; field histories cover different periods."
    )
    ET.SubElement(svg, "rect", width="100%", height="100%", fill="white")
    ET.SubElement(svg, "text", x="12", y="28", fill="#13233f").text = (
        "Cumulative oil · MMbbl"
    )
    for index, (key, name, value) in enumerate(rows):
        y = 56 + 36 * index
        ET.SubElement(svg, "text", x="12", y=str(y), fill="#13233f").text = name
        if value is None:
            ET.SubElement(svg, "text", x="300", y=str(y), fill="#5b6b86").text = (
                f"{name}: unavailable"
            )
            continue
        bar = ET.SubElement(
            svg,
            "svg",
            x="300",
            y=str(y - 16),
            width="480",
            height="18",
            viewBox="0 0 1 1",
            preserveAspectRatio="none",
        )
        width = value / maximum if maximum else 0
        ET.SubElement(
            bar,
            "rect",
            {
                "data-field": key,
                "width": format(width, ".12g"),
                "height": "1",
                "fill": "#0B3D91" if key == field_id else "#0f8a7e",
            },
        )
        ET.SubElement(svg, "text", x="800", y=str(y), fill="#13233f").text = str(value)
    return ET.tostring(svg, encoding="unicode")


def create_app(config, *, fetch=download):
    """Return a WSGI callable with a fixed public-release allowlist."""
    approved, limits = validate_config(config)
    renderer_revision = config["renderer_revision"]

    def application(environ, start_response):
        def respond(status, body):
            raw = json.dumps(body, allow_nan=False).encode()
            # Public, credential-free API; CORS permits the static Pages client.
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(raw))),
                ("Cache-Control", "no-store"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
                ("X-Content-Type-Options", "nosniff"),
            ]
            start_response(f"{status.value} {status.phrase}", headers)
            return [raw]

        def error(status, message):
            return respond(status, {"error": message, "issue": ISSUE})

        if environ.get("PATH_INFO") != "/render":
            return error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
        method = environ.get("REQUEST_METHOD")
        if method == "OPTIONS":
            return respond(HTTPStatus.OK, {})
        if method != "POST":
            return error(HTTPStatus.METHOD_NOT_ALLOWED, "Use POST /render")
        try:
            if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
                raise ValueError("JSON required")
            length = int(environ.get("CONTENT_LENGTH", ""))
            if length <= 0:
                raise ValueError("Positive content length required")
            if length > limits["request_bytes"]:
                return error(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    "Request exceeds configured byte limit",
                )
            raw_request = environ["wsgi.input"].read(length)
            if len(raw_request) != length:
                raise ValueError("Truncated request")
            payload = strict_json(raw_request)
            if not isinstance(payload, dict) or set(payload) - {
                "dataset_revision",
                "field_id",
            }:
                raise ValueError("Unsupported request")
            revision = payload.get("dataset_revision")
            if not fullmatch(COMMIT, revision) or revision not in approved:
                raise ValueError("Unapproved dataset revision")
            field_id = payload.get("field_id")
            if field_id is not None and not isinstance(field_id, str):
                raise ValueError("Invalid field id")
        except (ValueError, UnicodeError):
            return error(
                HTTPStatus.BAD_REQUEST,
                "Use an approved full dataset revision and optional field id",
            )
        release = approved[revision]
        url = (
            f"https://huggingface.co/datasets/{release['dataset_id']}/resolve/{revision}/"
            + quote(release["bundle_path"], safe="/")
        )
        try:
            raw = fetch(
                url, max_bytes=limits["bundle_bytes"], timeout=limits["timeout_seconds"]
            )
            if (
                len(raw) > limits["bundle_bytes"]
                or hashlib.sha256(raw).hexdigest() != release["bundle_sha256"]
            ):
                raise ValueError("Bundle integrity failure")
            bundle = strict_json(raw)
            if (
                field_id is not None
                and isinstance(bundle, dict)
                and isinstance(bundle.get("fields"), dict)
                and field_id not in bundle["fields"]
            ):
                return error(HTTPStatus.BAD_REQUEST, "Unknown field in saved results")
            svg = render_svg(bundle, field_id)
        except (OSError, URLError, HTTPException):
            return error(
                HTTPStatus.SERVICE_UNAVAILABLE, "Saved results are unavailable"
            )
        except (ValueError, TypeError, UnicodeError, OverflowError):
            return error(HTTPStatus.BAD_GATEWAY, "Saved results failed validation")
        return respond(
            HTTPStatus.OK,
            {
                "media_type": "image/svg+xml",
                "svg": svg,
                "metric": "cum_oil_mmbbl",
                "units": "MMbbl",
                "dataset_id": release["dataset_id"],
                "dataset_revision": revision,
                "source_revision": release["source_revision"],
                "renderer_revision": renderer_revision,
                "bundle_sha256": release["bundle_sha256"],
                "sources": bundle["sources"],
                "field_id": field_id,
            },
        )

    return application


def main():
    config = strict_json(Path(os.environ["EXPLORER_RENDER_MANIFEST"]).read_bytes())
    app = create_app(config)
    # Hugging Face Docker Spaces default exposed port, official Docker guide:
    # https://huggingface.co/docs/hub/spaces-sdks-docker (accessed 2026).
    port = int(os.environ.get("PORT", "7860"))
    with make_server(os.environ.get("BIND_HOST", "localhost"), port, app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
