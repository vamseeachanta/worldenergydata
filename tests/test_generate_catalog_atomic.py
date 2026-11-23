from __future__ import annotations

import pytest

from scripts import generate_catalog


def test_atomic_yaml_write_preserves_existing_file_on_dump_failure(
    tmp_path, monkeypatch
):
    target = tmp_path / "schema.yaml"
    target.write_text("module: existing\n", encoding="utf-8")

    def fail_dump(*args, **kwargs):
        raise RuntimeError("dump failed")

    monkeypatch.setattr(generate_catalog.yaml, "dump", fail_dump)

    with pytest.raises(RuntimeError, match="dump failed"):
        generate_catalog._write_yaml_atomic(target, {"module": "replacement"})

    assert target.read_text(encoding="utf-8") == "module: existing\n"
    assert sorted(tmp_path.iterdir()) == [target]
