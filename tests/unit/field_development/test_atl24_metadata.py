"""Offline synthetic evidence tests; no science data is acquired."""

import copy
import hashlib
import json
import socket

import pytest

from worldenergydata.field_development.atl24_metadata import main, summarize
from worldenergydata.field_development.terrain import (
    TerrainFetchError,
    fetch_dem,
    load_terrain_sources,
)

CID = "C4085168939-NSIDC_CPRD"
GID = "G4100500270-NSIDC_CPRD"
FILENAME = "ATL24_20181014001049_02350102_006_02_002_01.h5"
TITLE = "ATLAS/ICESat-2 L3A Along Track Coastal and Nearshore Bathymetry V002"
ATOM_NS = "http://www.w3.org/2005/Atom"
CMR_NS = "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#atom"


@pytest.fixture
def evidence():
    collection = {
        "meta": {"concept-id": CID, "revision-date": "2026-10-12T16:32:05.955Z"},
        "umm": {
            "ShortName": "ATL24",
            "Version": "002",
            "EntryTitle": TITLE,
            "DOI": {"DOI": "10.5067/ATLAS/ATL24.002"},
            "AccessConstraints": {
                "Description": "Accessible provided that you are logged into your NASA Earthdata profile"
            },
        },
    }
    old = copy.deepcopy(collection)
    old["meta"]["concept-id"] = "C3433822507-NSIDC_CPRD"
    old["umm"].update(Version="001", DOI={"DOI": "10.5067/ATLAS/ATL24.001"})
    granule = {
        "meta": {
            "concept-id": GID,
            "collection-concept-id": CID,
            "revision-date": "2026-08-10T23:57:29.141Z",
        },
        "umm": {
            "CollectionReference": {"EntryTitle": TITLE},
            "GranuleUR": FILENAME + "_sample",
            "DataGranule": {
                "Identifiers": [
                    {"IdentifierType": "ProducerGranuleId", "Identifier": FILENAME}
                ],
                "ArchiveAndDistributionInformation": [
                    {"Size": 84.37, "SizeUnit": "NA"}
                ],
            },
        },
    }
    atom = f"""<feed xmlns="{ATOM_NS}" xmlns:e="{CMR_NS}"><entry>
      <id>{GID}</id><title>{FILENAME}_sample</title>
      <e:collectionConceptId>{CID}</e:collectionConceptId>
      <e:datasetId>{TITLE}</e:datasetId><e:producerGranuleId>{FILENAME}</e:producerGranuleId>
      <e:granuleSizeMB>84.37</e:granuleSizeMB></entry></feed>"""
    return {"items": [old, collection]}, {"items": [granule]}, atom


def run(evidence):
    c, g, a = evidence
    return summarize(json.dumps(c).encode(), json.dumps(g).encode(), a.encode())


def test_summary_is_bounded_and_deterministic(evidence, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline reader attempted network access")

    monkeypatch.setattr(socket, "socket", forbidden)
    result = run(evidence)
    assert result == run(evidence)
    assert result["collection"]["version"] == "002"
    assert result["historical_collections"][0]["version"] == "001"
    assert result["sample"]["advertised_size"] == {
        "value": "84.37",
        "unit": "MB",
        "source": "atom",
    }
    assert result["sample"]["umm_size_unit"] == "UNVERIFIED"
    assert result["sample"]["payload_bytes"] == "UNVERIFIED"
    assert result["sample"]["payload_sha256"] == "UNVERIFIED"
    assert result["collection_storage"] == {
        "total_bytes": "UNVERIFIED",
        "size_range": "UNVERIFIED",
    }
    assert result["science_access"] == "earthdata_authentication_required"
    assert result["engineering_qualification"] == "UNVERIFIED"
    assert (
        result["sources"]["collections"]["sha256"]
        == hashlib.sha256(json.dumps(evidence[0]).encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "field,value",
    [("Version", "001"), ("ShortName", "ATL03"), ("DOI", {"DOI": "wrong"})],
)
def test_reject_wrong_collection(evidence, field, value):
    evidence[0]["items"][1]["umm"][field] = value
    with pytest.raises(ValueError):
        run(evidence)


@pytest.mark.parametrize("index", [0, 1])
def test_duplicate_ids(evidence, index):
    evidence[index]["items"].append(copy.deepcopy(evidence[index]["items"][0]))
    with pytest.raises(ValueError):
        run(evidence)


@pytest.mark.parametrize(
    "old,new",
    [
        (GID, "G999-NSIDC_CPRD"),
        (CID, "C999-NSIDC_CPRD"),
        (FILENAME, FILENAME.replace("001049", "001050")),
        (TITLE, TITLE.replace("002", "001")),
        ("_sample", "_other"),
    ],
)
def test_atom_mismatch(evidence, old, new):
    c, g, a = evidence
    with pytest.raises(ValueError):
        run((c, g, a.replace(old, new)))


def test_umm_collection_mismatch(evidence):
    evidence[1]["items"][0]["meta"]["collection-concept-id"] = "C999-NSIDC_CPRD"
    with pytest.raises(ValueError):
        run(evidence)


@pytest.mark.parametrize("unit", [None, "NA", "unspecified", "MB"])
def test_umm_units_do_not_become_bytes(evidence, unit):
    info = evidence[1]["items"][0]["umm"]["DataGranule"][
        "ArchiveAndDistributionInformation"
    ][0]
    if unit is None:
        info.pop("SizeUnit")
    else:
        info["SizeUnit"] = unit
    assert run(evidence)["sample"]["payload_bytes"] == "UNVERIFIED"


@pytest.mark.parametrize("size", ["-1", "NaN", "Infinity", "", "bad"])
def test_invalid_atom_sizes(evidence, size):
    c, g, a = evidence
    with pytest.raises(ValueError):
        run((c, g, a.replace("84.37", size)))


def test_missing_atom_size_stays_unverified(evidence):
    c, g, a = evidence
    assert (
        run((c, g, a.replace("<e:granuleSizeMB>84.37</e:granuleSizeMB>", "")))[
            "sample"
        ]["advertised_size"]
        == "UNVERIFIED"
    )


def test_ambiguous_atom_size_rejected(evidence):
    c, g, a = evidence
    with pytest.raises(ValueError):
        run(
            (
                c,
                g,
                a.replace("</entry>", "<e:granuleSizeMB>10</e:granuleSizeMB></entry>"),
            )
        )


@pytest.mark.parametrize(
    "bad", [b"{}", b"[]", b"null", b"not json", b'{"items":null}', b'{"items":[{}]}']
)
def test_malformed_json(evidence, bad):
    with pytest.raises(ValueError):
        summarize(bad, json.dumps(evidence[1]).encode(), evidence[2].encode())


def test_malformed_xml(evidence):
    with pytest.raises(ValueError):
        summarize(
            json.dumps(evidence[0]).encode(),
            json.dumps(evidence[1]).encode(),
            b"<broken",
        )


def test_no_contacts_credentials_or_download_links(evidence):
    contact = "private" + "@" + "example.invalid"
    evidence[0]["items"][1]["umm"]["ContactPersons"] = [{"Email": contact}]
    evidence[1]["items"][0]["umm"]["RelatedUrls"] = [
        {"URL": "https://example.invalid/payload.h5?token=secret"}
    ]
    output = json.dumps(run(evidence))
    assert contact not in output
    assert "token=secret" not in output
    assert "example.invalid" not in output


def test_catalogue_metadata_limits():
    sources = load_terrain_sources()
    assert len(sources) == 6
    entry = sources["nasa_icesat2_atl24"]
    assert entry["status"] == "verified"
    assert entry["metadata_only"] is True
    assert entry["science_authentication_required"] is True
    assert entry["engineering_qualification"] == "UNVERIFIED"


def test_catalogue_cannot_enable_science_download(tmp_path):
    with pytest.raises(TerrainFetchError):
        fetch_dem(
            (-1, -1, 1, 1), tmp_path / "unused.tif", source_id="nasa_icesat2_atl24"
        )


def test_missing_authentication_evidence_rejected(evidence):
    evidence[0]["items"][1]["umm"].pop("AccessConstraints")
    with pytest.raises(ValueError):
        run(evidence)


def test_authentication_negation_not_treated_as_requirement(evidence):
    evidence[0]["items"][1]["umm"]["AccessConstraints"][
        "Description"
    ] = "Earthdata users need not be logged in"
    with pytest.raises(ValueError):
        run(evidence)


def test_duplicate_json_keys_rejected(evidence):
    c, g, a = evidence
    raw = json.dumps(c).replace(
        '"Version": "002"', '"Version": "002", "Version": "002"'
    )
    with pytest.raises(ValueError):
        summarize(raw.encode(), json.dumps(g).encode(), a.encode())


def test_multiple_atom_entries_rejected(evidence):
    c, g, a = evidence
    entry = a[a.index("<entry>") : a.index("</entry>") + len("</entry>")]
    with pytest.raises(ValueError):
        run((c, g, a.replace("</feed>", entry + "</feed>")))


def test_entities_rejected(evidence):
    c, g, a = evidence
    with pytest.raises(ValueError):
        run((c, g, '<!DOCTYPE feed [<!ENTITY x "84.37">]>' + a.replace("84.37", "&x;")))


def test_cli_readback_and_input_preservation(evidence, tmp_path):
    args = []
    bodies = [json.dumps(evidence[0]), json.dumps(evidence[1]), evidence[2]]
    for name, body in zip(("collections", "granules", "atom"), bodies):
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        args.extend(["--" + name, str(path)])
    output = tmp_path / "summary.json"
    main(args + ["--out", str(output)])
    first = output.read_bytes()
    main(args + ["--out", str(output)])
    assert first == output.read_bytes()
    assert json.loads(first) == run(evidence)
    assert all(
        source["retrieval_status"] == "UNVERIFIED"
        for source in json.loads(first)["sources"].values()
    )
    with pytest.raises(SystemExit) as error:
        main(args + ["--out", str(tmp_path / "collections")])
    assert error.value.code == 2
    assert (tmp_path / "collections").read_text(encoding="utf-8") == bodies[0]


@pytest.mark.parametrize("input_name", ["collections", "granules", "atom"])
def test_cli_rejects_hard_link_to_each_input(evidence, tmp_path, input_name):
    args = []
    paths = {}
    bodies = [
        json.dumps(evidence[0]).encode(),
        json.dumps(evidence[1]).encode(),
        evidence[2].encode(),
    ]
    for name, body in zip(("collections", "granules", "atom"), bodies):
        path = tmp_path / name
        path.write_bytes(body)
        paths[name] = path
        args.extend(["--" + name, str(path)])
    output = tmp_path / "summary.json"
    output.hardlink_to(paths[input_name])
    original_stat = output.stat()

    with pytest.raises(SystemExit) as error:
        main(args + ["--out", str(output)])

    assert error.value.code == 2
    assert all(path.read_bytes() == body for path, body in zip(paths.values(), bodies))
    assert output.read_bytes() == paths[input_name].read_bytes()
    assert output.samefile(paths[input_name])
    assert (output.stat().st_dev, output.stat().st_ino) == (
        original_stat.st_dev,
        original_stat.st_ino,
    )


@pytest.mark.parametrize(
    "revision",
    [
        "0000-01-01T00:00:00Z",
        "2026-00-01T00:00:00Z",
        "2026-13-01T00:00:00Z",
        "2026-99-01T00:00:00Z",
        "2026-01-00T00:00:00Z",
        "2026-01-32T00:00:00Z",
        "2026-02-29T00:00:00Z",
        "2026-02-30T00:00:00Z",
        "2024-02-30T00:00:00Z",
        "1900-02-29T00:00:00Z",
        "2100-02-29T00:00:00Z",
        "2026-04-31T00:00:00Z",
        "2026-06-31T00:00:00Z",
        "2026-09-31T00:00:00Z",
        "2026-11-31T00:00:00Z",
        "2026-12-32T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T25:00:00Z",
        "2026-01-01T99:00:00Z",
        "2026-01-01T00:60:00Z",
        "2026-01-01T00:99:00Z",
        "2026-01-01T00:00:60Z",
        "2026-01-01T00:00:99Z",
        "2026-99-99T99:99:99Z",
        "2026-02-29T23:59:59.123Z",
        "2026-04-31T23:59:59.1Z",
        "2026-01-01T24:00:00.000Z",
        "2026-01-01T23:60:00.123456789Z",
        "2026-01-01T23:59:60.1Z",
        "0000-12-31T23:59:59.999Z",
    ],
)
@pytest.mark.parametrize("target", ["selected", "historical", "granule"])
def test_invalid_calendar_revision_rejected(evidence, revision, target):
    meta = {
        "selected": evidence[0]["items"][1]["meta"],
        "historical": evidence[0]["items"][0]["meta"],
        "granule": evidence[1]["items"][0]["meta"],
    }[target]
    meta["revision-date"] = revision
    with pytest.raises(
        ValueError, match="invalid or inconsistent ATL24 metadata evidence"
    ):
        run(evidence)


@pytest.mark.parametrize(
    "revision",
    [
        "0001-01-01T00:00:00Z",
        "2000-02-29T23:59:59.1Z",
        "2024-02-29T00:00:00.000001Z",
        "9999-12-31T23:59:59.12345678901234567890Z",
    ],
)
def test_valid_revision_boundaries_keep_precision(evidence, revision):
    for item in evidence[0]["items"] + evidence[1]["items"]:
        item["meta"]["revision-date"] = revision
    result = run(evidence)
    assert result["collection"]["revision"] == revision
    assert result["historical_collections"][0]["revision"] == revision
    assert result["sample"]["revision"] == revision


@pytest.mark.parametrize(
    "declaration",
    [
        "<!DOCTYPE feed>",
        '<!ENTITY size "84.37">',
        '<!DOCTYPE feed [<!ENTITY small "84.37"><!ENTITY large "&small;&small;">'
        '<!ENTITY size "&large;&large;">]>',
        '<!DOCTYPE feed [<!ENTITY size SYSTEM "https://example.invalid/entity">]>',
    ],
)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16-be"])
def test_xml_declarations_rejected(evidence, declaration, encoding, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("XML parser attempted network access")

    monkeypatch.setattr(socket, "socket", forbidden)
    document = evidence[2]
    if "<!ENTITY" in declaration:
        document = document.replace(">84.37<", ">&size;<")
    raw = (declaration + document).encode(encoding)
    with pytest.raises(
        ValueError, match="invalid or inconsistent ATL24 metadata evidence"
    ):
        summarize(
            json.dumps(evidence[0]).encode(), json.dumps(evidence[1]).encode(), raw
        )


def test_normal_xml_with_comment_and_cdata(evidence):
    c, g, a = evidence
    normal = '<?xml version="1.0"?>' + a.replace(
        "<entry>", "<!-- public discovery metadata --><entry>"
    ).replace(">84.37<", "><![CDATA[84.37]]><")
    result = run((c, g, normal))
    assert result["sample"]["advertised_size"] == {
        "value": "84.37",
        "unit": "MB",
        "source": "atom",
    }
