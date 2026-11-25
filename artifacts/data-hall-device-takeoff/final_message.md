I've written `output/submission.zip` with the five required files (`takeoff.csv`, `locations.csv`, `bom.csv`, `register.csv`, `basis.md`). A consistency script I wrote passes: totals agree across files, every bill line re-prices exactly, purchases are whole cartons with the 5% spare, and all 23 manual clauses are in the register. There is no verifier here, so the counts are unconfirmed, and four of them rest on judgement calls listed below.

**Takeoff:** R1 51 · R2 8 · R3 8 · R4 6 · R5 32 · R6 4 · R7 6 · J1 38 · P1 7 · F1 12 · F2 4 · F3 3 · F4 6 · F5 30 · D1 27 · R8 0 · F6 0.

**How the counts were built**
- Every symbol on the four power plans, the fire alarm plan and the enlarged plans was matched against the legend by computer, then checked by eye. Positions were converted to millimetres so duplicates could be ruled out across match lines and overlapping enlarged views; none were found.
- Devices in the electrical/entry strip and the PDU gallery were counted from the enlarged plans.
- **Addendum 2:** deleted the 4 plain duplex receptacles (R1) inside the cloud in bay A1 and added 2 quadraplex (R2) at the two southernmost positions.
- **Keyed notes** (none are drawn):
  - 8 visible appliances (F1), one per bay on the north and south walls.
  - 4 more F1, one per exit door.
  - 28 weather-resistant receptacles (R5), one per CRAH unit: 4 perimeter plus 24 in-row, as drawn on the plans.
  - 6 floor boxes (R7), one per PDU.
- **Unresolved:** two square-with-diamond symbols that are not in the legend, on E-232 (bay A4) and E-233 (bay C4). They carry no quantity and are listed in `basis.md`.

**Bill:** each device type and location condition gets the cheapest assembly the spec allows, priced at each line's own quantity breaks.
- **Basket total: $17,986.78**; purchase total including spare and cartons is $21,166.05.
- The spec requires an extra-duty while-in-use hood on weather-resistant and damp-area receptacles. The catalogue has none, so it is stated in `basis.md` with no line.

**Judgement calls** (all stated in `basis.md`; each one changes a count or a condition, so any of them could fail an exact check):
1. **Addendum scope:** "the duplex receptacles" was read as R1 only. If it means every duplex type in the cloud, R5 falls to 28 and R6 to 3.
2. **Vestibule R5s:** the four R5s drawn on E-201 inside the entry vestibule are counted, although that area is otherwise drawn empty on the parent plan.
3. **CRAH count:** the equipment schedules say 12 in-row units, but every plan shows 24. I used the plans, giving 28 R5 for the keyed note.
4. **Dotted-circle symbols:** read as access-floor detectors (F5), although their dash pattern differs from the legend symbol.
5. **Pull box on the apron edge:** one pull box on E-201 sits on the edge of a damp CRAH apron and is carried as damp. Otherwise it would be two-hour rated or masonry.
6. **Sheet attribution:** keyed-note devices have no drawn position, so which sheet they are reported on in `locations.csv` is a convention. That only affects a soft check.

My working files are in `/filesystem/work`.