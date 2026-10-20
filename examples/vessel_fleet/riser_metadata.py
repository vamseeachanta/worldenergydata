"""Show catalog inputs and the derived buoyancy OD ratio; no clearance check."""

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)


def catalog_example() -> dict[str, float]:
    """Use packaged CSV record RJ-21-75-BUOY, also tabulated in issue #1138.

    Independent arithmetic: buoyancy OD / bare main-tube OD = 49/21 = 7/3.
    These are catalog observations, not certified equipment dimensions.
    """
    joint = next(
        entry
        for entry in DrillingRiserLoader().get_riser_joint_entries()
        if entry.component_id == "RJ-21-75-BUOY"
    )
    ratio = joint.buoyancy_od_ratio
    if ratio is None:
        raise ValueError(
            "The worked example requires both diameters and buoyancy coverage"
        )
    return {
        "bare_od_in": joint.od_in,
        "buoyancy_od_in": joint.buoyancy_od_in,
        "buoyancy_od_ratio": ratio,
    }


if __name__ == "__main__":
    for name, value in catalog_example().items():
        print(f"{name}: {value:.1f}")
