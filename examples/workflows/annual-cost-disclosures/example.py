"""Print the cited annual observations and derive project-only exact links."""

from worldenergydata.cost.data_collection import (
    disclosure_row_is_linkable,
    load_operator_disclosures_dataset,
    resolve_cost_datapoint_link,
)


def main() -> None:
    records = load_operator_disclosures_dataset()
    print("scope | fiscal year | reported metric | as-reported amount")
    for record in records:
        print(
            f"{record.scope.value} | {record.fiscal_year} | "
            f"{record.metric_name_reported} | "
            f"{record.amount} {record.currency} {record.unit}"
        )
    for record in records:
        if disclosure_row_is_linkable(record.scope.value):
            result = resolve_cost_datapoint_link(record.operator, record.project_name)
            print(f"project linkage: {result.status.value}")
        else:
            print("operator linkage: ineligible")


if __name__ == "__main__":
    main()
