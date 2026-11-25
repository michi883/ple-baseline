I've written the validation memo as a Word document, with a §7 drop-in and the Bianca paragraph inside it. The short answer is that the companion run did not validate. On the procedure's rollup line, S = 131 min, D = 118 min, E = +13 min and u_val = ±9 min.

**Your questions, in order:**
- **Assembly:** the run's assembly is the one the certification covers. That rests on all nine rows of Ironwood's §1.2 geometry table matching the drawing and the revC geometry, not on the identifiers. The run's revC label rests only on its own output header, because no case directory, setup record or log for the companion run is on the server.
- **Governing criterion:** single-point, a 181 °C rise above the 21.0 °C start, so the limit falls at 202.0 °C. The test reaches it at 118 min (TC-6, over a tie course); the run reaches it at 131 min. **The §7 stub's 131 min stands.** Reading 181 °C as an absolute temperature would give 118 min and a false exact match with D.
- **D and Bianca's figure:** I adopt D = 118 min. Her 129 min is not admissible under §6: there is no reissued Red Butte report, no calibration certificate and no supersession statement. It is also internally inconsistent: TC-6 is one of the nine averaged thermocouples, yet her table leaves the average at 163 min. Even if accepted, the run would still reach the average criterion 13 min late.
- **Error against both tests:** the criterion is 10 % of D = 11.8 min, and |E| = 13 min exceeds it. |E| also exceeds u_val (9 min), so this is a model error, not scatter. E is positive: the run says the wall holds longer than it did, which is the non-conservative direction.
- **Largest prediction that clears:** 129.8 min (129 min in whole minutes).
- **Two comparisons:**

| | Test | Run |
|---|---|---|
| Minutes between the two criteria | 45 min | 45 min |
| Governing point above the nine-point mean at governance | ≈ 85 °C | 91 °C |

- **What the comparisons say:** the run reproduces the tie hot spot's lead over the rest of the face. The fault is a uniform 13 min lag at both criteria, so the rework belongs in the through-wall heat path that every point on the face shares: leaf properties and the cavity and unexposed-face boundary conditions. It does not belong in tie mesh refinement, the geometry or the furnace-side exposure. **None of it has started;** CO-002 is a mesh pass on two wildfire cases.
- **Rest of Phase 1:**
  - The wildfire through-wall outputs use the same treatment, so they would understate heating in Ocotillo's favour.
  - The 10/27 Red Butte window is an E119 test under the SOW, but report §4.2 calls it a wildfire-phase test. That needs correcting.
  - The rating stays at 1 hour.
- **Wildfire claim:** this exercise establishes nothing about wildfire performance. There is also no wood-frame comparator anywhere on file. The memo sets out what evidence would close that gap and the reporting form any future comparison must follow.
- **If Bianca's figure were substantiated:** 129 min clears the 120 min needed for the 2-hour rung. Only Red Butte can reissue the result and only Ironwood can change the rating — not Ocotillo and not us.
- **Stamp language:** "CFD thermal analysis only. Fire-resistance rating certified separately by others."
- **Checklist:** item 6 can close on this memo. Items 2, 3, 4, 5, 7, 9 and 10 stay open, with the reason for each given in the memo.

**Things that need your call or attention:**
- Your Modeling Standard §3.5 bans constant solid properties, but App. A and the drawing supply only constants. The rework needs your ruling on which governs.
- The run's tie temperature jumps to 64.2 °C within 1 min and then sits flat at 71.0 °C. Neither criterion uses it, but it should be checked in the rework.
- The site-mesh log shows walls 3048 mm tall against revC's 2745 mm panel, which is part of why item 7 stays open.

The seal isn't applied; the memo is marked as a review copy. No other file on the server was changed. The container lacks Calibri, so my test render ran to 11 pages; it will be somewhat shorter in Word.

Files are in `output/`:
- `CFDME-2025-041_E119_validation_memo_revA.docx` — the memo (Bianca paragraph is Section 13)
- `CFDME-2025-041_Rennert_reply_paragraph_revA.txt` — the same paragraph as plain text, for pasting into an email