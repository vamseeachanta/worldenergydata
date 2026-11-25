"""Count wells reaching permanent or temporary abandonment in end-of-operations reports."""
import pandas as pd


def eligible_reports(raw, wells, audit, label):
    reports = audit.keep(label + " abandonment operation", raw, raw.EOR_OPERATION_CD.eq("A"))
    reports = reports.assign(well=reports.API_WELL_NUMBER.astype("string").str.slice(0, 10))
    return audit.keep(label + " on eligible Gulf well", reports, reports.well.isin(wells.well))


def report_year(dates):
    # The source uses US date-only values or a date with a time of day.
    token = dates.astype("string").str.strip().replace("", pd.NA).str.split().str[0]
    return pd.to_datetime(token, format="%m/%d/%Y").dt.year


def eor_counts(raw, wells, audit):
    """Count a Gulf well once per year and reached status, across all its bores."""
    reports = eligible_reports(raw, wells, audit, "EOR")
    reports = audit.keep("EOR reached PA or TA", reports, reports.BOREHOLE_STAT_CD.isin(["PA", "TA"]))
    reports = reports.assign(year=report_year(reports.BOREHOLE_STAT_DT), status=reports.BOREHOLE_STAT_CD)
    events = audit.keep("EOR with dated outcome", reports, reports.year.notna())[["well", "year", "status"]]
    return audit.keep("EOR unique well-year-status", events, ~events.duplicated())


def eor_diagnostics(raw, wells, events, audit):
    """Count reports reaching other statuses and test agreement with dated current PA wells."""
    reports = eligible_reports(raw, wells, audit, "EOR other-status cross-check")
    other = audit.keep("EOR reached another status", reports, ~reports.BOREHOLE_STAT_CD.isin(["PA", "TA"]))
    years = report_year(other.BOREHOLE_STAT_DT)
    omitted = audit.keep("EOR other-status reports in 2007–2025", other, years.between(2007, 2025))
    audit.diagnostics["eor_other_2007_2025"] = len(omitted)
    attained = audit.keep("EOR unique well-year reaching PA", events, events.status.eq("PA"))
    current = audit.keep("EOR coverage population with current PA", wells, wells.status.eq("PA"))
    population = current.assign(year=current.status_date.dt.year).merge(
        attained[["well", "year"]], on=["well", "year"], how="left", validate="one_to_one", indicator=True
    )
    for start, stop in [(2005, 2005), (2006, 2006), (2007, 2007), (2010, 2025)]:
        period = str(start) if start == stop else f"{start}_{stop}"
        rows = audit.keep("EOR coverage current PA " + period, population, population.year.between(start, stop))
        matched = audit.keep("EOR same-year PA match " + period, rows, rows["_merge"].eq("both"))
        audit.diagnostics["eor_coverage_" + period] = (len(matched), len(rows))
