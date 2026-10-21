"""Reject storage inventory as an annual-throughput capacity basis."""

import pytest

from worldenergydata.lng_terminals.collectors.gie_collector import GIECollector


@pytest.mark.parametrize("inventory", ["267.84", 267.84, None])
def test_storage_inventory_is_not_throughput_capacity(inventory):
    """GIE API User Manual v007 (4 October 2022), section 2.4, page 8.

    https://www.gie.eu/transparency-platform/GIE_API_documentation_v007.pdf

    The published dtmi example is 267.84 in thousand cubic metres of LNG.
    Dimensional check: a volume cannot determine mass/time without density and
    a time basis, neither of which is supplied. Expected capacity_mtpa is None.
    String and numeric encodings must give the same missing-throughput result;
    absent inventory is the control. Terminal identity must still be retained.
    """
    record = {"name": "Synthetic Terminal", "country": "GBR"}
    if inventory is not None:
        record["dtmi"] = inventory
    with GIECollector() as collector:
        terminals = collector.parse_records([record])
    assert [terminal.terminal_name for terminal in terminals] == ["Synthetic Terminal"]
    assert terminals[0].capacity_mtpa is None
