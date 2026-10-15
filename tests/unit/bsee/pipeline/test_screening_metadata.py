"""Screening inventories do not imply qualified engineering inputs."""


def test_manifest_declares_partial_readiness_and_unverified_freshness(tmp_path):
    from worldenergydata.bsee.pipeline_screening_io import write_artifacts

    rows = [{"segment_id": "synthetic", "segment_id_source": "DERIVED:synthetic"}]
    revision = {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-15",
                "changed": "Initial issue",
                "why": "Synthetic test",
            }
        ],
    }
    manifest = write_artifacts(
        rows, tmp_path / "out", revision, repository_root=tmp_path / "repository"
    )
    assert manifest["readiness_status"] == "partial"
    assert manifest["intended_use"] == "screening_inventory_only"
    assert manifest["source_freshness"]["state"] == "unverified"
