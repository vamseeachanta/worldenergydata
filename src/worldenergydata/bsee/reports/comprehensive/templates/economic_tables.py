"""
Economic table generation for comprehensive financial reports
Contains HTML table generation functions for sensitivity analysis
"""

from typing import Any, Dict, List

import numpy as np
import numpy_financial as npf


def generate_sensitivity_analysis_tables(
    economic_context: Dict[str, Any],
) -> Dict[str, str]:
    """
    Generate HTML tables for sensitivity analysis showing NPV and IRR variations

    Args:
        economic_context: Dictionary containing economic parameters

    Returns:
        Dictionary containing HTML tables for different sensitivity scenarios
    """
    if not economic_context:
        return {
            "error": "<p>No economic context available for sensitivity analysis tables</p>"
        }

    tables = {}

    # Oil price sensitivity table
    oil_price_scenarios = [50, 60, 70, 80, 90, 100]  # $/bbl
    gas_price_base = economic_context.get("gas_price", 3.50)

    oil_sensitivity_data = []
    for oil_price in oil_price_scenarios:
        # Recalculate economics with new oil price
        temp_context = economic_context.copy()
        temp_context["oil_price"] = oil_price

        # Simplified NPV calculation for sensitivity
        annual_oil_revenue = temp_context.get("annual_oil_bbl", 100000) * oil_price
        annual_gas_revenue = temp_context.get("annual_gas_mcf", 500000) * gas_price_base
        annual_revenue = annual_oil_revenue + annual_gas_revenue
        annual_costs = temp_context.get("operating_costs", 2500000)
        annual_net_cash = annual_revenue - annual_costs

        # 10-year cash flow projection
        cash_flows = [
            -temp_context.get("initial_capex", 10000000)
        ]  # Initial investment
        for year in range(10):
            decline_factor = (1 - temp_context.get("decline_rate", 0.08)) ** year
            cash_flows.append(annual_net_cash * decline_factor)

        # Calculate NPV and IRR
        npv_10 = npf.npv(0.10, cash_flows)
        npv_15 = npf.npv(0.15, cash_flows)

        try:
            irr = npf.irr(cash_flows)
            irr_percent = f"{irr:.1%}" if not np.isnan(irr) else "N/A"
        except:
            irr_percent = "N/A"

        oil_sensitivity_data.append(
            {
                "oil_price": oil_price,
                "npv_10": npv_10,
                "npv_15": npv_15,
                "irr": irr_percent,
            }
        )

    # Generate oil price sensitivity HTML table
    oil_table_html = """
    <table class="sensitivity-table" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <caption style="font-weight: bold; margin-bottom: 10px;">Oil Price Sensitivity Analysis</caption>
        <thead>
            <tr style="background-color: #f0f0f0;">
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">Oil Price ($/bbl)</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 10%</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 15%</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">IRR</th>
            </tr>
        </thead>
        <tbody>
    """

    for row in oil_sensitivity_data:
        npv_10_color = "green" if row["npv_10"] > 0 else "red"
        npv_15_color = "green" if row["npv_15"] > 0 else "red"

        oil_table_html += f"""
            <tr>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">${row['oil_price']}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_10_color};">${row['npv_10']:,.0f}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_15_color};">${row['npv_15']:,.0f}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{row['irr']}</td>
            </tr>
        """

    oil_table_html += """
        </tbody>
    </table>
    """

    tables["oil_price_sensitivity"] = oil_table_html

    # Gas price sensitivity table
    gas_price_scenarios = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5]  # $/mcf
    oil_price_base = economic_context.get("oil_price", 75.0)

    gas_sensitivity_data = []
    for gas_price in gas_price_scenarios:
        # Recalculate economics with new gas price
        temp_context = economic_context.copy()
        temp_context["gas_price"] = gas_price

        # Simplified NPV calculation for sensitivity
        annual_oil_revenue = temp_context.get("annual_oil_bbl", 100000) * oil_price_base
        annual_gas_revenue = temp_context.get("annual_gas_mcf", 500000) * gas_price
        annual_revenue = annual_oil_revenue + annual_gas_revenue
        annual_costs = temp_context.get("operating_costs", 2500000)
        annual_net_cash = annual_revenue - annual_costs

        # 10-year cash flow projection
        cash_flows = [-temp_context.get("initial_capex", 10000000)]
        for year in range(10):
            decline_factor = (1 - temp_context.get("decline_rate", 0.08)) ** year
            cash_flows.append(annual_net_cash * decline_factor)

        # Calculate NPV
        npv_10 = npf.npv(0.10, cash_flows)
        npv_15 = npf.npv(0.15, cash_flows)

        try:
            irr = npf.irr(cash_flows)
            irr_percent = f"{irr:.1%}" if not np.isnan(irr) else "N/A"
        except:
            irr_percent = "N/A"

        gas_sensitivity_data.append(
            {
                "gas_price": gas_price,
                "npv_10": npv_10,
                "npv_15": npv_15,
                "irr": irr_percent,
            }
        )

    # Generate gas price sensitivity HTML table
    gas_table_html = """
    <table class="sensitivity-table" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <caption style="font-weight: bold; margin-bottom: 10px;">Gas Price Sensitivity Analysis</caption>
        <thead>
            <tr style="background-color: #f0f0f0;">
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">Gas Price ($/mcf)</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 10%</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">NPV @ 15%</th>
                <th style="border: 1px solid #ccc; padding: 10px; text-align: center;">IRR</th>
            </tr>
        </thead>
        <tbody>
    """

    for row in gas_sensitivity_data:
        npv_10_color = "green" if row["npv_10"] > 0 else "red"
        npv_15_color = "green" if row["npv_15"] > 0 else "red"

        gas_table_html += f"""
            <tr>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">${row['gas_price']:.2f}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_10_color};">${row['npv_10']:,.0f}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_15_color};">${row['npv_15']:,.0f}</td>
                <td style="border: 1px solid #ccc; padding: 8px; text-align: center;">{row['irr']}</td>
            </tr>
        """

    gas_table_html += """
        </tbody>
    </table>
    """

    tables["gas_price_sensitivity"] = gas_table_html

    # Combined scenario analysis table (oil vs gas price matrix)
    oil_scenarios = [60, 75, 90]
    gas_scenarios = [2.5, 3.5, 4.5]

    matrix_table_html = """
    <table class="sensitivity-matrix" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
        <caption style="font-weight: bold; margin-bottom: 10px;">NPV Scenario Matrix (@ 10% Discount Rate)</caption>
        <thead>
            <tr style="background-color: #f0f0f0;">
                <th style="border: 1px solid #ccc; padding: 10px;">Oil Price / Gas Price</th>
    """

    for gas_price in gas_scenarios:
        matrix_table_html += f'<th style="border: 1px solid #ccc; padding: 10px; text-align: center;">${gas_price:.1f}/mcf</th>'

    matrix_table_html += """
            </tr>
        </thead>
        <tbody>
    """

    for oil_price in oil_scenarios:
        matrix_table_html += f"""
            <tr>
                <td style="border: 1px solid #ccc; padding: 8px; font-weight: bold; background-color: #f8f8f8;">${oil_price}/bbl</td>
        """

        for gas_price in gas_scenarios:
            # Calculate NPV for this combination
            annual_oil_revenue = (
                economic_context.get("annual_oil_bbl", 100000) * oil_price
            )
            annual_gas_revenue = (
                economic_context.get("annual_gas_mcf", 500000) * gas_price
            )
            annual_revenue = annual_oil_revenue + annual_gas_revenue
            annual_costs = economic_context.get("operating_costs", 2500000)
            annual_net_cash = annual_revenue - annual_costs

            # 10-year cash flow projection
            cash_flows = [-economic_context.get("initial_capex", 10000000)]
            for year in range(10):
                decline_factor = (
                    1 - economic_context.get("decline_rate", 0.08)
                ) ** year
                cash_flows.append(annual_net_cash * decline_factor)

            npv = npf.npv(0.10, cash_flows)
            npv_color = "green" if npv > 0 else "red"

            matrix_table_html += f"""
                <td style="border: 1px solid #ccc; padding: 8px; text-align: right; color: {npv_color};">${npv:,.0f}</td>
            """

        matrix_table_html += "</tr>"

    matrix_table_html += """
        </tbody>
    </table>
    """

    tables["scenario_matrix"] = matrix_table_html

    return tables
