# %% [markdown]
# # HSE query quickstart
#
# This runnable example uses the existing synthetic demonstration database.
# No record is an observation, and no regulatory acceptance limit is applied.
# The inputs are defined in hse.api.build_synthetic_session: three incidents,
# penalties of 5000, 15000 and 50000, and two annual statistics records.
# Selecting penalties >= 10000 gives 15000 + 50000 = 65000 by hand.
# The year selection uses incident dates, not penalty assessment dates.
#
# ## Revision history
#
# Revision 1, 2026-10-20: introduce a reproducible query and calculation example.

# %%
from worldenergydata.hse.api import (
    EpaTriQuery,
    IncidentsQuery,
    OshaQuery,
    PenaltiesQuery,
    StatisticsQuery,
    build_synthetic_session,
)


def main():
    """Print independently checkable answers for the labeled sample."""
    session = build_synthetic_session()
    engine = session.get_bind()
    try:
        incidents = IncidentsQuery(session).query(year=2022, severity="fatality")
        penalties = PenaltiesQuery(session).query(year=2022, min_amount=10000)
        statistics = StatisticsQuery(session).query(year=2022, metric="total_incidents")
        releases = EpaTriQuery(session).query(year=2022)
        osha = OshaQuery(session).query(year=2022)
        print("Data basis: synthetic demonstration; no observed results.")
        print(f"Selected fatal incidents: {len(incidents)}")
        print(f"Selected penalty sum: {penalties.penalty_amount.sum():.0f}")
        print(f"Stored incident count sum: {statistics.total_incidents.sum()}")
        print(f"TRI records: {len(releases)}; OSHA records: {len(osha)}")
    finally:
        session.close()
        engine.dispose()


# %% [markdown]
# ## Configured database
#
# ```python
# import os
# import worldenergydata as wed
#
# config = wed.hse_api.HSEQueryConfig(database_url=os.environ["HSE_DATABASE_URL"])
# with wed.hse_api.HSEApi(config) as client:
#     result = client.incidents.query(year=2024, source="bsee_inc")
#
# # The database package includes the asynchronous SQLite driver.
# async def query_async():
#     async with wed.hse_api.HSEApi(config) as client:
#         return await client.incidents.aquery(year=2024)
# ```
#
# Carcinogen classification and OSHA NAICS filtering raise NOT_EVALUATED
# because the persisted schema does not retain the required evidence.
# OSHA deduplication and database completeness remain separate ingest work.

# %%
if __name__ == "__main__":
    main()
