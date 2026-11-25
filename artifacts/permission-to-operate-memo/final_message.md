I've written the memo to Lena for the reviewing engineer to sign, and opened the work package. The memo's answer is no: Permission to Operate can't issue on 08/04/2025 on the record as it stands, and she should hold.

**What stands in the way.** Telemetry can't be live at the SOC at the moment PTO is issued, which TCS-02 §5 and ISA 6.2 and 7.2 require.
- **The RTU's power runs through the POI recloser.** Brantley's equipment schedule (E-101 Rev C) feeds the RTU enclosure from a panel on the PV side. That panel is fed from the PV switchboard, which is fed through the transformer and the POI recloser. Providing that supply is Corwyn's job under TCS-02 §3.1/§3.4 and ISA 5.2, so it isn't part of the RTU review held elsewhere.
- **The recloser has to stay open until PTO.** ISA 6.1 allows it to be closed before PTO only for the witness test. Corwyn's ISA has no other provision for energizing the site early.
- **The RTU has been dead since 07/08/2025.** The recloser was opened at 15:35 after the witness test. On Brantley's own 5.5 h figure the UPS ran out at about 21:05; the Corvane runtime table puts it no later than about 21:35. The SOC's confirmation of live telemetry on the checklist was taken that day with the recloser closed, so it doesn't count as the §5 confirmation. Lena can see this herself on the RTU's communications heartbeat.
- **The per-inverter readings have the same problem.** They come straight from the inverters, which get their control power from their own ac output, so they're dead whenever the site is.

**What has to be done, and by whom.**
- **Corwyn (through Brantley Electric):**
  - Re-feed the RTU from a supply that stays live with the recloser open, for example a dedicated circuit from the office building's own service.
  - Show the UPS gives at least 4 h at the actual load after the data sheet's 20% derate. Nothing in the record shows the load behind the 5.5 h figure.
- **City of Wrenford:** permit and inspect the new circuit before it is energized.
- **SCADA/EMS Engineering (Marcus Deele):** specify the supply in the RTU drawing, accept it, and say in writing how the per-inverter readings will show as valid when PTO is issued. That last question has no answer yet.
- **DER Program Office (Contracts and Commissioning):** accept the change in writing and tell Corwyn now that 08/04 can't be confirmed.
- **SOC:** confirm live telemetry at the moment of issue.

It's one small circuit, and it could physically be finished within the 15 business days to 08/04. But the steps have to happen in order, none has started on the record, and the timing depends on Corwyn's contractor and the City's inspections. So the memo tells Lena to hold unless the Office confirms in writing before then that everything is closed. There is no conditional or interim route.

**Everything else checks out:** the executed ISA, the witness test (all points passed), the inverter certificate and equipment-list entry, the City's final approval, and the revenue meter. One minor records point: Distribution Protection Engineering's review of the customer-side protection (06/18) predates Brantley's Rev C drawings (06/24), so their confirmation should be filed. The four matters under separate review aren't addressed, and the hold stands whatever they conclude.

The signature block is left blank for the reviewing engineer's name and licence number. Work package #47 is in the DER Program Backlog Review project. It records the determination and lists 16 items by owner, including Corwyn's five. It is assigned to S. Rennick (Commissioning), set to In progress with High priority and due 08/04/2025, with Lena and Marcus added as watchers.

Files are in /filesystem:
- Corwyn_PTO_Memo.docx