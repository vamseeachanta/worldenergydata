"""Brazil ANP FieldConcept mapping tests (#718)."""

import pandas as pd

from worldenergydata.brazil_anp.field_concept import (
    build_brazil_field_concept,
    build_brazil_field_meta,
)
from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.recommendation import recommend


def _fields_df():
    return pd.DataFrame(
        [
            {
                "CAMPO": "TUPI",
                "BACIA": "Santos",
                "OPERADOR": "Petrobras",
                "AMBIENTE": "Mar",
                "DATA_INICIO_PRODUCAO": "2010-10-28",
            }
        ]
    )


def _platforms_df():
    return pd.DataFrame(
        [
            {
                "[CAMPOS]": "TUPI;IRACEMA",
                "[BACIA]": "Santos",
                "[OPERADOR]": "Petrobras",
                "[LÂMINA D'ÁGUA (m)]": "2.150,5",
                "[CLASSIFICAÇÃO]": "FPSO",
            }
        ]
    )


def _wells_df():
    return pd.DataFrame(
        [
            {"Nome_poço_anp": "7-TUPI-1", "Campo": "TUPI", "Ambiente": "Mar"},
            {"Nome_poço_anp": "7-TUPI-2", "Campo": "TUPI", "Ambiente": "Mar"},
        ]
    )


def test_build_brazil_field_meta_from_official_header_shapes():
    meta = build_brazil_field_meta(
        fields_df=_fields_df(),
        platforms_df=_platforms_df(),
        wells_df=_wells_df(),
        field_name="TUPI",
    )

    assert meta["field_name"] == "TUPI"
    assert meta["operator"] == "Petrobras"
    assert meta["basin"] == "Santos"
    assert meta["environment"] == "Mar"
    assert meta["water_depth_m"] == 2150.5
    assert meta["well_count"] == 2
    assert meta["first_oil_date"] == "2010-10-28"
    assert meta["source"] == "anp_fase_desenvolvimento_producao"


def test_build_brazil_field_concept_uses_region_key_and_sparse_metadata():
    meta = build_brazil_field_meta(
        fields_df=_fields_df(),
        platforms_df=_platforms_df(),
        wells_df=_wells_df(),
        field_name="TUPI",
    )

    concept = build_brazil_field_concept(meta)

    assert concept.name == "TUPI"
    assert concept.operator == "Petrobras"
    assert concept.region == "brazil"
    assert concept.water_depth_m == 2150.5
    assert concept.num_wells == 2
    assert concept.year_first_oil == 2010
    assert concept.data_source == "anp_fase_desenvolvimento_producao"


def test_brazil_region_prior_favors_fpso_for_deepwater_field():
    concept = build_brazil_field_concept(
        build_brazil_field_meta(
            fields_df=_fields_df(),
            platforms_df=_platforms_df(),
            wells_df=_wells_df(),
            field_name="TUPI",
        )
    )

    ranked = recommend(concept)

    assert ranked[0].concept_type == ConceptType.FPSO
