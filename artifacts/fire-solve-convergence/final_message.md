I've written the technical note at `/filesystem/CFDME-2025-041_transient_solve_disposition_revA.docx`. It runs 12 pages on the firm letterhead, dated 10/10/2025. The disposition is **attempt 3 rejected and returned for correction; no fourth steady attempt**. The signature lines and seal are left blank for you and Marguerite to sign. I used Gordon as preparer and stamp, Marguerite as reviewer.

**Residual plateau and steady solution**
- **The plateau is the plume puffing, not stalled convergence.** It should show 0.87 Hz and a 1.15 s period (D = 3.0 m). Attempt 3 showed about 0.87 Hz and 1.15 s, which agrees within **0.41 %**.
- The run's 1.15 s figure is weak evidence, because a steady solver's iterations carry no physical time. The firm's three transient study runs recorded 1.14, 1.15 and 1.15 s, which confirms the period.
- **No steady solution exists** (Modeling Standard rev 4 §4).

**Rest of the delivered setup**
- **Non-conforming:** the solver setup, time control, turbulence model, walls, ambient state (the Dry Wash high-altitude conditions), wall assembly and ties, schemes, solution controls, radiation settings, the missing regime call and the "validated setup" claim. Section 5 gives the required setting for each.
- **Conforming:** the combustion model, the radiation model choice, the fluid thermophysics and the wind inlet type.

**Authorized run (case 3.1-B, 240°, 8 m/s)**
- maxCo 0.9 and maxDeltaT 0.01 s (the reference dictionary's value), with adaptive time-stepping.
- writeInterval **0.0461 s**, the largest that still gives 25 samples per period.
- endTime **31.10 s**: 8.00 s startup plus 20 periods (23.09 s), rounded up so the window keeps all 20.
- Nine entries differ from Mulshi's controlDict; both values are tabulated.
- Note that the firm's own reference dictionary writes every 0.1000 s, which fails the 25-sample rule for this plume.

**Mesh**
- Attempt 3 ran on the production mesh with the wall assembly (11,214,862 cells, revC, 40 m domain top).
- Our verification covers a different, fluid-only study grid (11,196,000 cells, Pope fraction 84 %).
- It does not cover the production mesh, the tie refinement, the 240° inflow arrangement, revD, or the geometry trace.

**What carries forward**
- Geometry, the production mesh (conditionally), the combustion and radiation models (radiation re-banded), the fluid thermophysics and the probes.
- The inlet: Uref 8.0 m/s at Zref 6.1 m, roughness 0.03 m, displacement height 0.0 m, from 240°.
- The delivered flow-direction entry does not actually encode 240°, and the run's probe shows flow from 270°. It has to be fixed before the run counts as case 3.1-B.

**Cost (solver wall clock)**
- **4 h 28 min per case and 26 h 49 min for the six cases**, at the study fine grid's rate (40.00 s simulated in 5 h 45 min).
- **Falk's basis cannot be met** for this run. The rate comes from a different grid and solver stack, and the study's core count wasn't recorded.
- That study grid ran at the Courant limit (0.90 against 0.9). The production mesh has smaller cells and the matrix includes 12 m/s cases, so the time step there can only be the same or shorter.
- **The figure is an optimistic floor and should not be quoted.** The real rate will come from case 3.1-B run at a fixed, recorded core count.
- **Attempt 3** used 6 h 41 min on 64 cores (424.3 CPU-hours) and reached no simulated time. That is 1.49 times one case and 24.9 % of the matrix figure.
- Only the plateau record and the job-sizing data from attempt 3 are usable.

**Other errors on file**
- Phase 1 report rev B, Appendix C misstates where the 11,214,862 cell count comes from.
- The scoping memo's D* arithmetic is slightly off (3.74 m, not 3.76 m); it doesn't change any result.
- Modeling Standard Appendix A allows constant solid properties, which conflicts with its own §3.5.

These are listed as open items with owners in Section 10.