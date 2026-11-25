I've written `output/submission.zip` with all five files. In my own re-implementation of the DAP-2 protocol, the design passes every strength, deflection and drift check. That model reproduces all the published verification values in DAP-2 Appendix A. There was no verifier, so the cost-optimality and the reported numbers haven't been checked against the grader. The installed cost is **$339,534**, $55,466 under the $395,000 cap.

**Seismic basis:** Risk Category III (Ie = 1.25), Site Class D, SDS = 0.44, SD1 = 0.24. That gives SDC D: SD1 governs over SDS. Cs = 0.1375, W = 2,270.5 kips, V = 312.2 kips. The wall weight delivered to the roof is 1,716 plf, which includes the lever action of the 3 ft parapet.

**Design:**
- **Wall system:** intermediate precast shear walls, R = 4, Ω0 = 2.5 (2.0 for collectors under footnote b), Cd = 4, from UFC 3-301-01 Table 3-1 row A.6 (same as ASCE 7-22 Table 12.2-1). Ordinary precast is not permitted in SDC D, and the special system's premium alone pushes the total over the cap.
- **Geometry:** taken from the 7 Aug scan, which I registered to the building grid using the four control targets, cross-checked against the erection log and RFI-041.
- **Deck zones:** P5 in Z1, Z4, Z9, Z10; P4 in Z5, Z6, Z8, Z11, Z12; P3 in Z2, Z3; P2 in Z7. I found this by a cost-driven search across all 24 load combinations. The worst zone is at 92% of capacity; amplified deflection is 3.79 in against the 4.0 in limit.
- **Chords, collectors and drag struts:** C1 (L4x4x3/8) on all 20 lines. That includes drag struts across the 12–16 ft louvers, because SDC-02 asks for one across every wall opening 12 ft or wider.
- **Walls:** no joint connectors (isolated panel piers), BA2 tie-down on every panel, WA2 anchors at 10 ft. Anchorage force is 858 plf, set by the code minimum 0.2·ka·Ie·Wp with ka = 2.0. The anchors are checked including the 1.4 factor for steel elements.

**Things to know:**
- **Erection-stage deflection drives the deck.** With the deck east of X = 180 ft unfastened, the roof cantilevers from the west wall; that case sets the 3.79 in. Meeting the 4.0 in limit there too costs about $5,400 in deck upgrades. I assumed the limit applies to the erection cases; if it doesn't, that money can come back out.
- **No joint connectors is a deliberate choice.** Under DAP-2's tie-down definition (VP-1 gives a panel-1 base moment of 88.91 kip-in), connectors make the segments stiffer and raise tie-down demand, so they cost more twice over.
- **Margin I bought:** Z4 is P5 rather than P4 (+$1,944). Under some alternative readings of the protocol, its shear reaches 0.99–1.01 of the P4 capacity.
- **Chord capacity assumption:** I took member capacity as 0.9·Fy·Ag, assuming the chords are braced by the deck. Peak chord force is 56.7 kips against 92.7 kips. If the grader uses a buckling-based compression capacity, the S and N chords could fail.
- **Readings I chose where the documents are ambiguous:**
  - Wall weight uses full wall lengths, with no deduction for openings.
  - Tie-downs and the SFRS premium are counted on 81 panels, from the shop tickets. My own as-built model splits the walls into 79 panels; at 79 the cost would be about $5,500 lower.
  - Accidental eccentricity "+1" means the centre of mass shifts in the positive X/Y direction.
  - The design is checked for both signs, and against several other plausible protocol readings; worst cases stay at or below 0.945 of capacity.

Files are in `output/submission.zip`:
- design_record.json
- diaphragm_plan.dxf
- seismic_calculations.xlsx
- constraint_register.xlsx
- design_basis.md