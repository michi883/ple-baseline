I've written the BIM model to `submission/model.ifc`. It's untested against the real grader, which wasn't available. My own checker, written from my reading of the brief, finds no failures in either phase, both on the design and on the geometry read back out of the IFC file.

**Layout** (local metres; every building is a rectangle extruded from the ground, except the berm)
- **First data hall (`DH1`, phase 1):** south-west area, 74.5 × 61.5 m, 2 storeys × 5 m, gross floor area 9,164 m².
- **Second data hall (`DH2`, phase 2):** northern area, 61 × 75.5 m, 2 storeys, gross floor area 9,211 m².
- **Substation (`SUB1`):** 32 × 32 m, at the north end of the corridor between the wetlands.
- **Cooling plant (`CTP1`) and generator yard (`GEN1`):** along the north setback, both 3.5 m high and 32 m apart.
- **Berm (`BRM1`):** 5 m high, shaped like a comb so it covers the south and west sides of both the generator yard and the cooling plant. Using phase-1 structures only, it blocks every sight line from either receptor to the generator yard, even for target points up to 4.7 m high.
- **Retention basin (`RET1`):** 70 × 29 m (2,030 m²), modelled just below ground (top at z = 0) as the contract requires.
- **Road:** one 6 m road from a single entrance at (178, 1) on the south frontage, up the corridor, then east (299 m). Every building is within 14.6 m of it.
- **Medium-voltage lines:** utility entry → substation and substation → `DH1` (phase 1), substation → `DH2` (phase 2). All three meet within 1.2 m at the substation's south-east corner, so they connect under either the 2 m join rule or the "substation as common bus" rule. The phase-2 line stays 0.7 m outside the phase-1 substation, as clause 7.5 requires.

**Key results against the brief**

| Requirement | Limit | My design |
|---|---|---|
| Phase-1 cost (MV + 0.3 × road) | ≤ 314 | 298.4 |
| Full build-out cost | ≤ 473 | 360.0 (reference design: 454.7) |
| Noise at R1 / R2 | ≤ 42.35 dB | 37.4 / 38.4 dB |
| Site coverage | ≤ 15.1 % | 12.9 % |
| Stormwater basin area | ≥ 1,583 m² | 2,030 m² |
| Generator-yard separation from occupied buildings | ≥ 28 m | 32 m |
| Wetland clearance: buildings / road | ≥ 8 m | 10 m / 18 m |
| Lot-line setback | ≥ 18 m | ≥ 18.5 m, including the exempt berm and basin |

Heights, floor-to-floor heights, data-hall aspect ratios and minimum areas are also within limits.

**Judgement calls the grader could read differently**
- **Number of data halls:** I built two in total (one per phase). The program's `count: 2` on `DH2` could be read as two phase-2 halls; I read it as cumulative, matching the brief's "two data halls".
- **MV length rule (6.2):** I compared the total MV length with the largest centroid-to-centroid distance it serves. Both phases pass with margin.
- **Utility feed node:** the graph edge for the utility connection uses a non-building node I named `POI`.
- **Footprint curves:** I used `IfcPolyline`, which the contract names, rather than the example's `IfcIndexedPolyCurve`.
- **Storeys on other buildings:** following the example, every non-data-hall building has one storey and a floor-area value equal to its footprint.

The scripts that generate and check the model are in `/app/work`: `design.py`, `check.py`, `write_ifc.py` and `validate_ifc.py`.