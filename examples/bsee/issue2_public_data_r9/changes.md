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
