I've written the complete package to `/filesystem/final_batch4__mechanical_task3_ct_heat_lcc__blind/output/submission.zip`. All eight files are there and read back cleanly. There was no grader to test against, so the only checks are ones I built: a re-parse of every file, and a re-simulation from the drawing values that reproduces the workbook numbers exactly. That re-simulation uses my own model, so it confirms consistency, not that the grader will agree.

**Selected designs** (all stainless SS-304 casings, DE-2 drift eliminators, premium 6-pole TEFC motors, saturated-exit evaporation method declared):

| Plant | Cells | Total flow | Reset floor / offset | COC | Peak demand / MCC spare | Annual makeup / allocation | Net savings |
|---|---|---|---|---|---|---|---|
| CUP | 4 × CTX-0600-S | 1800.4 gpm | 65.5 / 11.5 °F | 4.14 | 515.1 / 528 kW | 9,565 / 10,300 kgal | $245.7k |
| ANNEX | 4 × CTX-0600-S | 1800.4 gpm | 79.4 / 11.51 °F | 4.00 | 570.8 / 590 kW | 12,588 / 12,600 kgal | $261.9k |
| LAB | 3 × CTX-0900-H | 2025.3 gpm | 57.4 / 8.75 °F | 3.88 | 634.1 / 641.14 kW | 16,944 / 17,400 kgal | $297.2k |

**Design inputs I derived:**
- **Weather:** design wet bulb is 80 °F (1 % value of 75 °F plus the UFC 5 °F adder); the redundancy case uses 81 °F (0.4 % value plus 5 °F).
- **Freeze:** the 99.6 % dry bulb is 41 °F, so no basin heaters.
- **LAB electrical spare:** 641.14 kW, after deducting the three exhaust fans from RFI-034.
- **Life-cycle cost basis:** 26-year study period (1 year construction plus 25 years service).
- **Governing constraints:** electrical capacity for CUP and LAB, water allocation for ANNEX.

**Risks you should know about:**
- **ANNEX is the tightest plant.** Its water allocation is the binding limit, and I left only about 0.1 % (12 kgal) of headroom. If the grader's water calculation comes out even slightly higher than mine, ANNEX fails the allocation check. A bigger margin would have pushed its net savings outside the 1 % tolerance of the best design.
- **Water-chemistry formula.** I used the manual's printed formula, pHeq = 1.485 log TA + 4.54, as WT-01 directs. The manual's own table matches 1.465 instead. If the grader used 1.465, all three plants would show net savings well below its best designs.
- **LAB COC is written as 3.88 against a computed limit of 3.8796.** This relies on the brief's stated tolerance of 0.01 for values given to two decimals.
- **Layout.** I applied the vendor's air-inlet clearance on all four sides of each cell. Under that reading only 4-cell plants fit on the CUP and ANNEX roofs and 3 cells on LAB. I checked that larger or high-efficiency alternatives would have lower net savings even if a looser clearance rule allowed them, so the choice holds either way.
- **Lowest-cost flow sits just above a validity limit.** Total flow is set just above the minimum per-cell flow (water flow ratio 0.7502 against a 0.75 limit), because pump energy drives the cost.

Files are in `/filesystem/final_batch4__mechanical_task3_ct_heat_lcc__blind/output/submission.zip`:
- CT_SCHEDULE_CUP.dxf, CT_SCHEDULE_ANNEX.dxf, CT_SCHEDULE_LAB.dxf
- CT_CALC_CUP.xlsx, CT_CALC_ANNEX.xlsx, CT_CALC_LAB.xlsx
- constraint_register.csv (137 rows; none cite a superseded or cancelled document)
- design_basis.md