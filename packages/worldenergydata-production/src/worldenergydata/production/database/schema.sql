-- Database format version 1; no real production data is shipped.
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    version TEXT NOT NULL,
    locator TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    data_kind TEXT NOT NULL CHECK (data_kind IN ('reported', 'synthetic')),
    loaded INTEGER NOT NULL DEFAULT 0 CHECK (loaded IN (0, 1))
);
CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('field', 'facility', 'reservoir', 'aggregate'))
);
CREATE TABLE asset_links (
    field_id TEXT NOT NULL REFERENCES assets(asset_id),
    child_id TEXT NOT NULL REFERENCES assets(asset_id),
    PRIMARY KEY (field_id, child_id)
);
CREATE TABLE field_mappings (
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    PRIMARY KEY (source_id, external_id)
);
CREATE TABLE regulator_production (
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    period TEXT NOT NULL,
    region TEXT NOT NULL,
    external_id TEXT NOT NULL,
    source_label TEXT NOT NULL,
    oil_bbl REAL CHECK (oil_bbl >= 0),
    gas_mcf REAL CHECK (gas_mcf >= 0),
    water_bbl REAL CHECK (water_bbl >= 0),
    condensate_bbl REAL CHECK (condensate_bbl >= 0),
    PRIMARY KEY (snapshot_id, asset_id, period)
);
CREATE TABLE decline_curves (
    curve_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    model TEXT NOT NULL,
    qi REAL NOT NULL,
    di REAL NOT NULL,
    b REAL NOT NULL,
    rate_unit TEXT NOT NULL,
    origin_period TEXT NOT NULL,
    history_sha256 TEXT NOT NULL,
    method_ref TEXT NOT NULL,
    qualification TEXT NOT NULL CHECK (qualification = 'NOT_EVALUATED')
);
PRAGMA user_version = 1;
