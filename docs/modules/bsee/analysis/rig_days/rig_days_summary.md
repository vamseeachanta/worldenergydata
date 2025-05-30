## Summary and Way Forward

- Rig Days by War
{"COM": 87, "DRL": 151, "PND": 49, "TA": 21}

- Rig Days by Milestone
{"drilling_days": 156, "completion_days": ?, "rig_days": 156}

### Drilling Days

Drilling_days = (td_date - spud_date) + 1

### Completion Days

Looking at your notes, we can mix and match. If so, we came up with 3 methods as follows
method 1: Completion days = COM + PND + TA
Method 2: Take the maximum of all WAR_END_DT and do the following:
 completion days = max(WAR_END_DT) - min(WAR_START_DT) - drilling_days (or)
method 3: Completion days = max(WAR_END_DT) - td_date + 1 (MOST PREFERRED Method)

Please let us know which method (or a better method) for calculating completion days?

## Rig By WAR

[by WAR count](rig_days_by_WAR.md)

## Rig By Milestone

[by Milestone](rig_days_by_milestone.md)