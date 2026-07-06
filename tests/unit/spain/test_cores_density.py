"""Spain CORES crude density/API conversion registry tests (#807)."""

import json

import pytest

from worldenergydata.spain.production.cores_density import (
    CoresCrudeDensityFactor,
    CoresDensityCoverageError,
    CoresOilConversionAudit,
    bbl_per_tonne_from_api,
    build_oil_conversion_audit,
    load_crude_density_factors,
)


def _factor(**overrides):
    values = {
        "field_name": "Ayoluengo",
        "aliases": ("ayoluengo",),
        "api_gravity_deg": 30.0,
        "api_gravity_min_deg": None,
        "api_gravity_max_deg": None,
        "bbl_per_tonne": bbl_per_tonne_from_api(30.0),
        "measurement_basis": "representative produced stream",
        "source_title": "Example technical literature",
        "source_url": "https://example.test/ayoluengo-assay",
        "source_class": "technical_literature",
        "evidence_note": "Representative field-applicable conversion basis.",
        "confidence": "medium",
        "accepted_for_conversion": True,
    }
    values.update(overrides)
    return CoresCrudeDensityFactor(**values)


def _write_registry(path, entries):
    path.write_text(json.dumps({"registry_version": "test", "factors": entries}))


def test_bbl_per_tonne_from_api_matches_reference_formula():
    assert bbl_per_tonne_from_api(36.0) == pytest.approx(7.44554, rel=1e-5)
    assert bbl_per_tonne_from_api(20.0) == pytest.approx(6.73432, rel=1e-5)


def test_density_registry_requires_citation_fields(tmp_path):
    path = tmp_path / "density.json"
    entry = _factor().__dict__
    entry.pop("source_url")
    _write_registry(path, [entry])

    with pytest.raises(ValueError, match="source_url"):
        load_crude_density_factors(path)


def test_density_registry_accepts_legacy_list_payload(tmp_path):
    path = tmp_path / "density.json"
    path.write_text(json.dumps([_factor().__dict__]), encoding="utf-8")

    factors = load_crude_density_factors(path)

    assert factors["ayoluengo"].field_name == "Ayoluengo"


def test_density_registry_rejects_duplicate_aliases(tmp_path):
    path = tmp_path / "density.json"
    _write_registry(
        path,
        [
            _factor(field_name="Ayoluengo", aliases=("ayoluengo",)).__dict__,
            _factor(field_name="AYOLUENGO", aliases=("Ayo luengo",)).__dict__,
        ],
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_crude_density_factors(path)


def test_density_registry_rejects_non_representative_range_as_conversion_factor():
    with pytest.raises(ValueError, match="representative"):
        _factor(
            api_gravity_deg=None,
            api_gravity_min_deg=20.0,
            api_gravity_max_deg=39.0,
            bbl_per_tonne=7.1,
            measurement_basis="non-representative discovery-test range",
        )


def test_density_registry_normalizes_accents_and_punctuation(tmp_path):
    path = tmp_path / "density.json"
    _write_registry(
        path,
        [
            _factor(
                field_name="Boquerón",
                aliases=("boqueron", "Boquerón"),
            ).__dict__,
            _factor(
                field_name="Viura (1)",
                aliases=("viura 1", "Viura-1"),
            ).__dict__,
        ],
    )

    factors = load_crude_density_factors(path)

    assert factors["boqueron"].field_name == "Boquerón"
    assert factors["viura1"].field_name == "Viura (1)"


def test_density_registry_rejects_invalid_source_class_and_confidence():
    with pytest.raises(ValueError, match="source_class"):
        _factor(source_class="blog")
    with pytest.raises(ValueError, match="confidence"):
        _factor(confidence="certain")
    with pytest.raises(ValueError, match="accepted_for_conversion"):
        _factor(accepted_for_conversion="false")


def test_density_registry_rejects_string_boolean_flags(tmp_path):
    path = tmp_path / "density.json"
    entry = _factor().__dict__
    entry["accepted_for_conversion"] = "false"
    _write_registry(path, [entry])

    with pytest.raises(ValueError, match="accepted_for_conversion"):
        load_crude_density_factors(path)


def test_density_registry_requires_boolean_flag(tmp_path):
    path = tmp_path / "density.json"
    entry = _factor().__dict__
    del entry["accepted_for_conversion"]
    _write_registry(path, [entry])

    with pytest.raises(ValueError, match="accepted_for_conversion"):
        load_crude_density_factors(path)


def test_default_density_registry_file_loads_from_package_data():
    factors = load_crude_density_factors()

    assert isinstance(factors, dict)


def test_default_density_registry_keeps_current_fields_missing():
    with pytest.raises(CoresDensityCoverageError, match="Ayoluengo"):
        build_oil_conversion_audit(
            ["Ayoluengo", "Casablanca"],
            load_crude_density_factors(),
            allow_default_density=False,
        )


def test_crude_density_factor_rejects_secondary_article_conversion_directly(tmp_path):
    with pytest.raises(ValueError, match="source_class"):
        _factor(source_class="secondary_article", accepted_for_conversion=True)
    with pytest.raises(ValueError, match="representative"):
        _factor(
            api_gravity_deg=None,
            api_gravity_min_deg=20.0,
            api_gravity_max_deg=39.0,
            bbl_per_tonne=None,
            measurement_basis="non-representative field range only",
            accepted_for_conversion=True,
        )

    path = tmp_path / "density.json"
    entry = _factor().__dict__
    entry["source_class"] = "secondary_article"
    _write_registry(path, [entry])
    with pytest.raises(ValueError, match="source_class"):
        load_crude_density_factors(path)


def test_oil_conversion_audit_rejects_unbacked_conversion_entries():
    good = _factor()
    unaccepted = _factor(accepted_for_conversion=False, bbl_per_tonne=None)

    with pytest.raises(ValueError, match="accepted"):
        CoresOilConversionAudit(
            used_factors=(good,),
            defaulted_fields=(),
            missing_fields=(),
            _accepted_entries=(("ayoluengo", unaccepted),),
            _defaulted_field_keys=(),
        )
    with pytest.raises(ValueError, match="bbl_per_tonne"):
        CoresOilConversionAudit(
            used_factors=(_factor(bbl_per_tonne=None, accepted_for_conversion=False),),
            defaulted_fields=(),
            missing_fields=(),
            _accepted_entries=(),
            _defaulted_field_keys=(),
        )
    with pytest.raises(ValueError, match="duplicate"):
        CoresOilConversionAudit(
            used_factors=(good,),
            defaulted_fields=(),
            missing_fields=(),
            _accepted_entries=(("ayoluengo", good), ("ayoluengo", good)),
            _defaulted_field_keys=(),
        )
    with pytest.raises(ValueError, match="default"):
        CoresOilConversionAudit(
            used_factors=(good,),
            defaulted_fields=(),
            missing_fields=(),
            _accepted_entries=(("ayoluengo", good),),
            _defaulted_field_keys=("casablanca",),
        )


def test_oil_conversion_audit_names_defaulted_fields():
    audit = build_oil_conversion_audit(
        ["Ayoluengo", "Casablanca"],
        {"ayoluengo": _factor()},
        allow_default_density=True,
    )

    assert audit.defaulted_fields == ("Casablanca",)
    assert audit.missing_fields == ()
    assert audit.bbl_per_tonne_for_field("Casablanca") == pytest.approx(7.33)


def test_oil_conversion_audit_strict_mode_names_missing_fields():
    with pytest.raises(CoresDensityCoverageError, match="Casablanca"):
        build_oil_conversion_audit(
            ["Ayoluengo", "Casablanca"],
            {"ayoluengo": _factor()},
            allow_default_density=False,
        )


def test_oil_conversion_audit_rejects_non_boolean_default_opt_in():
    with pytest.raises(ValueError, match="allow_default_density"):
        build_oil_conversion_audit(
            ["Casablanca"],
            {},
            allow_default_density="false",
        )
