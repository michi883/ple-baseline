I've filed the package, logged three scheduling items on case #45 and closed the case. Three arrays need a witness test, and only Marden Falls can go to the SOC for release, once Standards Engineering signs its waiver.

**Scope on 07/14/2025:** five arrays are in the batch. Tresbay Community Center is out because it withdrew its request on 07/09/2025, per the case record.

**Carriage calls against CEL-2025-Q2,** the current list (no later edition had been published by 07/14/2025):

| Array | Inverter actually installed | Call | Result |
|---|---|---|---|
| Cravenwood High | Solmery SM-215K-3P (on the list) | Carried | Waiver eligible; disposition is Standards Engineering's |
| Marden Falls WRF | 4 × Solmery SM-245K-3P (on the list) | Carried | Waiver eligible; disposition is Standards Engineering's |
| Darnwick Elementary | Arvexa PV-750 (on neither edition) | Not carried | Witness test required |
| Holcott Library | Selvix SV-720 (on the superseded edition only) | Not carried | Witness test required |
| Lockmere Middle | Selvix SV-720 | Not carried | Witness test required |

Lockmere's checklist shows Torvane TE-180K units, which are on the list. However, Evan Solberg's note on the commissioning wiki says a Selvix SV-720 was substituted on site after the checklist was submitted, so I made the call on the SV-720.

**Witness-test package (Darnwick, Holcott, Lockmere):**
- **Tests:** the waiver procedure's minimum set, run to IEEE 1547.1 — protective trip tests, anti-islanding and ride-through checks, measured against each site's approved settings.
- **Who:** the customer or its commissioning agent performs the tests; an Alleniom witness engineer observes, records and signs.
- **On file first:** the corrected checklist marking, settings sheets, the customer's test plan, instrument calibration records, operator names and manufacturer test evidence.
- **Lockmere:** also needs a revised checklist and an ISA change order for the substitution.
- **Sequencing:** schedule Lockmere first, because the witness test is the only thing holding its permission to operate.

**SOC release list:** Marden Falls only. Nothing can be released today, because no array has a signed waiver or witness-test sign-off. Lockmere is left off despite live telemetry until its witness test is done, and Cravenwood is left off until its telemetry unit is installed and live.

**Case tracking:**
- Scheduling items #47 (Darnwick), #48 (Holcott) and #49 (Lockmere) are linked to #45 and assigned to Evan Solberg as case owner.
- They show status "New": the task workflow wouldn't accept "To be scheduled".
- I recorded the batch determination as a comment on #45 and closed it after confirming the package's three arrays match the three items.

**Flagged for Standards Engineering in the package:**
- **Wrong cross-reference:** the waiver procedure points to DIS-01 §6 for the test points, but that section covers monitoring and control.
- **Protective relays:** the procedure requires them to be on the list, but the checklists don't identify relay models and the list has no relay entries.
- **Next list edition:** the next edition is due 07/31/2025; any waiver signed after it takes effect must be rechecked against it.
- **Missing from records:** the arrays waiting on telemetry units aren't on the equipment-allocation roster. The Cravenwood and Lockmere application numbers don't appear in the queue reports, and the other three checklists carry no application number.

Files are in the document store, folder /DER_Program/Commissioning/Municipal/:
- Municipal_Witness_Test_Package.docx