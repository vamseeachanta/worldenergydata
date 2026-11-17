"""Select normalized local GeoJSON and render a regional SVG without retrieval.

Coordinates are longitude/latitude degrees in EPSG:4326. Source evidence is
caller supplied, retained in the image, and not independently authenticated.
"""

import json
import math
import re
from copy import deepcopy
from xml.etree.ElementTree import Element, SubElement, tostring

_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")


def _text(value):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and all(
            c in "\t\n\r"
            or " " <= c <= "\ud7ff"
            or "\ue000" <= c <= "\ufffd"
            or "\U00010000" <= c <= "\U0010ffff"
            for c in value
        )
    )


def _key(properties):
    if not isinstance(properties, dict) or not all(
        _text(properties.get(k)) for k in ("area", "block")
    ):
        raise ValueError("Each feature needs explicit area and block strings")
    return properties["area"], properties["block"]


def _signed_area(ring):
    # Use a local origin to avoid cancellation at large longitudes.
    ox, oy = ring[0]
    return sum(
        (a[0] - ox) * (b[1] - oy) - (b[0] - ox) * (a[1] - oy)
        for a, b in zip(ring, ring[1:] + ring[:1])
    )


def _reject_legacy_crs(value):
    if "crs" in value:
        raise ValueError("Remove legacy CRS declarations after explicit normalization")


def _polygons(geometry):
    if not isinstance(geometry, dict) or geometry.get("type") not in (
        "Polygon",
        "MultiPolygon",
    ):
        raise ValueError("Only Polygon and MultiPolygon geometry is supported")
    _reject_legacy_crs(geometry)
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("Geometry must contain polygons")
    polygons = [coordinates] if geometry["type"] == "Polygon" else coordinates
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("A polygon must contain an exterior ring")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError("A ring needs at least four positions")
            for point in ring:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(
                        type(v) in (int, float) and -limit <= v <= limit
                        for v, limit in zip(point, (180, 90))
                    )
                ):
                    raise ValueError(
                        "Positions must be finite longitude/latitude pairs"
                    )
            if ring[0] != ring[-1]:
                raise ValueError("Rings must be closed")
            if _signed_area(ring) == 0:
                raise ValueError("Rings must enclose nonzero area")
    return polygons


def select_blocks(document: dict, requested: dict[tuple[str, str], str]) -> dict:
    """Return a detached, complete FeatureCollection in requested key order.

    ``requested`` maps exact (area, block) string pairs to display groups.
    Every feature identity is checked; geometry is checked for selected features.
    Duplicate identities, missing keys and malformed source evidence raise
    ValueError. No identifier coercion, partial selection or geometry repair occurs.
    """
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    _reject_legacy_crs(document)
    source = document.get("source")
    required = ("source_id", "release", "sha256", "terms", "crs", "units")
    if not isinstance(source, dict) or not all(_text(source.get(k)) for k in required):
        raise ValueError(
            "Source identity, release, digest, terms, CRS and units are required"
        )
    if source["crs"] != "EPSG:4326" or source["units"] != "degrees":
        raise ValueError("Only EPSG:4326 longitude/latitude degrees are supported")
    if not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("Source sha256 must contain 64 lowercase hexadecimal digits")
    if (
        not isinstance(requested, dict)
        or not requested
        or any(
            not isinstance(key, tuple)
            or len(key) != 2
            or not all(_text(part) for part in key)
            or not _text(group)
            for key, group in requested.items()
        )
    ):
        raise ValueError("Requested keys and groups must be nonempty strings")
    features = document.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection features must be a list")
    indexed = {}
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Expected GeoJSON features")
        key = _key(feature.get("properties"))
        if key in indexed:
            raise ValueError(f"Duplicate block identity: {key}")
        indexed[key] = feature
    missing = requested.keys() - indexed.keys()
    if missing:
        raise ValueError(f"Missing requested blocks: {sorted(missing)}")
    selected = []
    for key, group in requested.items():
        feature = deepcopy(indexed[key])
        _reject_legacy_crs(feature)
        _polygons(feature.get("geometry"))
        feature["properties"]["group"] = group
        selected.append(feature)
    return {
        "type": "FeatureCollection",
        "source": deepcopy(source),
        "features": selected,
    }


def render_svg(
    document: dict,
    requested: dict[tuple[str, str], str],
    *,
    title: str = "Lease blocks",
) -> str:
    """Render a complete selection as one standalone SVG string.

    A local equirectangular display uses the selection's midpoint latitude and
    one uniform scale. Spans above ten degrees or latitudes beyond 85 degrees
    are rejected. This display provides no engineering distance or area basis.
    Polygon topology and source authenticity must be qualified before ingestion.
    """
    selected = select_blocks(document, requested)
    if not _text(title):
        raise ValueError("Title must be nonempty XML text")
    groups = list(dict.fromkeys(requested.values()))
    if len(groups) > len(_COLORS):
        raise ValueError("At most six distinct display groups are supported")
    geometries = [_polygons(f["geometry"]) for f in selected["features"]]
    points = [
        p
        for polygons in geometries
        for polygon in polygons
        for ring in polygon
        for p in ring
    ]
    west, east = min(p[0] for p in points), max(p[0] for p in points)
    south, north = min(p[1] for p in points), max(p[1] for p in points)
    if east - west > 10 or north - south > 10 or max(abs(south), abs(north)) >= 85:
        raise ValueError(
            "Display requires a regional, nonpolar extent without dateline crossing"
        )
    mid_lon, mid_lat = (west + east) / 2, (south + north) / 2
    cosine = math.cos(math.radians(mid_lat))
    scale = min(640 / ((east - west) * cosine), 400 / (north - south))

    def project(point):
        return (
            400 + (point[0] - mid_lon) * cosine * scale,
            280 - (point[1] - mid_lat) * scale,
        )

    root = Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": "0 0 800 600",
            "role": "img",
        },
    )
    SubElement(root, "title").text = title
    SubElement(root, "desc").text = (
        "Regional polygon display; no distance or area measurements."
    )
    SubElement(root, "metadata").text = json.dumps(selected["source"], sort_keys=True)
    SubElement(root, "rect", {"width": "800", "height": "600", "fill": "white"})

    def label(parent, x, y, text, **attrs):
        SubElement(
            parent, "text", {"x": str(x), "y": str(y), "font-size": "12", **attrs}
        ).text = text

    label(root, 400, 30, title, **{"text-anchor": "middle"})
    for feature, polygons in zip(selected["features"], geometries):
        props = feature["properties"]
        group = SubElement(
            root, "g", {f"data-{k}": props[k] for k in ("area", "block", "group")}
        )
        commands = []
        for polygon in polygons:
            areas = []
            for ring in polygon:
                projected = [tuple(round(v, 9) for v in project(p)) for p in ring[:-1]]
                area = abs(_signed_area(projected))
                if area == 0:
                    raise ValueError("Ring collapses at SVG display precision")
                areas.append(area)
                commands.append(
                    "M" + " L".join(f"{x},{y}" for x, y in projected) + " Z"
                )
            if areas[0] <= sum(areas[1:]):
                raise ValueError("Polygon loses filled area at SVG display precision")
        SubElement(
            group,
            "path",
            {
                "d": " ".join(commands),
                "fill": _COLORS[groups.index(props["group"])],
                "fill-rule": "evenodd",
                "stroke": "#222",
                "stroke-width": "1",
            },
        )
        exterior = [p for polygon in polygons for p in polygon[0]]
        x, y = project(
            (
                (min(p[0] for p in exterior) + max(p[0] for p in exterior)) / 2,
                (min(p[1] for p in exterior) + max(p[1] for p in exterior)) / 2,
            )
        )
        label(
            group,
            x,
            y,
            f"{props['area']} {props['block']}",
            **{"text-anchor": "middle"},
        )
    SubElement(
        root, "path", {"d": "M80,80 V480 H720", "fill": "none", "stroke": "#222"}
    )
    label(root, 400, 520, "Longitude (degrees)", **{"text-anchor": "middle"})
    label(
        root,
        20,
        280,
        "Latitude (degrees)",
        transform="rotate(-90 20 280)",
        **{"text-anchor": "middle"},
    )
    for lon in (west, east):
        x, _ = project((lon, south))
        label(root, x, 498, f"{lon:.4f}", **{"text-anchor": "middle"})
    for lat in (south, north):
        _, y = project((west, lat))
        label(root, 72, y, f"{lat:.4f}", **{"text-anchor": "end"})
    for i, name in enumerate(groups):
        SubElement(
            root,
            "rect",
            {
                "x": str(60 + i * 120),
                "y": "540",
                "width": "10",
                "height": "10",
                "fill": _COLORS[i],
            },
        )
        label(root, 74 + i * 120, 550, name)
    label(
        root,
        400,
        580,
        "Local equirectangular display only; do not read distance or area.",
        **{"text-anchor": "middle"},
    )
    return tostring(root, encoding="unicode") + "\n"
