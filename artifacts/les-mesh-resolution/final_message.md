I've saved the note as `/filesystem/CFDME-2025-041_resolution_note_revA.docx`. It's about 2⅓ pages in the firm's memo style, addressed to Marguerite, and lists its sources. The short version: **Item 4 cannot close on rev B as written.**

1. **Where the index lands:** the report's figure is D*/dx = 7.5, from D* = 3.76 m and the fine grid's 0.5 m background cell. That is inside our 5–10 band.
   - The fire itself is carried in a refinement zone two levels finer, at 0.125 m; the mesh check output confirms that cell size. On that cell D*/dx is about 30, above the band.
   - So the band is met only if 0.5 m counts as the "representative" cell.
   - D* is also slightly wrong: the scoping memo's own inputs give 3.74 m, not 3.76 m. The index still rounds to 7.5.

2. **What acceptance rests on:** QA Verification Standard rev 3 §5. Either the index or the resolved-energy (Pope) test alone is enough, but both are the default for life-safety work. Four things need Marguerite's decision, because the standard doesn't settle them:
   - which cell size counts as representative;
   - whether an index above 10 fails the band or is only "wasteful";
   - whether Ocotillo's public fire-safety claim for homes counts as life-safety use, which would make both tests the default;
   - whether D* should use site air (minor).

3. **Resolved-energy figure:** no, it was not taken inside the region the index describes. The 84 % comes from the plume-axis probe, which sits inside the 0.125 m zone; the 7.5 describes 0.5 m cells, where nothing was measured. The study's "PASS on both criteria" pairs numbers from two different regions, and no single region shows both.

4. **Ambient values:** they don't represent the site. D* uses sea-level air at 20 °C; the site is at about 750 m and 35–42 °C. Temperature cancels out of D*, but the lower pressure at elevation raises it about 3.6 %, to roughly 3.88 m. That moves the index to about 7.8 on 0.5 m cells and about 31 on 0.125 m cells, so the band answer doesn't change.

5. **Closing the item:**
   - **What fails now:** the values sit in an appendix, a three-grid table is offered as evidence, and the Verification section leaves out the turbulence sub-model, the averaging window and an acceptance sentence.
   - **What settles it with nothing new run:** Marguerite records her four decisions, and the Verification section is rewritten from numbers already on file. The note includes a model acceptance sentence.
   - **If she wants both tests passed in one region:** the file can't show that today. The only option without a run is pulling a reading from the fine-grid results in the 0.5 m cells, if those were kept on the cluster. Otherwise it waits for the Sprint 2 production runs.

The note also flags that:
- the production mesh's plume region is 0.25 m and 0.125 m, not 0.5 m;
- the only solve on that mesh is a steady RANS run that can't supply either test;
- the turbulence sub-model used in the study isn't recorded anywhere on the file server.

**Points to check before you send it:**
- **"From" line:** it says "CFDME-2025-041 project team"; put your name in if you prefer.
- **No issue date:** the system clock reads 2026, so the note is dated by the record (10/09/2025) instead.
- **Averaging window:** the 8–40 s window is inferred, because the fine-grid output doesn't state it.
- **"Near 60 %" estimate:** the resolved energy in the 0.5 m cells is a rough scaling estimate, labelled in the note as not evidence.
- **Site pressure:** this is a standard-atmosphere figure for the windload memo's "~750 m"; an error of 100 m moves D* by only about 0.5 %.