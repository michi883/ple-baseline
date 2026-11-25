I've written the Item 051 memo on the house form and saved it as `/filesystem/Thelbridge_Verification_Memo_Item051_BlockC.docx`. It is from Rahul Nimkar to Adrian Vance, copied to Rachel Marlbeck. The disposition is **NOT VERIFIED**, and the item stays Open.

**Why it fails**
- **The settlement calc leaves out the clay.** In CB-GEO-007 Rev.0 (the Engineer of Record's Block C settlement calc), the consolidation sheet is marked "Not computed". The calc uses only short-term settlement (0.9 in) and concludes "SATISFACTORY". The geotechnical report (§9.1) requires the clay consolidation to be computed for each governing footing.
- **My check of the consolidation:** using the register's values (Cc 0.28, e₀ 0.92, σ′p 1,900 psf, 18 ft layer, 900 psf stress increase), the clay settles about 5.1 in (5.4 in by the report's formula). Adding the 0.9 in gives roughly 6 in, against the 1.0 in limit in Spec 31 20 00 Art. 3.6.A. That limit would only be met if the stress increase at mid-clay were under about 185 psf, a fifth of what the calc itself reports.
- **Differential settlement** is checked in the calc against a 1/500 limit. The spec's limit is 0.5 in over 30 ft (about 1/720). Adjacent footings are likely to differ by about 1.4–1.6 in, roughly three times the limit.
- **Monitoring:** the worst point read 0.61 in on 06/26/2026 with the building only partly loaded. The rate has more than doubled since December and groundwater at Block C has held steady, which fits consolidation under way. At the current rate the 1.0 in limit is reached around 09/12–09/20/2026.
- **Other problems for the revised calc:**
  - The calc's footing sizes and founding level (underside El. 740.5) don't match Detail 3/S-201 (7′-6″ footing, underside El. 746.0).
  - The slab-on-grade load over Block C is left out.
  - Some cited sources can't be traced in the record.

**What has to be produced to close it**
1. **Gregory Nash, PE (Engineer of Record):** a revised, sealed CB-GEO-007 that computes consolidation, stress beneath each footing, and differential and time-dependent settlement, using as-built footing geometry and checked against Art. 3.6.A.
2. **Gregory Nash, PE:** the written disposition Art. 3.6.B requires, setting out remedial measures for the footings already built and monitoring requirements. This should be coordinated with Kelbrook Geotechnical.
3. **Rowan Bay (Steven Kendrow):**
   - as-built footing records for C-1 to C-12;
   - a log of loads placed on Block C, dated against the readings;
   - the 07/10/2026 reading (missing from the record), with later readings taken weekly and copied to the Engineer of Record.

**Effect on the 07/22 Level-3 placement**
- **Block C loading:** Art. 3.6.B means Adrian should notify the Engineer of Record in writing, and no further load should go on the Block C foundations until the Engineer of Record's written disposition has been issued and verified.
- **Placement extent unclear:** the register lists the 07/22 placement as Blocks A/B only. However, the Level-3 shop drawings cover grids 1–8, and S-101 puts Block C on grids 6–8.
- **Recommendation:** Rowan Bay should confirm the placement's extent in writing before the hold-point is released. Item 051 doesn't otherwise hold the Block A/B pour.

**Choices and limits**
- I dated the memo 07/17/2026; change it if you issue on another day.
- The template had no cc line or page numbers, so I added both. The five numbered sections are unchanged.
- The `exports/` folder isn't writable, so the memo sits beside the template.
- I took the calc's 0.9 in short-term settlement as reported and didn't re-check it; the clay settlement alone exceeds the limit.