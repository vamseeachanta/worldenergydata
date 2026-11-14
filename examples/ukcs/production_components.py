"""Offline example of source-supported UKCS condensate extraction.

Inputs are synthetic monthly volumes, not measured production. NSTA PPRS
layer 0 identifies GCONDVOL in m3. NIST SP 811 Appendix B.8 (web edition
2016), petroleum-barrel entry, supports the shared rounded 6.2898 bbl/m3
factor: 10 m3 * 6.2898 = 62.898 bbl, displayed as 62.9 bbl.
An unknown second month makes the observed-month annual total unknown.
"""

import pandas as pd

from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader


def main():
    """Print inputs, the conversion method, monthly answers and annual totals."""
    raw = pd.DataFrame(
        {
            "FIELDNAME": ["EXAMPLE", "EXAMPLE"],
            "PERIODYR": [2024, 2024],
            "PERIODMNTH": [1, 2],
            "GCONDVOL": [10.0, None],
        }
    )
    loader = UKCSFieldProductionLoader()
    monthly = loader.load(raw)
    annual = loader.annual_aggregate(monthly)
    print("Synthetic inputs (GCONDVOL in m3):")
    print(raw.to_string(index=False))
    print("Method: condensate_bbl = GCONDVOL * shared m3-to-bbl factor.")
    print("Monthly answer (bbl):")
    columns = ["field", "year", "month", "condensate_bbl", "ngl_bbl"]
    print(monthly[columns].to_string(index=False, float_format="{:.1f}".format))
    print("Observed-month annual totals (bbl; missing values remain NaN):")
    print(
        annual[["field", "year", "condensate_bbl", "ngl_bbl"]].to_string(
            index=False, float_format="{:.1f}".format
        )
    )


if __name__ == "__main__":
    main()
