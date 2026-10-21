"""Repeated sparse country conversion preserves supplied source evidence.

These adapters return FieldConcept, not enriched metadata dictionaries. The
measured-origin statement therefore travels in their existing data_source
field. Depth 12 is a synthetic identity-transform sentinel: 12 m stays 12 m.
No engineering thresholds or physical qualification are asserted here.
"""

import copy

import pytest

from worldenergydata.brazil_anp.field_concept import build_brazil_field_concept
from worldenergydata.canada.field_concept import canada_field_to_concept
from worldenergydata.sodir.field_concept import sodir_field_to_concept
from worldenergydata.spain.field_concept import spain_field_to_concept
from worldenergydata.ukcs.field_concept import ukcs_field_to_concept


@pytest.mark.parametrize(
    "convert",
    [
        build_brazil_field_concept,
        canada_field_to_concept,
        sodir_field_to_concept,
        spain_field_to_concept,
        ukcs_field_to_concept,
    ],
)
def test_supplied_measurement_and_source_survive_repeated_conversion(convert):
    """Hand calculation: supplied depth wins unchanged; no fallback is needed.

    Converting the same dict twice must produce equal models and leave the dict
    untouched. This is not a claim that arbitrary metadata origins are mapped.
    """
    meta = {
        "field_name": "synthetic",
        "water_depth_m": 12,
        "source": "synthetic; water_depth_m=measured",
        "value_origins": {"water_depth_m": "measured"},
    }
    before = copy.deepcopy(meta)
    first = convert(meta)
    assert first.water_depth_m == 12
    assert first.data_source == meta["source"]
    assert convert(meta) == first
    assert meta == before
