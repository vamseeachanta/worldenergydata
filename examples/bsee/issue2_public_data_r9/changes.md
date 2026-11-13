# Revision 9 changes

Owner comments received 13 November 2026 on revision 8. Each comment is quoted
as received; the line below it says where revision 9 applies it.

## Comment 1 (takeaway)

> Can we add a deck hand? graphic. with logo so it is memorable? This should be consistent. and attractive. pulling. across. various articles.
>
> Use the Deckhand graphic. plus Gulf of Mexico or Gulf of America. map. or something much more insightful. Also add hashtags where replicable.

- Deckhand graphic: a marked slot, `id="deckhand-opening"`, sits above the
  title. The shared opening graphic (hand and mooring rope, with the Deckhand
  logo) is being made once for every edition and goes in this slot; this page
  draws no graphic or logo of its own.
- Map: Figure 1 in section 1 maps the surface location of every original Gulf
  of Mexico borehole spudded in 2005 to 2009 (1,584 wells) and in 2021 to 2025
  (246 wells), coloured by water-depth band, on a Natural Earth land outline
  labelled "Gulf of America (Gulf of Mexico)". The first observation bullet
  gives the shift: 68.8 % of the earlier wells were in less than 100 m of water
  against 13.4 % of the later ones; 500 m or more rose from 23.3 % to 82.5 %.
- Hashtags: one line after the sign-off, before the appendices.

## Comment 2 (Figure 1 caption, revision 8)

> Keep Figure title brief. and use footnotes. That means convert additional information to footpaths. Same trend for every figure or table.

Every figure and table now has a title of at most ten words. Scope, method
notes, source with file and retrieval dates, and the data file move to numbered
notes under the title. The pattern is the same for Figures 1 to 6, Table 1 and
Table B1.

## Comment 3 (pie captions, revision 8)

> For charts like these. we need to revisit. how we are going to show things. You know, if notes are common, then yeah, somehow show the common foot nodes and common titles. and following that the years Etcetera. So yeah, figure something out.

Each pie set is one figure: Figure 3 (rig type) and Figure 5 (water depth).
Each has one title, one shared legend and one block of notes; only the year is
above each pie. The notes give the three yearly totals once. Shares of 5 % or
more are printed in the slice; smaller shares are listed under the pie, so no
label overlaps and none is lost.

## Comments 4, 5 and 6 (Figure 2, pies 2a to 2c, Figure 3 captions, revision 8)

> See my figure title comment above
>
> See my figure title comment about
>
> see comments. about above.

Applied as comment 2 to the water-depth bar chart (now Figure 4), the depth
pies (now Figure 5) and the day chart (now Figure 6).

## Comment 7 (Figure 3 image, revision 8)

> Make the charts interactive possible. Also, let us. follow the life cycle of a bell while providing these individual charts. which means start with drilling than completion, then intervention, then temporary appointment and permanent apartment. Yeah, review the. I would like you to review, though.

- Interactive: every chart is interactive with a static image fallback. The
  map has period buttons and depth-band legend toggles; bar charts and pies
  have hover values and legend toggles; each day chart has hover values
  (median, quartiles and count, in days).
- Life of a well: section 3 is now "Days from drilling to abandonment".
  Figure 6 gives five individual charts in the order drilling, completion,
  intervention, temporary abandonment and permanent abandonment. The
  observations, counting rules, Table B1 and the reusable prompt follow the
  same order.
- Review: requested from a second provider after push; not reviewed by the
  author.

## Data choices

- Counts in Figures 2 to 5 and Table 1 are unchanged from revision 8 (APD file
  of 2 November 2026, retrieved 3 November 2026).
- Day statistics are unchanged from revision 8 (APM and borehole files of
  12 November 2026, retrieved 13 November 2026); only their order changes.
- The map uses the same pinned borehole file as section 3: region G,
  original-hole suffix ST00BP00, status other than CNL, by spud year, at
  `SURF_LATITUDE` and `SURF_LONGITUDE`. All 1,830 selected wells have
  coordinates in the map area (`data/map-selection.csv`).
- New source: Natural Earth 1:50m land, version 5.1.2 (public domain), pinned
  to commit f1890d9f of natural-earth-vector and by SHA-256 in
  `inputs/source-pins.json`. It draws the land outline only.

## Review-gate round 1 fixes

- File dates (12 November 2026 for the APM, borehole and APD column-check
  files; 2 November 2026 for the counting APD file) are now read from the
  date stamps of each archive's data members, recorded in the new
  `file_date` column of `data/sources.csv` and placed on the page from there.
- `data/sources.csv` gives the APM file the role "Duration analysis"; only the
  borehole file feeds the map.
- Day-chart hover values use the same four-significant-figure text as Table B1
  (for example drilling Q3 115.2 d in 500 to 1,500 m).
- The Figure 1 counts note labels each band ("100 to 500 m: 126").
- The under-5 % list on the pies reads "Under 5%:", matching the slice labels.
- Left open: the sign-off date "3 November 2026" is the earlier approval and
  needs the reviewer's own update before publication; "10 wells whose first
  New Well permit gives no requested spud date" is carried from the published
  permit counter at commit f5af5b6d; the Appendix B selection list keeps the
  build's rule names.

## Review-gate round 2 fixes

Second-provider review of 13 November 2026 at the previous head. Counts, day
statistics, figures and data files are unchanged; `data/sources.csv` changes
only in the role of the chart library. Changes a reader can see:

- Conversion source: section 2.2 now reads "1 ft = 0.3048 m exactly" and links
  NIST SP 811, Appendix B.8; the Appendix A conversion rule cites the same
  source.
- Chart library: the page loads Plotly 2.35.2 from its release address with an
  integrity check instead of embedding it, so the page is 1,016,299 bytes
  instead of 5,573,727. Without network access, or if the check fails, each
  chart shows its static image. The Appendix A software line says so.
- Pies (Figures 3 and 5): a legend click no longer hides a slice, so the shares
  in the slices, the under-5 % lists and the hover text always refer to the
  year total.
- Map (Figure 1): depth bands hidden or isolated through the legend stay so
  when the period buttons switch between 2005 to 2009 and 2021 to 2025.
- Appendix A code link: `build_r9.py` at the full SHA of the commit that holds
  the script, as before; the commit is new.
- `data/sources.csv`: the Plotly role reads "Chart library" (was "Offline
  chart library").
- Revision 8 page: the same conversion citation, software line, chart library
  loading, pie legend behaviour and code link change; 718,849 bytes instead of
  5,277,002. Its counts and figures are unchanged.

Not visible on the page: downloads accept HTTPS only, including redirects; the
build requires `--build-commit` as a full 40-character SHA; `--bundle PATH`
writes an offline interactive copy outside the example folder; both READMEs
give the rebuild commands with `--build-commit`, and the revision 8 README no
longer mentions a Table 2.
