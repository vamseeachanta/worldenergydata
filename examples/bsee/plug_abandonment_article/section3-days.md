# Days from drilling to abandonment

Section 3 of the Issue 2 public data article, revision 10 (commit 70c73f65), parked for the series'
plugging-and-abandonment article. Text as published in the revision 10 review copy; figure numbers are those of
revision 10. Charts: `days_charts.py` (static) and `days_charts.js` (interactive). Data: `data/days-summary.csv`
and `data/days-overview.csv`.

## 3.1 Observations

Some of the observations are as follows, in the order of a well's life:

- Drilling: recorded spud-to-total-depth medians rise with water depth, from 21 d under 100 m to 67 d at 1,500 m
  and deeper.
- Completion: estimate medians rise with water depth, from 10 d under 100 m to 40 d at 1,500 m and deeper.
- Intervention: estimate medians range from 7 to 22 d across the four depth bands.
- Temporary abandonment: estimate medians range from 5 to 14 d across the four depth bands.
- Permanent abandonment: estimate medians range from 7 to 20 d across the four depth bands.

## 3.2 Counting rules and exclusions

- Drilling days are the recorded dates from spud to total depth of each original borehole (borehole file).
- Days on completion, intervention and abandonment permits are the operator's estimate on each permit (APM file).
- Each original borehole or permit is counted once, for 2005 to 2025, in the same four water-depth bands.
- Missing, invalid, zero or negative days are left out and counted.
- The APD file holds no estimated drilling days.

The detailed rules and record counts are in `../issue2_public_data_r11/counting-rules.md`, section 4.

## 3.3 Days at each stage of a well's life

Figure 6 sets the median days of every stage side by side for the four water-depth bands. Panel a follows the
life of a well, stage by stage; panel b takes one water-depth band at a time, from the shelf to the deepest
water. Hover over a bar for its median and N.

Figure 6 notes:

1. Median: the middle value. Half of the records take fewer days and half take more.
2. N: the number of records behind a median, boreholes for drilling and permits to modify for the other stages.
   Records with missing, zero or negative days are not counted. Hover over a bar for its N; Figure 7 prints it
   beside each band.
3. Drilling is the recorded calendar interval from spud to total depth. The other stages are operator estimates
   on permits to modify. The stages come from different records and are not paired, so the medians are not added
   up.
4. The medians describe 2005 to 2025 as a whole. Quartiles are in Figure 7 and Table B1.
5. Sources: BSEE BoreholeRawData.zip, file of 12 November 2026, retrieved 13 November 2026, and
   eWellAPMRawData.zip, file of 12 November 2026, retrieved 13 November 2026.
6. Data: days-overview.csv.

Figure 6 - Median days of each stage, by water depth

Figure 7 gives each stage on its own, in the same order: the median and quartile days in the four water-depth
bands, with the median and N beside each band (a. drilling, recorded spud to total depth; b. completion,
c. intervention, d. temporary abandonment and e. permanent abandonment, each an operator estimate).

Figure 7 notes:

1. Median: the middle value. Half of the records take fewer days and half take more. Dots mark the medians.
2. N: the number of records behind the median, boreholes for drilling and permits to modify for the other
   stages. Records with missing, zero or negative days are not counted. ≈ marks a count rounded to four
   significant figures.
3. Bars run from the first to the third quartile: the middle half of the records.
4. Drilling is the recorded calendar interval from spud to total depth of original boreholes spudded from 2005
   to 2025. The other stages are operator estimates on permits to modify with status dates from 2005 to 2025.
5. Each chart has its own day scale.
6. Sources: as Figure 6.
7. Data: days-summary.csv; full counts in Table B1.

Figure 7 - Days at each stage of a well's life

## Open points carried with the section

- Figures 6 and 7 show recorded drilling intervals and operator estimates side by side; they come from different
  records and are not paired.
- The medians describe 2005 to 2025 as a whole.
