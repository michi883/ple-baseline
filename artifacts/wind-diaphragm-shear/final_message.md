`output/submission.zip` is written and checked. It contains exactly the five required files, all of which open and parse, and the schedule headers match the templates with no blank cells. There was no verifier available, so every check below is one I built myself.

**Analysis.** I wrote my own implementation of the criteria's DIAPH‑MT semi-rigid model. It reproduces the published verification example exactly: 240 elements / 273 nodes, reactions 10.00 / 10.00 k, peak unit shear 185.2 plf, peak chord bar force 2.57 k, peak Y displacement 0.1669 in. Matching it required placing each pier at the nearest mesh node with round-half-to-even on ties; no other tie rule gives those values. The schedule values also match a second, independent run of the solver exactly.

- **Geometry:** taken from the 2026 IFC model and the roof scan — the generator-yard notch, the mechanical well, the 36.00 ft screen wall (N108–N111) and the field-cut opening in S14, whose 1.5 ft leg is dropped.
- **Wind:** V = 115 mph, Kzt = 1.19, Ke = 0.867, giving q_h = 28.74 psf. The parapet and screen-wall lever action is included, the torsional cases use M_T = e·B·|F|, and every reported quantity is ASD (0.6W).
- **Mesh:** results are reported at L2. The wall-line W reaction under W01 changes 0.18 % from L2 to L3 (limit 5 %).

**Design: installed cost $221,430 (cap $310,000).**
- **Deck:** 4 deck types (the Owner's limit) over the 12 zones.
- **Chords:** PL3x3/8 throughout, except a PL12x1 chord on line E2. That chord is there to spread load along E2 so that panel E201 stays within its base-connection capacity; without it E201 was at 135 % of capacity.
- **Connections:** 199 embeds and 9 tie-downs.
- **Margins:** peak deflection is 0.521 in against 0.55 in. All checks hold with 3–5 % margin, also under the alternative E2-direction and torsion-sign assumptions.

**Judgement calls the grade depends on** (all recorded in the design basis):
- **E2 wall direction:** I applied the E2 line load as if the wall faced west. Geometrically it faces east into the yard, but the IFC model, the scan and the wind coefficients all treat its exterior as west. If the Engineer's re-analysis uses the geometric direction, about 4–7 of the 36 reported values per scenario would fall outside tolerance.
- **Torsion sign:** positive eccentricity is taken as a counter-clockwise moment.
- **Station ties:** report stations fall exactly between two elements. 213 of 216 values are within tolerance whichever element is picked; the other 3 use the lower-coordinate element.
- **Embed count:** I used the conservative rule max(2, ⌈L/8⌉+1, shear count). If the intended rule is ⌈L/8⌉, this costs about $11.6k more than needed.
- **Governing scenario:** taken as the one with the largest line load on each wall line, which matches the spec's example "S | W05". If the reaction is meant instead, all six rows would change.

**What each file holds:**
- `lateral_schedule.xlsx`: the nine sheets as specified.
- `diaphragm_plan.dxf`: one plan on the building grid in feet, using all seven required layers. Both directions are overlaid and labelled TRANSVERSE and LONGITUDINAL, with "LOADS SHOWN ARE ASD" on the face.
- `constraint_register.xlsx`: 130 rows, each citing a clause that appears word-for-word in a current document. Numbers appear only where they are in that clause, and no superseded document is cited.
- `calculations.pdf`: 14 letter-portrait pages with the seven sections from criteria 11.1, marked ASD on every page.
- `design_basis.md`: the two required tables and 18 resolved document conflicts.