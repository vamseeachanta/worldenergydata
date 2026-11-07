# Run it yourself: Gulf of Mexico new-well permits by rig type

Article: https://www.aceengineer.com/newsletter/issue-002-public-data/

For decision makers: this prompt lets your team, or your AI assistant, recount the permits from the public BSEE file. If you would rather have it done for you, or extended to other BSEE files, use the contact link on the article page.

For practitioners: paste the block below into an AI assistant that can run Python and use the internet. It needs git and Python 3.10 or later, and no other package. The key results it must reach are in `results.json` next to this file. `eval.py` grades them.

## Prompt (copy all of it)

```text
Task: recount the new-well permits by rig type in US federal waters of the Gulf of
Mexico, 2005 to 2026, and redraw Table 1 and Figure 1 of the article "Gulf of
Mexico well permits by rig type: a public US data file"
(https://www.aceengineer.com/newsletter/issue-002-public-data/).

Inputs (all public, no account needed):
- BSEE Application for Permit to Drill raw data, US federal government data,
  updated daily: https://www.data.bsee.gov/Well/Files/APDRawData.zip
  (the article counts the file of 2 November 2026).
- BSEE Incident Investigations raw data, also read by the script:
  https://www.data.bsee.gov/Other/Files/IncInvRawData.zip
- Counting script: https://github.com/vamseeachanta/worldenergydata at commit
  f5af5b6da87710bb395552f9cda5e34d1f324479,
  examples/bsee/rawdata_fact_check/count_rawdata.py. Its README gives the rule.
- Published Figure 1 data:
  https://www.aceengineer.com/assets/data/newsletter/issue-002/fig-p1-new-well-permits-by-rig-type.csv

Counting rule: count each well once, at its first New Well permit in the Gulf of
Mexico region, in the year of its requested spud date, with the rig type that
permit names. Rig types: jack-up, drillship, semisubmersible, DP semisubmersible,
platform rig, submersible; barge, barge rig and well intervention vessel are
grouped as other.

Steps:
1. git clone --filter=blob:none https://github.com/vamseeachanta/worldenergydata
   cd worldenergydata
   git fetch origin f5af5b6da87710bb395552f9cda5e34d1f324479 || git fetch origin refs/pull/1844/head
   git checkout f5af5b6da87710bb395552f9cda5e34d1f324479
   (The repository is large; the blobless clone downloads only what you check out.
   The pinned commit is the head of pull request 1844; GitHub keeps that ref after
   the branch is deleted, so the second fetch works if the first one does not.)
   Use Python 3.10 or later. No package install is needed.
2. python examples/bsee/rawdata_fact_check/count_rawdata.py --self-test
3. python examples/bsee/rawdata_fact_check/count_rawdata.py --out bsee-out --last-year 2026
   It downloads the BSEE files and prints the counts as JSON.
4. Build Table 1 (permits, median, shallowest and deepest water depth for each rig
   type) and compare every cell of 2005 to 2025 with the published Figure 1 CSV.

Expected key results (from the article):
- 2,895 permits: jack-up 1,333, drillship 758, semisubmersible 282, DP
  semisubmersible 260, platform rig 162, submersible 81, other 19.
- Median water depth (ft): 101, 5,187, 3,233, 5,263.5, 392, 40, 12.
- 2005: 234 of 322 permits named a jack-up and 15 a drillship. 2025: 44 of 47
  named a drillship and 1 a jack-up.
- Figure 1: no cell of 2005 to 2025 differs from the published CSV.
The BSEE file changes daily. If your counts differ by a few permits, report the
difference and the SHA-256 of the file you used; it is not an error.

Ask me before you go on if:
- the download from data.bsee.gov fails: ask me to download both files in a
  browser, https://www.data.bsee.gov/Well/Files/APDRawData.zip and
  https://www.data.bsee.gov/Other/Files/IncInvRawData.zip (the script reads both,
  although the permit counts use only the first), put them in one folder, and pass
  that folder with --data-dir;
- you want to extend the count: ask me which years, which rig types and which BSEE
  region I want.

You cannot:
- say which rig actually drilled each well: the file names the rig type of the
  permit only;
- rebuild the exact file of 2 November 2026: BSEE does not keep daily copies.

Output: Table 1, a redrawn Figure 1 (permits per year by rig type, stacked bars),
and a file my-results.json in this form, with the result ids of
https://github.com/vamseeachanta/worldenergydata/blob/main/examples/report-evals/issue-002-gom-well-permits/results.json
{"results": [{"id": "permits_all_2005_2026", "value": 2895}, ...]}
Then grade it. The eval files are on the main branch, so bring them into the clone:
git checkout origin/main -- examples/report-evals
python examples/report-evals/issue-002-gom-well-permits/eval.py --compare my-results.json
```

## Check your answer

From the clone at the pinned commit, after `git checkout origin/main -- examples/report-evals`:

```text
python examples/report-evals/issue-002-gom-well-permits/eval.py --compare my-results.json
python examples/report-evals/issue-002-gom-well-permits/eval.py
```

The first line grades your own results. The second reads the counting script from the pinned commit, runs it on today's files and compares every key result itself; add `--data-dir FOLDER` if you saved the two BSEE files by hand. `DRIFT` on a count means today's BSEE file differs from the file the article counted.

## Adapt it to your project

`count_rawdata.py` takes `--first-year` and `--last-year`. The same rule applies to any year range. For a different question, such as permits by operator or by water depth band, keep the one-permit-per-well rule and state it beside the count.
