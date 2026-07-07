"""Spain CORES crude density/API conversion registry tests (#807)."""

import json
from importlib.resources import files

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
    path.write_text(
        json.dumps(
            {
                "registry_version": "test",
                "registry_date": "2026-07-06",
                "factors": entries,
            }
        )
    )


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


def test_density_registry_rejects_legacy_list_payload(tmp_path):
    path = tmp_path / "density.json"
    path.write_text(json.dumps([_factor().__dict__]), encoding="utf-8")

    with pytest.raises(ValueError, match="registry_version"):
        load_crude_density_factors(path)


def test_density_registry_requires_root_metadata(tmp_path):
    path = tmp_path / "density.json"
    path.write_text(json.dumps({"factors": [_factor().__dict__]}), encoding="utf-8")

    with pytest.raises(ValueError, match="registry_version"):
        load_crude_density_factors(path)

    path.write_text(
        json.dumps({"registry_version": "test", "factors": [_factor().__dict__]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="registry_date"):
        load_crude_density_factors(path)


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


def test_default_density_registry_accepts_cited_source_fields():
    factors = load_crude_density_factors()
    casablanca_tarraco_url = (
        "https://www.boe.es/boe/dias/1977/07/14/pdfs/A15865-15866.pdf"
    )
    amposta_url = "https://www.boe.es/boe/dias/1976/05/21/pdfs/A09838-09839.pdf"
    dorada_url = "https://www.boe.es/boe/dias/1978/06/26/pdfs/A15132-15132.pdf"
    montanazo_lubina_url = "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2012-6772"
    boqueron_rodaballo_url = "https://doi.org/10.1016/j.fuel.2004.06.027"
    salmonete_url = "https://doi.org/10.1016/0146-6380(86)90044-6"

    amposta = factors["amposta"]
    assert amposta.field_name == "Amposta"
    assert amposta.source_class == "regulator_record"
    assert amposta.source_url == amposta_url
    assert amposta.accepted_for_conversion is True
    assert amposta.api_gravity_deg == pytest.approx(17.0)
    assert amposta.bbl_per_tonne == pytest.approx(6.600967486990584)

    casablanca = factors["casablanca"]
    assert casablanca.field_name == "Casablanca"
    assert casablanca.source_class == "regulator_record"
    assert casablanca.source_url == casablanca_tarraco_url
    assert casablanca.accepted_for_conversion is True
    assert casablanca.api_gravity_deg == pytest.approx(33.0)
    assert casablanca.bbl_per_tonne == pytest.approx(7.312182839124249)

    boqueron = factors["boqueron"]
    assert boqueron.field_name == "Boquerón"
    assert boqueron.source_class == "technical_literature"
    assert boqueron.source_url == boqueron_rodaballo_url
    assert boqueron.accepted_for_conversion is True
    assert boqueron.api_gravity_deg == pytest.approx(38.7)
    assert boqueron.bbl_per_tonne == pytest.approx(7.565553308321867)

    dorada = factors["dorada"]
    assert dorada.field_name == "Dorada"
    assert dorada.source_class == "regulator_record"
    assert dorada.source_url == dorada_url
    assert dorada.accepted_for_conversion is True
    assert dorada.api_gravity_deg == pytest.approx(21.3)
    assert dorada.bbl_per_tonne == pytest.approx(6.792106612876507)

    montanazo_lubina = factors["montanazolubina"]
    assert montanazo_lubina.field_name == "Montanazo-Lubina"
    assert montanazo_lubina.source_class == "regulator_record"
    assert montanazo_lubina.source_url == montanazo_lubina_url
    assert montanazo_lubina.accepted_for_conversion is True
    assert montanazo_lubina.api_gravity_min_deg == pytest.approx(30.81)
    assert montanazo_lubina.api_gravity_max_deg == pytest.approx(33.33)
    expected_combined_factor = (1.2 + 2.9) / (
        (1.2 / bbl_per_tonne_from_api(30.81)) + (2.9 / bbl_per_tonne_from_api(33.33))
    )
    assert montanazo_lubina.api_gravity_deg == pytest.approx(32.584375993836886)
    assert montanazo_lubina.bbl_per_tonne == pytest.approx(expected_combined_factor)
    assert bbl_per_tonne_from_api(montanazo_lubina.api_gravity_deg) == pytest.approx(
        expected_combined_factor
    )
    assert "montanazo" not in factors
    assert "lubina" not in factors
    with pytest.raises(CoresDensityCoverageError, match="Montanazo"):
        build_oil_conversion_audit(
            ["Montanazo"],
            factors,
            allow_default_density=False,
        )
    with pytest.raises(CoresDensityCoverageError, match="Lubina"):
        build_oil_conversion_audit(
            ["Lubina"],
            factors,
            allow_default_density=False,
        )

    rodaballo = factors["rodaballo"]
    assert rodaballo.field_name == "Rodaballo"
    assert rodaballo.source_class == "technical_literature"
    assert rodaballo.source_url == boqueron_rodaballo_url
    assert rodaballo.accepted_for_conversion is True
    assert rodaballo.api_gravity_deg == pytest.approx(41.3)
    assert rodaballo.bbl_per_tonne == pytest.approx(7.681125803043588)

    salmonete = factors["salmonete"]
    assert salmonete.field_name == "Salmonete"
    assert salmonete.source_class == "technical_literature"
    assert salmonete.source_url == salmonete_url
    assert salmonete.accepted_for_conversion is True
    assert salmonete.api_gravity_deg == pytest.approx(44.9)
    assert salmonete.bbl_per_tonne == pytest.approx(7.841149257273662)

    tarraco = factors["tarraco"]
    assert tarraco.field_name == "Tarraco"
    assert tarraco.source_class == "regulator_record"
    assert tarraco.source_url == casablanca_tarraco_url
    assert tarraco.accepted_for_conversion is True
    assert tarraco.api_gravity_deg == pytest.approx(35.0)
    assert tarraco.bbl_per_tonne == pytest.approx(7.401084758140957)

    audit = build_oil_conversion_audit(
        [
            "Amposta",
            "Boquerón",
            "Casablanca",
            "Dorada",
            "Montanazo-Lubina",
            "Rodaballo",
            "Salmonete",
            "Tarraco",
        ],
        factors,
        allow_default_density=False,
    )

    assert audit.used_field_names == (
        "Amposta",
        "Boquerón",
        "Casablanca",
        "Dorada",
        "Montanazo-Lubina",
        "Rodaballo",
        "Salmonete",
        "Tarraco",
    )
    assert audit.defaulted_fields == ()
    assert audit.missing_fields == ()


def test_default_density_registry_keeps_current_fields_missing():
    registry_path = files("worldenergydata.spain").joinpath(
        "data/cores/crude_density_factors.json"
    )
    payload = json.loads(registry_path.read_text())
    expected_fields = payload["source_gap_fields"]
    assert expected_fields == [
        "Albatros",
        "Ayoluengo",
        "Gaviota",
        "Viura (1)",
    ]

    with pytest.raises(CoresDensityCoverageError) as exc_info:
        build_oil_conversion_audit(
            expected_fields,
            load_crude_density_factors(),
            allow_default_density=False,
        )
    message = str(exc_info.value)
    for field_name in expected_fields:
        assert field_name in message


def test_default_density_registry_partially_covers_current_cores_fields():
    registry_path = files("worldenergydata.spain").joinpath(
        "data/cores/crude_density_factors.json"
    )
    payload = json.loads(registry_path.read_text())
    current_fields = [
        "Albatros",
        "Amposta",
        "Ayoluengo",
        "Boquerón",
        "Casablanca",
        "Dorada",
        "Gaviota",
        "Montanazo-Lubina",
        "Rodaballo",
        "Salmonete",
        "Tarraco",
        "Viura (1)",
    ]
    expected_gap_fields = [
        "Albatros",
        "Ayoluengo",
        "Gaviota",
        "Viura (1)",
    ]
    expected_used_fields = [
        "Amposta",
        "Boquerón",
        "Casablanca",
        "Dorada",
        "Montanazo-Lubina",
        "Rodaballo",
        "Salmonete",
        "Tarraco",
    ]
    factors = load_crude_density_factors()

    assert payload["coverage_status"] == "missing"
    assert payload["source_gap_fields"] == expected_gap_fields
    assert sorted([*expected_gap_fields, *expected_used_fields]) == sorted(
        current_fields
    )

    with pytest.raises(CoresDensityCoverageError) as exc_info:
        build_oil_conversion_audit(
            current_fields,
            factors,
            allow_default_density=False,
        )
    message = str(exc_info.value)
    for field_name in expected_gap_fields:
        assert field_name in message
    assert "Amposta" not in message
    assert "Boquerón" not in message
    assert "Casablanca" not in message
    assert "Dorada" not in message
    assert "Montanazo-Lubina" not in message
    assert "Rodaballo" not in message
    assert "Salmonete" not in message
    assert "Tarraco" not in message

    defaulted_audit = build_oil_conversion_audit(
        current_fields,
        factors,
        allow_default_density=True,
    )

    assert defaulted_audit.used_field_names == tuple(expected_used_fields)
    assert defaulted_audit.defaulted_fields == tuple(expected_gap_fields)
    assert defaulted_audit.missing_fields == ()


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
