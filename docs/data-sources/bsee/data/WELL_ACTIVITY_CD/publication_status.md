# WELL_ACTIVITY_CD: publication status

Checked: 2026-10-12. No published definition for this activity field was found
in the public sources opened below. This is a bounded search result, not proof
that no definition exists anywhere. In particular, PND has no published
definition in those sources; a proposed expansion is not a definition.

## Field and repository provenance

The raw table is `mv_war_main_prop`, carrying `WELL_ACTIVITY_CD` and the join
key `SN_WAR`. The repository's
[load_war_prop](../../../../modules/bsee/analysis/production/FDAS_V30/extract_drilling_completion_days.py#L158)
reads CSV or pickle input; lines 166-176 select the key and activity field and
require both columns. This establishes how the loader reads the field, not
what the regulator means by its values.

The observed tokens below come from the committed
[frequency file](../../../../../reports/lower_tertiary/data/war_activity_code_frequency.csv),
not a fresh raw-data download. Its blank and aggregate rows are not code values.
No tally or published result is recalculated here. The existing
[canonical vocabulary](../../../../../packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml)
records source table and data vintage in `meta`; its runtime labels are unchanged.

The Markdown heading, source-link and code-table layout follows the existing
[field description](well_activity_cd_description.md); the neighbouring
[API field note](../well_api_number.md) likewise uses a field-specific source link.

## Occurring codes and definition status

Every row has **no published definition found for WELL_ACTIVITY_CD**. The
right-hand column records only overlapping wording published by BSEE in the
[borehole status list](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields),
whose domain is `BOREHOLE_STAT_CDS` for `BOREHOLE_STAT_CD`. It belongs to a
**different field**. Transferring its meanings to activity codes is an inference.

| Code | WELL_ACTIVITY_CD status | Published in the different borehole status list |
| --- | --- | --- |
| `TA` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Temporarily Abandoned |
| `PA` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Permanently Abandoned |
| `DRL` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Drilling Active |
| `COM` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Borehole Completed |
| `WO` | no published definition found | no published definition found |
| `CHZ` | no published definition found | no published definition found |
| `PND` | no published definition found | no published definition found |
| `ST` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Borehole Side Tracked |
| `MPF` | no published definition found | no published definition found |
| `DSI` | no published definition found | Defined by BSEE in BOREHOLE_STAT_CDS as Drilling Suspended |
| `REC` | no published definition found | no published definition found |
| `TBK` | no published definition found | no published definition found |

Table: observed activity tokens and the separate published borehole domain.

## Public source ledger

All URLs below were opened on 2026-10-12 using Python urllib. PDF text was also
inspected through the public document reader. Titles identify the cited pages;
findings apply to the returned page or extracted text, not uninspected dynamic
panels, hidden form options or authenticated application help.

| Title and URL | Publisher | Finding in this pass |
| --- | --- | --- |
| [eWell WAR Online Query Field Definitions](https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx) | BSEE | Rendered field list runs from SN_WAR to BOTM_BLOCK_NUM; WELL_ACTIVITY_CD is absent. |
| [Borehole field definitions](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields) | BSEE | Publishes BOREHOLE_STAT_CDS and the overlapping phrases above; no PND entry. |
| [Form BSEE-0133, Well Activity Report](https://www.bsee.gov/sites/bsee.gov/files/form-0133-exp-2024.pdf) | BSEE | Item 10 has a STATUS column; extracted text contains no PND definition. |
| [NTL No. 2016-N07, Well Records Submittal](https://www.bsee.gov/sites/bsee.gov/files/notices-to-lessees-ntl/ntl-2016-n07-well-records-submittal-november-29-2016.pdf) | BSEE | Discusses WAR records and Item 10 dates; extracted text contains no PND definition. |
| [BSEE eWell and TIMS Web Application Manual](https://bsee.gov/sites/bsee.gov/files/bsee-policy-manual-section/ocs-operations/ewell-permitting-and-reporting-system-application-manual.pdf) | BSEE | Covers account access; extracted text contains no PND definition. |
| [eWell APM Online Query Field Definitions](https://www.data.bsee.gov/Well/eWellAPM/FieldDefinitions.aspx) | BSEE | Describes BOREHOLE_STAT_CD, a different field; no activity-code definition list is rendered. |
| [API List Well Completions Field Definitions](https://www.data.bsee.gov/Well/API/FieldDefinitions.aspx?page=wellcomps) | BSEE | Describes COMP_STATUS_CD, a different field; no activity-code definition list is rendered. |
| [Raw Data](https://www.data.bsee.gov/Main/RawData.aspx) | BSEE | Links eWell WAR raw data; the download archive was not opened or downloaded. |
| [eWell WAR Online Query](https://www.data.bsee.gov/Well/eWellWAR/Default.aspx) | BSEE | Returned query page does not expose WELL_ACTIVITY_CD as a definition list. |
| [Submitted Well Activity Report example](https://www.bsee.gov/sites/bsee.gov/files/reports/reports/2015-09-25-shell-gom-bsee-rsfo-war-bj-public.pdf) | BSEE, hosting a submitted report | Extracted form text has STATUS but no PND definition. No operational data is reproduced. |

Table: public sources successfully reopened, with bounded findings.

### Not verified

| Cited page | Publisher | Opened / attempted | Result |
| --- | --- | --- | --- |
| [Data Center Contact](https://www.data.bsee.gov/Main/Contact.aspx) | BSEE | 2026-10-12 | Redirected to the site's 404 error page. No contact information is asserted from it. |
| [30 CFR 250.743](https://www.ecfr.gov/current/title-30/section-250.743) | eCFR, Office of the Federal Register / Government Publishing Office | 2026-10-12 | Redirected to an access-block page. No regulatory-content claim is made from it. |

Table: cited pages whose substantive content could not be verified.

Dynamic Field Values panels, individual WAR viewer pages and authenticated
submission help were not inspected. The issue's archive-content and hidden
form-option findings were not reverified. A successful download of a page does
not establish those claims.

## Interpretation rule and enquiry

Codes without a published definition are shown as **bare codes** and labelled
**undefined**. Borehole wording may be cited only with its different-field
qualification; it does not validate a WAR interpretation. Legacy display labels
and operational groupings are not regulator definitions.

[Issue 1065](https://github.com/vamseeachanta/worldenergydata/issues/1065) warns
that ONRR OGOR-A production-reporting status codes reuse DRL, DSI and TA with
different meanings. That warning is attributed to the issue; the ONRR code
list was not independently verified in this pass. Do not transfer meanings
between these fields merely because their letters match.

The enquiry is **drafted on the issue, not sent as of 2026-10-12**. Both drafts
remain there; no reply is recorded. Sending the enquiry is an owner action.
Interim results with and without PND and a later reply or documented wait remain
separate work. This note neither chooses an operational basis nor changes results.
