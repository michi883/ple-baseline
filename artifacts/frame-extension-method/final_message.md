I've built the method package and written it to `output/submission.zip`, which holds the six files; the loose copies in `output/` are identical. My own checker, which re-reads the files from the zip, finds no violations. There is no verifier in this workspace, so that is a check against my reading of the rules, not against the grader's.

**Programme**
- All 294 issued activities are programmed with their issued ids, durations and crane hours, and all 308 issued dependencies are kept.
- I added two kinds of logic. The lift above in a zone waits until the lift below has finished (TWP-09 7.2), and each slab is struck only at its early-strike age.
- The last activity finishes on day 203, against the day-250 completion date.
- Peak demands on any day: crane 9.40 of 10 h, gangs 6 of 8, shoring yard 3599 of 3600 sf, scaffold face 104 of 120 ft, laydown 16 of 16 units, stair-core zones shored 1 of 1.
- The 3600 sf shoring yard governs the programme length. I tried an exact solver; it found nothing better and puts the programme within about 3% of optimal on mean bound/price, if the bound works the way I assumed.

**Temporary works**
- **Shoring:** SP-16 posts at 3.5 ft centres for the 387.6 and 397.6 psf zones and 4.0 ft for 372.6 psf. The 4.0 ft grid puts 5962 lb on a 6000 lb post: compliant, but with almost no reserve.
- **Striking:** every slab is struck early under RS-16 reshores at 8 ft centres, which stay until the slab is 28 days old. Leaving the shores in for 28 days instead could not meet day 250 with a 3600 sf yard.
- **Scaffold:** SF-3 frames for light and medium duty. Heavy duty (bands E–G) needs SF-5 because the planks it needs don't fit the narrower frame. Ties, guardrails at 42 in and hook-on ladders with rest platforms above 35 ft follow the clauses.
- **Lateral stability:** XB-1 cross-bracing on every zone-lift.
- **Crane:** one tower crane at CP-C serves every zone. The power line is handled under Option 3: 10 ft minimum approach and a work zone demarcated at 140 ft.

**Register and note**
- The register has 143 rows: all 31 TWP-09 revision C parameters with their values, plus the applicable clauses of the five adopted CFR sections. Every cited clause exists in the shipped text, and nothing from revision B, the revision A baseline or MS-14 is cited.
- The method note covers the four things it is read for and carries the LivingBIM CC BY 4.0 attribution.

**Where I chose the stricter reading.** The brief doesn't settle these, so a different reading by the grader would cost marks:
- **Strike age** is counted from the day after the pour finishes, one day more than counting from the placing day.
- **Resources:** reshoring holds yard stock through its removal day, and the crane is scheduled to 9.95 h rather than 10.
- **Takeoff:** posts are the soffit area divided by the grid squared. Light-duty platforms get a third plank to cover the planks' own weight, and heavy-duty platforms a sixth to keep the platform fully planked.
- **Occupancy report:** shored days run from shoring start to strike finish. Those columns must match the grader exactly, so this is the reading with the most riding on it.
- **Z-D-S crane radius:** the zone is 38.5 ft from the crane, inside the chart's first radius of 40 ft, so I rated it at the 38,000 lb chart maximum. If the grader extrapolates the chart instead, that capacity misses its 2% tolerance on the three Z-D-S zone-lifts.

My build and checker scripts are in `/filesystem/work`, outside the input tree.