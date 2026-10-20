"""Worked offline recorder-feasibility example; no title documents are fetched."""

from worldenergydata.landman.recorder_coverage import load_catalog


def main():
    catalog = load_catalog()
    # Input: the bundled dated metadata, restricted to these candidate states.
    for record in catalog.priority_counties(states=["TX", "OK", "CO", "KS"]):
        # Method: access truth table, then a separate automation-rights decision.
        print(
            f"{record.state}/{record.county}: {record.classification}; "
            f"automation={record.automation_feasibility}; "
            f"title={record.title_chain_status}"
        )


if __name__ == "__main__":
    main()
