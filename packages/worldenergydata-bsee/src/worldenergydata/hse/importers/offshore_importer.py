"""Offline, transactional intake of reviewed public metadata and paraphrases.

No downloader runs during import. Source terms and access checks precede curation.
SQLite constraints make repeat intake idempotent; existing datasets are linked,
never copied into the source-neutral event table.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from worldenergydata.hse.offshore import (
    Event,
    ReviewReceipt,
    SourceDocument,
    check_contacts,
    check_privacy,
)


def normalise(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def day(value):
    return date.fromisoformat(str(value)[:10])


def match(left, right):
    if (
        left["country"] != right["country"]
        or abs((day(left["event_date"]) - day(right["event_date"])).days) > 2
    ):
        return None
    if right.get("module") == "hse" and left["country"] == "US":
        left_blocks = {
            normalise(v) for v in re.split(r"[;,]", left.get("block_or_lease") or "")
        } - {""}
        right_blocks = {
            normalise(v) for v in re.split(r"[;,]", right.get("block_or_lease") or "")
        } - {""}
        if (
            day(left["event_date"]) == day(right["event_date"])
            and left_blocks & right_blocks
        ):
            return "bsee_date_block"
    left_names = {
        normalise(left["installation_name"]),
        *(normalise(v) for v in left.get("installation_aliases", [])),
    } - {""}
    right_names = {
        normalise(right["installation_name"]),
        *(normalise(v) for v in right.get("installation_aliases", [])),
    } - {""}
    return "installation_date_country" if left_names & right_names else None


def validate_identity(row, *, with_module=False):
    """Reject contact data and internal fields before an index reaches storage.

    Exporters must review names in authoritative identity exports separately;
    this structural/contact check does not recognize arbitrary personal names.
    """
    check_contacts(row)
    required = {"record_id", "event_date", "country", "installation_name"}
    allowed = required | {"installation_aliases", "block_or_lease"}
    if with_module:
        required.add("module")
        allowed.add("module")
        if row.get("module") not in {"hse", "marine_safety"}:
            raise ValueError("existing identity module is unsupported")
    if (
        not required <= set(row)
        or set(row) - allowed
        or not isinstance(row["record_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]*", row["record_id"])
        or not isinstance(row["country"], str)
        or not re.fullmatch(r"[A-Z]{2}", row["country"])
        or not isinstance(row["installation_name"], str)
        or not isinstance(row.get("installation_aliases", []), list)
        or any(not isinstance(v, str) for v in row.get("installation_aliases", []))
        or (
            row.get("block_or_lease") is not None
            and not isinstance(row["block_or_lease"], str)
        )
    ):
        raise ValueError("existing index has invalid identity fields")
    date.fromisoformat(row["event_date"])


def merge_identity(canonical, *identities):
    """Keep the canonical date/location while retaining reviewed name aliases."""
    result = {
        key: canonical[key]
        for key in (
            "event_date",
            "country",
            "installation_name",
            "installation_aliases",
            "block_or_lease",
        )
    }
    names = set(result["installation_aliases"])
    for identity in identities:
        names.add(identity["installation_name"])
        names.update(identity.get("installation_aliases", []))
    result["installation_aliases"] = sorted(names - {result["installation_name"], ""})
    return result


class OffshoreImporter:
    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS external_links(
                    event_id TEXT NOT NULL, module TEXT NOT NULL, record_id TEXT NOT NULL,
                    identity TEXT NOT NULL,
                    UNIQUE(module,record_id));
                CREATE TABLE IF NOT EXISTS sources(
                    source TEXT NOT NULL, source_ref TEXT NOT NULL, event_id TEXT NOT NULL,
                    payload TEXT NOT NULL, UNIQUE(source,source_ref));
                CREATE TABLE IF NOT EXISTS dedup_log(
                    id INTEGER PRIMARY KEY, incoming_id TEXT, matched_id TEXT,
                    rule TEXT NOT NULL, score REAL NOT NULL, disposition TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS gates(name TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.database)

    def ingest(self, packet, *, existing=(), stage="pilot"):
        if stage not in {"pilot", "candidate"}:
            raise ValueError("intake stage must be pilot or candidate")
        existing = list(existing)
        for row in existing:
            validate_identity(row, with_module=True)
        check_privacy(
            {"events": packet["events"], "sources": packet["sources"]},
            packet["reviewed_text"],
        )
        events = [
            Event.model_validate(row).model_dump(mode="json")
            for row in packet["events"]
        ]
        sources = [
            SourceDocument.model_validate(row).model_dump(mode="json")
            for row in packet["sources"]
        ]
        ids = {row["event_id"] for row in events}
        if len(ids) != len(events) or ids != {row["event_id"] for row in sources}:
            raise ValueError(
                "event IDs must be unique and every event must have source evidence"
            )
        stats = dict(events_added=0, sources_added=0, linked_existing=0)
        with self.connect() as db:
            before_digest = self.content_digest(db)
            if (
                stage == "candidate"
                and not db.execute("SELECT 1 FROM gates WHERE name='pilot'").fetchone()
            ):
                raise ValueError(
                    "independent pilot review must precede candidate bulk intake"
                )
            stored = [
                json.loads(row[0]) for row in db.execute("SELECT payload FROM events")
            ]
            links = [
                dict(json.loads(r[3]), event_id=r[0], module=r[1], record_id=r[2])
                for r in db.execute("SELECT * FROM external_links")
            ]
            indexed = {(r["module"], r["record_id"]): r for r in [*existing, *links]}
            for row in events:
                incoming_id = row["event_id"]
                collision = next(
                    (s for s in stored if s["event_id"] == incoming_id), None
                )
                if collision and {
                    k: v for k, v in collision.items() if k != "installation_aliases"
                } != {k: v for k, v in row.items() if k != "installation_aliases"}:
                    raise ValueError("conflicting event ID")
                candidates = [
                    (candidate, match(row, candidate))
                    for candidate in [*stored, *indexed.values()]
                ]
                candidates = [
                    (candidate, rule) for candidate, rule in candidates if rule
                ]
                target_ids = {
                    c.get("event_id", f"{c.get('module')}:{c.get('record_id')}")
                    for c, _ in candidates
                }
                if len(target_ids) > 1:
                    raise ValueError("ambiguous event match; explicit review required")
                if candidates:
                    target, rule = candidates[0]
                    if target.get("module"):
                        linked = db.execute(
                            "SELECT event_id,identity FROM external_links WHERE module=? AND record_id=?",
                            (target["module"], target["record_id"]),
                        ).fetchone()
                        target_id = linked[0] if linked else incoming_id
                        count = db.execute(
                            "SELECT count(*) FROM (SELECT event_id FROM events UNION SELECT event_id FROM external_links)"
                        ).fetchone()[0]
                        if stage == "pilot" and count and not linked:
                            raise ValueError(
                                "pilot intake is limited to one canonical event"
                            )
                        identity = merge_identity(
                            json.loads(linked[1]) if linked else row, row, target
                        )
                        db.execute(
                            "INSERT INTO external_links VALUES (?,?,?,?) "
                            "ON CONFLICT(module,record_id) DO UPDATE SET identity=excluded.identity",
                            (
                                target_id,
                                target["module"],
                                target["record_id"],
                                json.dumps(identity, sort_keys=True),
                            ),
                        )
                        # Later rows in this packet must see reviewed aliases
                        # from identities linked earlier in the transaction.
                        indexed[(target["module"], target["record_id"])] = dict(
                            identity,
                            event_id=target_id,
                            module=target["module"],
                            record_id=target["record_id"],
                        )
                        stats["linked_existing"] += int(not linked)
                    else:
                        target_id = target["event_id"]
                        identity = merge_identity(target, row)
                        if (
                            target["installation_aliases"]
                            != identity["installation_aliases"]
                        ):
                            target["installation_aliases"] = identity[
                                "installation_aliases"
                            ]
                            db.execute(
                                "UPDATE events SET payload=? WHERE event_id=?",
                                (json.dumps(target, sort_keys=True), target_id),
                            )
                    db.execute(
                        "INSERT INTO dedup_log VALUES(NULL,?,?,?,?,?)",
                        (
                            incoming_id,
                            f"{target['module']}:{target['record_id']}"
                            if target.get("module")
                            else target_id,
                            rule,
                            1.0,
                            "linked",
                        ),
                    )
                else:
                    if db.execute(
                        "SELECT 1 FROM external_links WHERE event_id=?", (incoming_id,)
                    ).fetchone():
                        raise ValueError("conflicting event ID")
                    count = db.execute(
                        "SELECT count(*) FROM (SELECT event_id FROM events UNION SELECT event_id FROM external_links)"
                    ).fetchone()[0]
                    if stage == "pilot" and count:
                        raise ValueError(
                            "pilot intake is limited to one event; review it before candidate bulk intake"
                        )
                    target_id = incoming_id
                    db.execute(
                        "INSERT INTO events VALUES (?,?)",
                        (target_id, json.dumps(row, sort_keys=True)),
                    )
                    stored.append(row)
                    stats["events_added"] += 1
                for source in (s for s in sources if s["event_id"] == incoming_id):
                    source = dict(source, event_id=target_id)
                    old = db.execute(
                        "SELECT event_id,payload FROM sources WHERE source=? AND source_ref=?",
                        (source["source"], source["source_ref"]),
                    ).fetchone()
                    if old:
                        if old[0] != target_id or json.loads(old[1]) != source:
                            raise ValueError(
                                "conflicting source reference; explicit review required"
                            )
                        db.execute(
                            "INSERT INTO dedup_log VALUES(NULL,?,?,?,?,?)",
                            (
                                f"{source['source']}:{source['source_ref']}",
                                f"{source['source']}:{source['source_ref']}",
                                "source_ref",
                                1.0,
                                "duplicate skipped",
                            ),
                        )
                    else:
                        gate = db.execute(
                            "SELECT payload FROM gates WHERE name='pilot'"
                        ).fetchone()
                        if gate and json.loads(gate[0])["pilot_event_id"] == target_id:
                            if stage == "candidate":
                                raise ValueError(
                                    "pilot evidence changed; renew pilot review separately"
                                )
                            db.execute("DELETE FROM gates WHERE name='pilot'")
                        db.execute(
                            "INSERT INTO sources VALUES (?,?,?,?)",
                            (
                                source["source"],
                                source["source_ref"],
                                target_id,
                                json.dumps(source, sort_keys=True),
                            ),
                        )
                        stats["sources_added"] += 1
            # Any change invalidates a prior bulk acceptance receipt.
            if before_digest != self.content_digest(db):
                db.execute(
                    "DELETE FROM gates WHERE name IN ('bulk','existing_indexes')"
                )
        return stats

    def content_digest(self, db=None):
        """Hash the canonical evidence tables, excluding mutable audit/gate rows."""
        if db is None:
            with self.connect() as connection:
                return self.content_digest(connection)
        payload = {
            "events": db.execute(
                "SELECT event_id,payload FROM events ORDER BY event_id"
            ).fetchall(),
            "sources": db.execute(
                "SELECT source,source_ref,event_id,payload FROM sources ORDER BY source,source_ref"
            ).fetchall(),
            "external_links": db.execute(
                "SELECT * FROM external_links ORDER BY module,record_id"
            ).fetchall(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _review(self, db, review):
        receipt = ReviewReceipt.model_validate(review).model_dump(mode="json")
        if receipt["dataset_sha256"] != self.content_digest(db):
            raise ValueError("review digest does not match current evidence")
        ids = {
            r[0]
            for r in db.execute(
                "SELECT event_id FROM events UNION SELECT event_id FROM external_links"
            )
        }
        if not set(receipt["reviewed_event_ids"]) <= ids:
            raise ValueError("review contains unknown event IDs")
        return receipt

    def approve_pilot(self, event_id, review):
        with self.connect() as db:
            count = db.execute(
                "SELECT count(DISTINCT source) FROM sources WHERE event_id=? "
                "AND json_extract(payload, '$.access_status')='public'",
                (event_id,),
            ).fetchone()[0]
            if (
                count < 3
                or review.get("verdict") != "pass"
                or event_id not in review.get("reviewed_event_ids", [])
            ):
                raise ValueError(
                    "pilot gate requires three public sources and independent source review"
                )
            review = self._review(db, review)
            db.execute(
                "INSERT OR REPLACE INTO gates VALUES('pilot',?)",
                (json.dumps({"pilot_event_id": event_id, "review": review}),),
            )

    @staticmethod
    def _index_evidence(indexes):
        if set(indexes) != {"hse", "marine_safety"}:
            raise ValueError("complete hse and marine_safety index coverage required")
        evidence = {}
        for module, index in indexes.items():
            if (
                set(index) != {"complete", "records"}
                or index["complete"] is not True
                or not isinstance(index["records"], list)
            ):
                raise ValueError("complete existing index coverage required")
            seen = set()
            for row in index["records"]:
                validate_identity(row)
                if row["record_id"] in seen:
                    raise ValueError("existing index has invalid or duplicate identity")
                seen.add(row["record_id"])
            data = json.dumps(index, sort_keys=True).encode()
            evidence[module] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "record_count": len(index["records"]),
                "complete": True,
            }
        return evidence

    def reconcile_existing(self, indexes):
        """Consume complete identity-only exports and replace copies with links.

        The operator must attest the exports are complete, including BSEE
        investigation rows and marine USCG/MAIB/NTSB records. This method checks
        the actual supplied rows, and records their digests and checked content.
        It cannot establish the authenticity of an operator's completeness claim.
        """
        evidence = self._index_evidence(indexes)
        with self.connect() as db:
            events = [
                json.loads(r[0]) for r in db.execute("SELECT payload FROM events")
            ]
            identities = {r["event_id"]: r for r in events}
            for event_id, identity in db.execute(
                "SELECT event_id,identity FROM external_links"
            ):
                identities.setdefault(
                    event_id, dict(json.loads(identity), event_id=event_id)
                )
            events = list(identities.values())
            for row in events:
                for module, index in indexes.items():
                    matches = [
                        (r, match(row, dict(r, module=module)))
                        for r in index["records"]
                    ]
                    matches = [(r, rule) for r, rule in matches if rule]
                    if len(matches) > 1:
                        raise ValueError(
                            "ambiguous existing event match; explicit review required"
                        )
                    for target, rule in matches:
                        old = db.execute(
                            "SELECT event_id,identity FROM external_links WHERE module=? AND record_id=?",
                            (module, target["record_id"]),
                        ).fetchone()
                        if old and old[0] != row["event_id"]:
                            raise ValueError(
                                "ambiguous existing event link; explicit review required"
                            )
                        identity = merge_identity(
                            json.loads(old[1]) if old else row, row, target
                        )
                        db.execute(
                            "INSERT INTO external_links VALUES(?,?,?,?) "
                            "ON CONFLICT(module,record_id) DO UPDATE SET identity=excluded.identity",
                            (
                                row["event_id"],
                                module,
                                target["record_id"],
                                json.dumps(identity, sort_keys=True),
                            ),
                        )
                        db.execute(
                            "DELETE FROM events WHERE event_id=?", (row["event_id"],)
                        )
                        if not old:
                            db.execute(
                                "INSERT INTO dedup_log VALUES(NULL,?,?,?,?,?)",
                                (
                                    row["event_id"],
                                    f"{module}:{target['record_id']}",
                                    rule,
                                    1.0,
                                    "linked existing dataset",
                                ),
                            )
            # Reconciliation checks every original canonical event before
            # replacing it; already linked identities are checked on repeat.
            for event_id, module, record_id, identity in db.execute(
                "SELECT * FROM external_links"
            ):
                target = next(
                    (
                        r
                        for r in indexes[module]["records"]
                        if r["record_id"] == record_id
                    ),
                    None,
                )
                if not target or not match(
                    json.loads(identity), dict(target, module=module)
                ):
                    raise ValueError("existing link absent from complete index")
            db.execute("DELETE FROM gates WHERE name='bulk'")
            receipt = {"dataset_sha256": self.content_digest(db), "indexes": evidence}
            db.execute(
                "INSERT OR REPLACE INTO gates VALUES('existing_indexes',?)",
                (json.dumps(receipt),),
            )
        return receipt

    def approve_bulk(self, review, existing_indexes):
        """Accept only 50+ events, independent 10% review and both existing indexes.

        Index coverage is supplied by the operator exporting authoritative datasets;
        an absent database must never be represented by an empty complete index.
        """
        with self.connect() as db:
            review = self._review(db, review)
            ids = {
                row[0]
                for row in db.execute(
                    "SELECT event_id FROM events UNION SELECT event_id FROM external_links"
                )
            }
            if not db.execute("SELECT 1 FROM gates WHERE name='pilot'").fetchone():
                raise ValueError("pilot review must precede bulk admission")
            if (
                len(ids) < 50
                or review.get("verdict") != "pass"
                or len(ids & set(review.get("reviewed_event_ids", [])))
                < (len(ids) + 9) // 10
            ):
                raise ValueError(
                    "bulk gate requires 50 events and independent review of at least 10%"
                )
            evidence = self._index_evidence(existing_indexes)
            checked = db.execute(
                "SELECT payload FROM gates WHERE name='existing_indexes'"
            ).fetchone()
            if not checked or json.loads(checked[0]) != {
                "dataset_sha256": self.content_digest(db),
                "indexes": evidence,
            }:
                raise ValueError(
                    "existing indexes must be consumed against current evidence before acceptance"
                )
            db.execute(
                "INSERT OR REPLACE INTO gates VALUES('bulk',?)",
                (json.dumps({"review": review, "existing_coverage": evidence}),),
            )

    def export(self, destination):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": 1,
            "event_count": 0,
            "source_count": 0,
            "bulk_admitted": False,
            "sha256": {},
        }
        with self.connect() as db:
            tables = {
                "events": [
                    json.loads(r[0])
                    for r in db.execute("SELECT payload FROM events ORDER BY event_id")
                ],
                "sources": [
                    dict(
                        json.loads(r[0]),
                        citation=SourceDocument.model_validate_json(r[0]).citation,
                    )
                    for r in db.execute(
                        "SELECT payload FROM sources ORDER BY source,source_ref"
                    )
                ],
                "external_links": [
                    dict(
                        event_id=r[0],
                        module=r[1],
                        record_id=r[2],
                        identity=json.loads(r[3]),
                    )
                    for r in db.execute(
                        "SELECT * FROM external_links ORDER BY event_id,module,record_id"
                    )
                ],
                "dedup_log": [
                    dict(
                        zip(
                            (
                                "id",
                                "incoming_id",
                                "matched_id",
                                "rule",
                                "score",
                                "disposition",
                            ),
                            r,
                        )
                    )
                    for r in db.execute("SELECT * FROM dedup_log ORDER BY id")
                ],
                "gates": {
                    r[0]: json.loads(r[1])
                    for r in db.execute("SELECT name,payload FROM gates ORDER BY name")
                },
            }
            manifest.update(
                event_count=len(tables["events"]),
                source_count=len(tables["sources"]),
                linked_existing_count=len(tables["external_links"]),
                bulk_admitted="bulk" in tables["gates"],
            )
            manifest.update(
                dataset_sha256=self.content_digest(db),
                digest_format="canonical-sqlite-evidence-v1",
            )
            outputs = {}
            for name, payload in tables.items():
                filename = name + ".json"
                data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
                outputs[filename] = data
                manifest["sha256"][filename] = hashlib.sha256(data).hexdigest()
            outputs["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
            # Preflight every output before writing any bytes.
            for filename, data in outputs.items():
                path = destination / filename
                if path.exists() and path.read_bytes() != data:
                    raise FileExistsError("export changed; choose a new destination")
            for filename, data in outputs.items():
                path = destination / filename
                path.write_bytes(data)
                if path.read_bytes() != data:
                    raise OSError("export readback differs")
        return manifest
