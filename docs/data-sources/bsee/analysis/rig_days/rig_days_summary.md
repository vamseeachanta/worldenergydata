## Communications

### 2025-06-02

Vamsee thanks for the update, I have been wrestling with ChatGPT (and my lack of programming knowledge) but currently are in the process of developing these scripts.  The mv_war_main_prop_remark.txt file appears to have the information we need to determine total completion days on the well.  I have attached several scripts and the results.  This is still a work in progress but you can take a look and see what I am trying to do.

If you look at the remarks parsed file, each sn_war number appears to correspond to 1 week +/- of ops and the text summarized the entire week. You can see that the dates are consecutive and there are gaps and restarts, but the total number of days would be the total number of days of completion – i.e. ops after td date. So the drilling days are the days from spud to td and everything else is completion.  This should make it simpler for our purposes and is all we really need. I still need to verify that prop_remark.txt file does not include any drilling, so I need to qc it on multiple wells.

These scripts were done on Stones, what I am trying to now is move over to Julia and see if I can consolidate them into “One Big Beautiful Script” LOL!

If you guys have any suggestions let me know.   I am plodding along in between daily stuff 😊

Roy.

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

---

*Last updated: 2025-07-24*
