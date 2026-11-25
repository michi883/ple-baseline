I've built `output/submission.zip` with the seven required files at the top level, covering both packages. My own checks pass: the column headers match the schemas, sheet sets agree across all four CSVs, every file is under 50 MB, no discipline is split, the ledgers add up, no 16-word verbatim run, and every cited clause number exists. No grader was available, so several judgement calls below are unconfirmed.

**What the plan decides**
- **BP-2** is Amendment 0003; it was already advertised, so that is the only option. 15 sheets are re-issued, including two added sheets, S-202 (braced bay framing elevations) and M-503 (chiller pad anchorage details). They go out in three files of at most 46 MB each, using Revision (Issue) block overflow Option 2 for the whole set. Total cost is **$56,228.64**, which includes a 1-day extension ($2,740).
- **BP-3** is corrected before advertisement, so it gets no change number, revision marks or continuation sheet. 16 sheets are re-issued, including added sheets A-402 and M-502, in two files. Total cost is **$44,853.04** with no delay. Issuing it as an amendment instead would cost $4,920 more.
- **Dates and windows:** the Contracting Officer's memo date for BP-3's advertisement (9 Nov 2026) is used over the schedule export. The review regulation (ER 415-1-11) sets a 30-day backcheck window for BP-3, giving a deadline of 2026-10-10. For BP-2 it is 15 days before bid opening, giving 2026-09-13.
- **Void markups (10):**
  - two drawn on superseded prints;
  - two by authors not on the reviewer roster;
  - two with no timestamp;
  - four whose author isn't registered in the discipline of the sheet marked, or holds no registration at all.
- **Other dispositions:** two comments stay closed as elevated from the 60% review. One documented non-concurrence per package (EOR-2-011, EOR-3-030), chosen because it is cheaper. Every other valid comment is incorporated.
- **Title-block defects on re-issued sheets:** S-301 (checker same as drafter), E-501 (wrong discipline seal), A-501 (checker same as designer), M-101 (wrong discipline seal).

**Judgement calls that could cost points if the grader reads them differently**
- **Revision layers:** I used `Z-ANNO-REVC` and `Z-ANNO-REVS`, because FC 1-300-09N ¶12-3.3.4 ranks its own chapter above the A/E/C CAD Standard. The catch is that the Z-layer rule sits in the record-drawing section, and the current sheets use the G-layers instead.
- **Registration voids:** voiding the four registration-ground markups rests on FAR 52.236-25 and the roster's registration fields. If the grader treats coordination comments from other disciplines as valid, those four rows change.
- **BP-2 delay:** I took the finish date as start + 14 days = 9/14, giving D = 1. If the last production day itself counts as the finish, D = 0 and the ledger's delay line ($2,740) is overstated.
- **Index order:** I moved general-notes and legend sheets to the front of each discipline group, so GI-002 sits ahead of GI-001 but G-001 stays first.
- **Added sheets in BP-2:** they carry revision mark 3 (adding $480).
- **Sheet charge:** the $1,150 re-issue charge is not applied to added sheets, which carry only the $6,400 added-sheet charge.
- **Drawing index sheet (GI-001):** not re-issued. In BP-2 the continuation sheet instructs the change instead; in BP-3 the new sheets appear only in the regenerated sheet index CSV.

Files are in `/filesystem/dc_structural__eor_revision__blind/output/`:
- submission.zip