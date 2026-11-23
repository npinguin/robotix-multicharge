# Robotix MultiCharge — functionele productspecificatie en use-casecontract

**Status:** normatief functioneel doel- en acceptatiecontract; geen implementatie- of releasestatus. **Basisdatum:** 23 november 2026. **Reikwijdte:** UC01–UC29 + FLEX-01–21 + FORECAST-01–12 + UI-OWNER-01–10. Productgeneriek; Wessels is uitsluitend een concreet sitekwalificatieprofiel.

> **Dit is de enige functionele bron van waarheid voor MultiCharge.** De [RHI-platformvisie](https://github.com/npinguin/robotix-home-intelligence/blob/main/docs/ENGINEERING_PLATFORM_VISION.md) blijft hiërarchisch hoger voor platformeigenaarschap. [`ARCHITECTURE.md`](ARCHITECTURE.md) en [`INTERFACES.md`](INTERFACES.md) beschrijven implementatie en technische contracten, niet een tweede use-casebacklog. [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1), [Draft PR #9](https://github.com/npinguin/robotix-multicharge/pull/9), source-tests en exacte CI bewijzen alleen hun eigen status. Wijzig geen UC-scope uitsluitend in een PR-body; werk deze specificatie eerst bij en verwijs daarna naar gewijzigde UC-ID's.

## 0. Productvisie en toetsbare ontwerpgrenzen

**WHY —** Eén begrijpelijke laadervaring voor woningen met uiteenlopende laadpunten, voertuigen, prijzen, zon en gedeelde elektrische capaciteit zonder foutieve planning of meerdere fysieke commandowriters.

**WHAT —** Eén onafhankelijke Community Home Assistant-integratie met **ChargeController, Charger en ChargeableAsset**, vijf vaste schermen (**Overview → Charging Plan → Chargeable Assets → Chargers → Settings**), native configuratie, laadplanning, source-quality, uitvoering/readback, historie en herstel. Zonder verplichte Robotix Core/Basic/Premium, site-packages, template-sensors of handgemaakte helpers.

**HOW —** Hergebruik native HA-providerdata, Entity/Device Registry en Recorder. MultiCharge normaliseert geselecteerde bronnen, bezit één Config Entry, één 15-minutenplanner, één guarded executor en één resident/admin-UX. Bronmetingen blijven bij hun native provider. Fysiek beheer blijft bij bestaande eigenaar tot afzonderlijk gekwalificeerde exclusieve overdracht.

**PROOF —** Per UC een reproduceerbare GIVEN → WHEN → THEN, negatieve/fail-closed proef en waarneembaar bewijs. Developer/source CI, echte HA-integratie, browser, leverancierreadback, fysieke EVSE en field acceptance worden afzonderlijk vastgesteld. Een servicecall is geen fysiek resultaat.

**NEXT —** Volledige ontwikkelscope en regressies afwerken, daarna de bestaande kwalificatiepoort doorlopen met echte 0/1/2/4/10 laadpunten, nacht-/DST-tijdvakken, 390/1024/1600 schermen, acht talen, hardware en rollback. Geen stilzwijgende scopeknip of productiecutover.

### 0.1 Gebruikerservaring en directe configuratie

Een verse HA-installatie biedt **Guided setup** of **Configure entire charging site** (één complete data-only `controller/assets/chargers`-YAML met review/save) in dezelfde native Config Flow. In-card Settings en native HA owned entities zijn bruikbaar na installatie; expert file-managed config blijft uitdrukkelijk file-owned/read-only. Configureer alle voertuigprofielen, Chargers, elektriciteitslimieten, PV/grid en prijzen direct uit bestaande native HA-providers. Geen externe Robotix-producten, package-installatie of verplichte `template:`-blokken. Expert source-binding is installatieconfiguratie; dagelijkse voorkeuren leven op de bestaande logical owner devices.

### 0.1.1 Progressieve capability — bijna geen informatie tot volledige bronintegratie

**Acceptatieprincipe:** MultiCharge is één generiek product met **capability-driven progressive enhancement**, geen aparte Lite/Pro-mode, geen nieuwe Charger- of voertuigklasse en geen verplichte databronlijst. Je kunt een lege laadlocatie, een Guest zonder OEM/SoC en een eenvoudige geschikte laadmogelijkheid toevoegen **zonder** prijzen, PV, Energy Dashboard, andere Robotix-producten, YAML-packages of template sensors. Een extra, gevalideerde bron ontsluit alleen de functies waarvoor die bron nodig is. Een ontbrekende bron mag **niet** een onafhankelijk bruikbare functie uitschakelen; zij mag ook geen fysiek veiligheidsbewijs simuleren.

| Installatieprofiel | Welke gegevens zijn werkelijk beschikbaar? | Wat de gebruiker moet kunnen doen | Niet zomaar toestaan / vereiste kwalificatie |
| --- | --- | --- | --- |
| **0 — Nieuwe of lege HA** | Geen voertuig, geen Charger, geen OEM-account, geen PV of tarieven | Integratie configureren, drie logische concepten begrijpen, lege vijf-tab UX zien, later bronnen en apparaten toevoegen | Geen fictieve verbonden Charger of fysiek START |
| **1 — Guest + eenvoudige, elektrisch geschikte smart plug/aan-uit-lader** | Naam van Guest of helemaal géén geregistreerd voertuig; geschikte native aan/uit-service, eventueel gemeten vermogen; **geen SoC of kabelsensor** | Guest registreren of een begrensde **Charger-only** eenmalige sessie voorbereiden met **eindige minuten**, de werkelijke status zien en later zonder migratie uitbreiden | Een smart plug is niet automatisch een veilige EVSE. Fysiek starten kan pas na **geverifieerde elektrische geschiktheid en exclusief writer-eigenaarschap**, voldoende fysieke verbinding-/gebruikersbevestiging passend bij het apparaat en onafhankelijke power/STOP-readback. Als dat bewijs ontbreekt: duidelijke HOLD, **niet** het profiel of de hele UI blokkeren. **Manuele bevestiging** mag een onbestaande hardwarebeveiliging niet vervangen |
| **2 — Charger met echte energie- en statusmetingen, maar geen OEM-SoC** | Native connected/disconnected of bewezen equivalente status, gemeten W/kW en kWh; on/off of gekwalificeerde current | Eindige kWh-/minutenlading, actuele sessie, gemeten progress, prioriteit en deadline; Economy/Solar alleen bij echte optionele sources | Geen kWh-claim uit tijd alleen; `switch.on` is nooit een kabelmeting; geen fictieve resterende batterijlading |
| **3 — Volledige native Charger + voertuig + energiebronnen** | Bijvoorbeeld VW ID.4/Audi Q8 met actuele OEM-SoC/health/capaciteit; Wallbox/Peblar met native connectie, vermogen, current set/readback; eventueel PV, grid, tarieven | 80%-default waar toepasselijk, eigen SoC-doel, Ready By, Automatic, Solar, Economy, current modulation, betrouwbare historie, kosten uitsluitend bij effectieve tariefdekking | Geen fabrikantcode in generieke planner, geen verplicht voertuigcloudaccount, geen afgeleide all-in kost uit spotprijzen, geen ongeverifieerde fysieke eigenaarschapsoverdracht |

**Eén betekenis, één eigenaar:** De native HA-provider bezit de fysieke service, het echte apparaat en zijn metingen; **Charger** bezit het fysieke laadpunt, de geselecteerde voertuigvoorkeur, geobserveerde aansluiting, veilige command-/readbackstatus en zijn gemeten laadsessie; **ChargeableAsset** bezit uitsluitend type/naam, optionele SoC, doel, duur/kWh, deadline/Guest-expiry en bewezen aan dat voertuig toe te schrijven progress; **ChargeController** bezit het gezamenlijke elektrische budget, de strategie, de planner en de geaggregeerde waarheid. Zie de definitieve ownershipmatrix in §2 — dit is geen vierde eigenaar of tweede configuratiesysteem.

**Wat onbekend mag zijn:** SoC, voertuigfabrikant, capaciteit, prijs, PV, thuisverbruik, forecast en zelfs een voertuigprofiel zijn **optioneel voor de toepasselijke eenvoudige workflows**. Wat nooit wordt gegokt: elektrisch veilige belasting, actuele fysieke connector waar nodig, onafhankelijke command-/STOP-verificatie, exclusieve hardwarewriter, geldige site/circuitlimiet. De UI toont beschikbare acties en noemt de specifieke ontbrekende voorwaarde; geen globale Off-stand als vervanging van werkelijk ondersteunde functionaliteit.

**Twee representatieve generieke acceptatieprofielen (beide verplicht vóór Feature Complete):**

- **Minimale site:** schone HA, 1 geschikte smart plug/on-off Charger, 0 profielen of één Guest zonder SoC, geen PV/prijzen/robotix-entities; UI-configuratie volledig, beperkte duur-intentie, bronstatus en fysieke START/STOP **wanneer het geschikte toestel en het minimale onafhankelijke veiligheidsbewijs werkelijk kwalificeren**. Test ook het tegenovergestelde geval waarin alleen switch-state bestaat: zichtbare blokkering en nul fysieke writes, niet doen alsof dit een kabel- of energiebron is.
- **Rijke site:** schone HA, ≥2 verschillende native Chargers (Wallbox/Peblar of equivalente providers), Audi Q8/VW ID.4 of generieke OEM-SoC-bronnen, net-/PV-/prijsmetingen, 1/2/4/10 capaciteitscases; dezelfde drie Devices, dezelfde vijf-tab UX, één settings authority en één Executor, met extra bruikbare optimalisaties.

**Minimale site — zichtbare voorbereiding en blokkering (UC05/11/17, UI-OWNER-10):** In de bestaande Charger-view ziet een beheerder voor iedere **niet-toegewezen** Charger een formulier voor precies één eindige duur in minuten óf gemeten kWh, ook wanneer de veilige fysieke START nog niet kwalificeert. De input blijft als lokale, niet-uitgevoerde formulierdraft beschikbaar bij gewone sensorrefresh, maar wordt **niet** als actieve of persistente sessie, laadplan of uitgevoerd commando geregistreerd. De werkelijke START-knop is dan inactief met een concrete HA-kwaliteits-/veiligheidsreden (externe writer, ontbrekende commissioning, kabelbewijs, meting, stroomlimiet of verkeerde modus), zonder servicecall. Zodra alle vereiste evidence wél bestaat, gebruikt de knop exact dezelfde gevalideerde en gepersistente executor als alle andere manual requests; ongeldige XOR-limieten blijven afwijsbaar. Verwijderen/herbinden van de Charger of een gewijzigde site-config maakt de niet-ingediende draft ongeldig. Negatieve proef: één smart-plug-`switch` zonder gekwalificeerde fysieke connectie/meting → volledige UI, ingevulde duur, concrete HOLD, **nul** writes; fysiek geverifieerde geschikte on/off-laadmogelijkheid → werkelijk begrensde START/STOP met onafhankelijke readback. Geen nieuwe fysieke autoriteit of tweede command gateway.

**Persistence-recovery contract (UC23/26/29):** Een native HA control-state snapshot moet vóór toepassing volledig en transactioneel gevalideerd worden: completions, inflight, pause holds, accepted slots en session receipts worden pas samen geadopteerd nadat de gehele payload veilig is. Een beschadigde *latere* ontvangst mag geen gedeeltelijke intent-, pause-, geschiedenis- of grantwijziging veroorzaken; START blijft in HOLD tot expliciet gecontroleerd herstel. Toets een snapshot met geldige eerdere velden maar ongeldige laatste receipt, en controleer zowel onveranderde bestaande history/holds als nul fysieke writes en een ondubbelzinnige fouttoestand. Geldige historische IDs blijven op restart behouden; nooit een fysiek actieve sessie herstellen.

**UC-ankers:** UC01/02 (installeerbaar zonder bronnen), **UC05** (finite en zonder SoC), **UC11** (geschikte on/off / smart plug), **UC12** (volwaardige current capability), **UC13** (Guest), **UC17–20** (optionele, afzonderlijke inputkwaliteit) en **UC21/22/24** (niet-onderhandelbare fysieke veiligheid). FLEX-01/03/04/10/11/19 en UI-OWNER-05/10 toetsen deze exacte variatie. **Documentatie definieert de doelwerking, niet dat de huidige dev-bron deze minimumsite al fysiek accepteert.**

### 0.2 Scope-index — blijvende 29 functionele journeys

| UC | Functioneel resultaat |
|---|---|
| UC01 | Guided HA installation and clear onboarding |
| UC02 | Expert YAML import and one validated configuration |
| UC03 | One vehicle with one charger |
| UC04 | Several assets and chargers sharing a power budget |
| UC05 | Charging without vehicle SoC via explicit kWh or duration |
| UC06 | Target charge with Ready By deadline and feasibility |
| UC07 | Economy charging with valid tariff inputs |
| UC08 | Solar surplus charging with safe fallback |
| UC09 | Automatic charging across applicable goals/constraints |
| UC10 | Guarded Force Charge, Pause/Stop and Off |
| UC11 | Qualified on/off switching for suitable equipment |
| UC12 | Verified variable-current capability control |
| UC13 | Temporary guest vehicle or asset |
| UC14 | Today/Tomorrow 15-minute plan-vs-actual chart |
| UC15 | Measured charging history and attributable cost when data exists |
| UC16 | Native HA entities and safe automation entry points |
| UC17 | Optional, source-neutral Home Assistant inputs and power limits |
| UC18 | Missing or unreliable SoC handled as unknown |
| UC19 | Missing price data handled without fictitious prices |
| UC20 | Missing solar/grid measurement handled without invented capacity |
| UC21 | Disconnected or unidentified vehicle does not trigger charging |
| UC22 | Rejected command detected and real readback required |
| UC23 | Offline charger fails safe and recovers after verification |
| UC24 | Site or charger capacity limit enforces safe reduction/stop |
| UC25 | Expired previously active binding limit never fails open |
| UC26 | Restart, reload and rollback retain stable logical identities |
| UC27 | Infeasible deadline shown with explicit energy shortfall |
| UC28 | DST changes and negative tariffs handled by real intervals |
| UC29 | Add/remove/rebind without duplicate writer or loss of history |

**Statusregel:** de vroegere 17 S / 12 P was een tijdelijke broncodeclassificatie van 22 november, **geen** productscope of kwalificatie-uitkomst. Zet zulke aantallen niet in deze specificatie; actuele gaps en bewijslinks horen bij Issue #1 en het exact-head PR-/releasebewijs.

## 1. Individuele functionele use cases — UC01–UC29

### UC01 — Guided HA installation and clear onboarding
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Empty Home Assistant instance with integration available; no Robotix packages.  
**WHEN — handelingen:** Select Guided; set site, chargers, assets, optional sources; review; save/reopen.  
**THEN — verwacht gedrag / PASS:** One validated Config Entry, stable ChargeController/Charger/Asset devices, native sidebar, five tabs; unfinished wizard does not command hardware.  
**Negatief / fail-closed:** Invalid source, missing required identity, cancellation or duplicate integration ⇒ no entry or hardware write.  
**Bewijs:** HA flow result, Config Entry/registry IDs, negative flow and screenshots.

### UC02 — Expert YAML import and one validated configuration
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Fresh HA install or existing GUI-managed entry; complete data-only YAML.  
**WHEN — handelingen:** Select Configure entire charging site; paste Controller/Chargers/Assets and source bindings; review diff; save then edit again.  
**THEN — verwacht gedrag / PASS:** One GUI-owned validated Config Entry; no mandatory templates, packages, Robotix runtime or second authority.  
**Negatief / fail-closed:** Duplicate YAML keys, unsafe writer/commissioning, invalid sources, review cancel or file-owned edit ⇒ rejected before persistence.  
**Bewijs:** Input, review diff, saved entry revision, identity and zero physical command log.

### UC03 — One vehicle with one charger
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** One supported native Charger and one vehicle profile, with cable, control owner and independent power readback configured.  
**WHEN — handelingen:** Connect and explicitly identify the vehicle, choose Automatic and inspect plan and execution.  
**THEN — verwacht gedrag / PASS:** One bounded allocation, one physical writer, independently confirmed START/STOP and truthful Charger/Asset states; no duplicated power.  
**Negatief / fail-closed:** Disconnected or unconfirmed vehicle, unavailable control or readback ⇒ zero START, visible block.  
**Bewijs:** HA native entity changes, service trace, meter and Charger readback.

### UC04 — Several assets and chargers sharing a power budget
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** One or more compatible Chargers, with distinct vehicles and physical group limits.  
**WHEN — handelingen:** Connect two qualified vehicles, confirm each current plug and request concurrent charging.  
**THEN — verwacht gedrag / PASS:** One planner allocates only eligible chargers under site/phase/circuit/parallel limits with understandable per-vehicle reasons.  
**Negatief / fail-closed:** Fourth/unknown/duplicate vehicle, exhausted group budget, stale phase evidence ⇒ no overcommit or silent START.  
**Bewijs:** 15-min allocations, measured phase/circuit current, native commands and readbacks.

### UC05 — Charging without vehicle SoC via explicit kWh or duration
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Een Guest zonder OEM-account/SoC of helemaal geen geregistreerde Asset, met een geschikte on/off/smart-plug Charger of volwaardige EVSE. Er kunnen slechts minimale native meetwaarden zijn.  
**WHEN — handelingen:** Maak een optionele Guest aan of kies Charger-only; voer precies één eindige laadduur of echte kWh-vraag in; bevestig actuele fysieke sessie voor zover het betreffende hardwaretype dit vereist en vraag expliciet START.  
**THEN — verwacht gedrag / PASS:** Een minimale installatie kan zonder SoC/voertuigcloud worden ingericht; een gekwalificeerde eindige Charger-only of Guest-sessie gebruikt één veilige fysieke owner en eigen powermeting. Een tijdslimiet vereist geen kWh-meter; een echte kWh-limiet wel. Anonieme Charger-sessie houdt `asset_id=null`, nooit een fictieve auto.  
**Negatief / fail-closed:** Geen of twee eindige doelen, onveilige/ongeschikte smart plug, alleen `switch.on` als zogezegd kabelbewijs, geen onafhankelijke fysieke STOP/power-readback of ontbrekende exclusieve writer ⇒ geen START. Het apparaat en de GUI blijven wel configureerbaar; onbekende kWh blijven unknown.  
**Bewijs:** Actual time cutoff, physical STOP, power and receipt with null identity.

### UC06 — Target charge with Ready By deadline and feasibility
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Registered vehicle with known capacity/SoC or qualified finite energy goal, Ready By and charger capabilities.  
**WHEN — handelingen:** Set target and deadline; inspect next available quarter-hour schedule and execute.  
**THEN — verwacht gedrag / PASS:** Feasible schedule meets deadline; infeasible one reports energy/time shortfall before physical action.  
**Negatief / fail-closed:** Unknown SoC with no finite alternative, invalid DST deadline or missing capacity ⇒ no invented feasibility.  
**Bewijs:** Plan, timestamped inputs, readback and shortfall reason.

### UC07 — Economy charging with valid tariff inputs
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Bounded future intervals with explicit currency, unit, basis and freshness.  
**WHEN — handelingen:** Enable Economy and compare allocated cheap/negative/expensive intervals.  
**THEN — verwacht gedrag / PASS:** Price-aware scheduling uses real intervals; spot basis supports ranking but never effective billed cost.  
**Negatief / fail-closed:** Missing, stale, overlapping, mixed units or currency/invalid DST quote ⇒ no fictitious cheap price or cost.  
**Bewijs:** Original provider intervals, comparison, plan and qualified valuation receipt.

**UC07/UC17 source-neutral native tariff acceptance:** A selected native Home Assistant electricity-price sensor may already publish complete `today`/`tomorrow` arrays of timestamped `all_in` values in explicit `EUR/kWh` or `€/kWh`, without Robotix Energy, Basic EVSC, YAML templates or helper entities. Direct normalization accepts only complete 23/24/25-hour or 92/96/100-quarter local days with continuous actual UTC intervals, valid units, finite signed prices, source freshness and optional stale flag. No implicit missing quarters or future energy estimates. This provider's `all_in` represents **variable reference prices**, not verified settled invoices, fixed fees or capacity charges: the normalized quote basis is `variable_reference`, distinct from both wholesale `spot` and separately qualified `effective` billing tariffs. It may rank Economy intervals but cannot authorize all-in session bills or the persisted cost field. Overview must label this source as a **reference price**, and wholesale quote inputs as **spot price**, rather than presenting either as an unquestioned settled all-in tariff. Missing/invalid source states remain source-quality HOLD. Clean HA/native-provider positive and stale/DST/mixed/partial negative paths must pass before this provider route is accepted.

### UC08 — Solar surplus charging with safe fallback
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Qualified Solar intervals or fresh native signed grid export/direct surplus and electrical limits.  
**WHEN — handelingen:** Choose Solar; vary measured export/source quality; observe plan and command boundaries.  
**THEN — verwacht gedrag / PASS:** Only proven surplus is used, with near-term scope for live meters and guarded reduction/STOP when surplus disappears.  
**Negatief / fail-closed:** Stale solar, missing signed direction or absent capacity ⇒ no estimated tomorrow surplus or unqualified charging.  
**Bewijs:** Native W/kW source timestamps, plan intervals, real power/current and STOP.

### UC09 — Automatic charging across applicable goals/constraints
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Multiple charged/uncharged connected Assets with competing valid goals.  
**WHEN — handelingen:** Choose Automatic and advance 15-minute clock boundaries.  
**THEN — verwacht gedrag / PASS:** Eligible confirmed connections receive deterministic allocations; waiting/disconnected Assets retain intent but not executable slots.  
**Negatief / fail-closed:** Saved vehicle preference without plug confirmation, forecast-only slot or failed source ⇒ no command.  
**Bewijs:** Plan/forecast separation, grant IDs, HA service calls and readbacks.

### UC10 — Guarded Force Charge, Pause/Stop and Off
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Commissioned owner with physical switch/readback and known charger session.  
**WHEN — handelingen:** Request Force Charge, Pause, Resume and Off separately.  
**THEN — verwacht gedrag / PASS:** Pause persistently prevents new START and physically stops an active run; Resume lifts hold without hidden START; Off stops, readback confirms.  
**Negatief / fail-closed:** Unknown STOP/readback, restart/persistence failure or different owner ⇒ hold with no unsafe restart.  
**Bewijs:** Command outcomes, retained pause state, physical STOP/readback and restart.

### UC11 — Qualified on/off switching for suitable equipment
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Een native on/off Charger, waaronder een *elektrisch geschikte en correct beoordeelde* slimme stekker/relay voor het bedoelde laadapparaat, met native switch en onafhankelijk gemeten vermogen; de eenvoudige route heeft mogelijk geen OEM-SoC of laadpaal-kabelsensor.  
**WHEN — handelingen:** Commission exclusivity, START, reject/timeout and STOP.  
**THEN — verwacht gedrag / PASS:** Een enkele native switchwriter; geen verplicht fabrikant- of Robotix-bronpakket; minimale eindige bediening alleen waar apparaatgebruik, daadwerkelijke aansluiting/gebruikersconfirmatie, site-/circuitlimiet en onafhankelijk vermogen/STOP verifieerbaar zijn. De voor de gebruiker zichtbare actie wordt uitsluitend bij waargenomen power bevestigd.  
**Negatief / fail-closed:** Een generieke huishoudstekker is niet automatisch gecertificeerd voor EV-laden; ongeschikte belasting, ontbrekende source, onbewijsbare huidige sessie, concurrerende writer of geen echte readback ⇒ fysiek START geblokkeerd/unknown, niet gefingeerd succesvol. `switch.on` ≠ `connected`.  
**Bewijs:** Switch service log, power meter transitions, owner proof and rollback.

### UC12 — Verified variable-current capability control
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Variable-current Charger with proven phase/voltage/current step and separate current readback.  
**WHEN — handelingen:** Change setpoint while active; exceed bounds; reduce under power constraint.  
**THEN — verwacht gedrag / PASS:** Only supported step/bounds are sent via native current service; reported setpoint remains distinct from measured current; safe reduction/STOP.  
**Negatief / fail-closed:** Missing phase/current capability, stale ampere feedback or rejected setpoint ⇒ no false accepted current.  
**Bewijs:** Native setpoint service + independent actual ampere and group power.

### UC13 — Temporary guest vehicle or asset
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Temporary Guest zonder verplichte auto-OEM, SoC of capaciteit, met alleen naam/type, eindige duur of kWh-vraag en geldige expiry; een geschikte Charger met afzonderlijk fysiek bewijs.  
**WHEN — handelingen:** Create Guest, bind idle Charger, confirm physical connection, charge then expire/unassign.  
**THEN — verwacht gedrag / PASS:** Guest remains visible with expiry, gets active slots only when confirmed; expiry results in safe STOP, history retained.  
**Negatief / fail-closed:** No OEM/SoC, already occupied charger, expiry during active charge or unknown STOP ⇒ no identity guessing/replay.  
**Bewijs:** Guest native device, session receipt, expiry and Charger STOP.

### UC14 — Today/Tomorrow 15-minute plan-vs-actual chart
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Configured Today/Tomorrow 15-min source and Recorder history.  
**WHEN — handelingen:** Open all/single Charger/Asset chart; color by Vehicle/Charger; inspect proposed, accepted, actual and indicative.  
**THEN — verwacht gedrag / PASS:** Accurately labeled lanes and timestamp, stable ID hues, physically measured data only; 23/24/25-hour day preserved.  
**Negatief / fail-closed:** Unknown meter, unplugged saved vehicle or historical rebind ⇒ no fabricated actual, overlaid double totals or wrong owner color.  
**Bewijs:** 390/1024/1600 screenshots, tooltips, Recorder intervals and DST counts.

### UC15 — Measured charging history and attributable cost when data exists
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Charger input power/energy meter and immutable session-time vehicle association.  
**WHEN — handelingen:** Complete session, reassign vehicle and inspect earlier history and cost.  
**THEN — verwacht gedrag / PASS:** Past measured kWh and all-in cost are reported only with exact complete source coverage and effective tariff; old Asset attribution stays immutable.  
**Negatief / fail-closed:** Incomplete source, wrong Asset after rebind, spot-only price or failed STOP ⇒ unknown cost/identity rather than guessed figures.  
**Bewijs:** Recorder time-series, persisted receipts with timestamps, original vehicle IDs.

**UC15 engineering clarification — variable cost spanning tariff intervals:** A physically stopped, immutable session may cross multiple different effective-price intervals. Its original meter-based kWh receipt is authoritative and must never be silently rewritten using uniform session-average prices. The existing native Recorder historical power samples may yield a **separately labeled indicative variable energy cost** by integrating real observed power separately over every covered effective-price subinterval. This calculation can be shown only when *all* session instants have qualified source coverage, actual per-sample unit and freshness, one currency, nonoverlapping effective (not spot) prices, and a verified closed session plus metered energy receipt. Any gap, stale measurement, negative/unphysical power, mixed prices, overlapping quotes, incomplete session window, failed STOP or absent independent meter keeps this indicative figure unknown. It is not a verified billing amount and cannot overwrite historical `cost` or `cost_quality`; an all-in/billed amount still needs exact metered tariff-period energy and explicitly qualified fee coverage. Normal existing single-effective-interval receipts remain unchanged. No extra price or finance engine, HA entity, settings store, site template or required Robotix package.

### UC16 — Native HA entities and safe automation entry points
**Persona / eigenaar:** Resident/admin / MultiCharge  
**GIVEN — beginsituatie:** Native HA registry with owner-specific devices and role-based access.  
**WHEN — handelingen:** Read statuses as resident; admin changes mode/goal/assignment and invokes actions.  
**THEN — verwacht gedrag / PASS:** Charger/Asset/Controller native entities update near real time, readback status differs from request; admin-only writes, resident plan reads.  
**Negatief / fail-closed:** Resident physical service attempt, ambiguous target or stale revision ⇒ rejected without state change.  
**Bewijs:** Registry IDs, auth tests, independent state timestamps and ≤2s projection measurement.

### UC17 — Optional, source-neutral Home Assistant inputs and power limits
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Schone HA met nul, één of meerdere native Charger-/voertuig-/PV-/grid-/prijsproviders. Geen enkele optionele gegevensfamilie is verplicht om een lege site of een Guest-profiel te configureren.  
**WHEN — handelingen:** Configure source selectors on a fresh site and remove a source.  
**THEN — verwacht gedrag / PASS:** Eén bestaande source-normalisatielaag valideert alleen werkelijk gekozen units, bronbetekenis, timestamps, kwaliteit en fysieke limieten; rijkere inputs verrijken passende modi zonder eenvoudige workflows te blokkeren. Geen Robotix Core/Basic/Premium, `evsc_bridge`, handmatige templates/helpers of extra installatiestappen vereist.  
**Negatief / fail-closed:** Unknown provider semantics, stale signal, conflicting source ownership ⇒ unknown/fail-closed rather than inferred.  
**Bewijs:** Config Entry source IDs, native provider raw attributes and negative tests.

### UC18 — Missing or unreliable SoC handled as unknown
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Vehicle with missing/outdated SoC; optional finite kWh/duration request.  
**WHEN — handelingen:** Create charging intent and observe readiness/plan.  
**THEN — verwacht gedrag / PASS:** Unknown SoC displayed accurately; finite manual demand can work without inventing percentage.  
**Negatief / fail-closed:** Absent SoC and absent finite request ⇒ no fabricated energy demand.  
**Bewijs:** Source quality, Charger action eligibility and no-fake-SoC UI.

### UC19 — Missing price data handled without fictitious prices
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Price source unavailable or no future intervals; optional current quote.  
**WHEN — handelingen:** Select Economy and inspect plan/cost.  
**THEN — verwacht gedrag / PASS:** Missing prices remain unknown; current quotes are only current and never future tariffs or measured all-in cost.  
**Negatief / fail-closed:** NaN, invalid time zone/currency, gaps and stale price ⇒ no zero-price substitution.  
**Bewijs:** Source quality reasons, plan and historical receipt.

### UC20 — Missing solar/grid measurement handled without invented capacity
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** PV/grid meter omitted, stale, signed or out of range.  
**WHEN — handelingen:** Select Solar / inspect available capacity.  
**THEN — verwacht gedrag / PASS:** Source-based surplus only when qualified; unknown measurement is not 0 or unlimited capacity.  
**Negatief / fail-closed:** No real meter or undefined sign convention ⇒ no Solar START.  
**Bewijs:** Native measurement timestamps and physical power.

### UC21 — Disconnected or unidentified vehicle does not trigger charging
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Selected Asset and connected Charger may differ; prior identity may be confirmed.  
**WHEN — handelingen:** Unplug/replug, switch connected vehicle or trigger provider recreation/outage.  
**THEN — verwacht gedrag / PASS:** Only freshly witnessed/explicitly confirmed current connection can activate eligible vehicle; connected unknown remains distinct from saved selection.  
**Negatief / fail-closed:** Fast replug, missed event, stale status or other car ⇒ confirmation invalidated, zero automatic START.  
**Bewijs:** Ordered HA source event trace, connection epochs, plan and service log.

### UC22 — Rejected command detected and real readback required
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Native service may reject or fail; separate switch/current and power readback exist.  
**WHEN — handelingen:** START/STOP with rejected service, delayed readback, timeout and conflicting command.  
**THEN — verwacht gedrag / PASS:** Requested, accepted-unconfirmed, confirmed, rejected or execution_unknown statuses correctly correlate requests with physical truth; protective STOP issued as needed.  
**Negatief / fail-closed:** Service 200 response alone, unavailable meter or stale result never becomes confirmed.  
**Bewijs:** HA requests, native readback timestamps and STOP trace.

### UC23 — Offline charger fails safe and recovers after verification
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Charger offline/unavailable during active session, with pending identity and persisted control state.  
**WHEN — handelingen:** Force source loss and recovery; restart/replug.  
**THEN — verwacht gedrag / PASS:** Unsafe live charging is stopped when possible, previously confirmed identity not reused; recovery requires fresh source, idle/readback and new confirmation.  
**Negatief / fail-closed:** Lost STOP or unobservable power stays held/unknown, never silently resumes.  
**Bewijs:** HA source/provider outages and recovery session receipts.

### UC24 — Site or charger capacity limit enforces safe reduction/stop
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Site phase/circuit/parallel kW and qualified binding capacity, mixed Chargers.  
**WHEN — handelingen:** Start or increase load beyond constraints; reduce current or stop.  
**THEN — verwacht gedrag / PASS:** Hard limit never exceeded by approved commands; adjustable current decreases when qualified; otherwise STOP.  
**Negatief / fail-closed:** Stale binding or unverified wiring/phase ⇒ no fail-open or speculative surplus.  
**Bewijs:** Native phase/current values, source timestamps and executor trace.

### UC25 — Expired previously active binding limit never fails open
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Previously valid capacity/binding evidence expires while session is running.  
**WHEN — handelingen:** Wait beyond validity and recompute/advance plan.  
**THEN — verwacht gedrag / PASS:** Previous grant cannot override expired binding; observable hold or protective reduction/STOP.  
**Negatief / fail-closed:** Unchanged prior plan/green source CI never authorizes continuing unsafe load.  
**Bewijs:** Expiry boundary tests, physical current/power and STOP.

### UC26 — Restart, reload and rollback retain stable logical identities
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Configured native devices, Recorder identity/history and persisted incomplete intent.  
**WHEN — handelingen:** Reload/restart, upgrade/rollback, device rename/rebind.  
**THEN — verwacht gedrag / PASS:** Registry unique IDs and old history survive; no automatic START, silent command replay, orphan source or guessed session completion.  
**Negatief / fail-closed:** Corrupt persistence, missed event or unsafe unload ⇒ hold and explicit reconciliation/rollback.  
**Bewijs:** Before/after registry IDs, stores, receipts and rollback test.

### UC27 — Infeasible deadline shown with explicit energy shortfall
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Ready By with finite demand but insufficient verified charging capacity/time.  
**WHEN — handelingen:** Enter unrealistic deadline and inspect plan.  
**THEN — verwacht gedrag / PASS:** Explicit shortfall kWh/time, earliest feasible behavior, no deceptive 'ready' status.  
**Negatief / fail-closed:** Wrong source, DST shift, unsupported current, expired Guest ⇒ truthful unknown/block.  
**Bewijs:** Deadline math, 15-min plan evidence and UI text.

### UC28 — DST changes and negative tariffs handled by real intervals
**Persona / eigenaar:** Resident / MultiCharge  
**GIVEN — beginsituatie:** Real price intervals across DST jump and negative spot rates.  
**WHEN — handelingen:** Schedule today/tomorrow across spring/fall, compare spot vs all-in.  
**THEN — verwacht gedrag / PASS:** 92/96/100 genuine UTC quarters as applicable and correct local labels; negative prices remain negative, no invented gaps.  
**Negatief / fail-closed:** Duplicate local hour, missing interval or ambiguous currency ⇒ not flattened/guessed.  
**Bewijs:** UTC and local interval assertions, source tariff evidence.

### UC29 — Add/remove/rebind without duplicate writer or loss of history
**Persona / eigenaar:** Engineer / MultiCharge  
**GIVEN — beginsituatie:** Multiple stable Chargers/Assets, active or past sessions and concurrent admin clients.  
**WHEN — handelingen:** Add/delete/rebind, alter names, change vehicle from C1 to C2, restore prior config.  
**THEN — verwacht gedrag / PASS:** Exactly one saved assignment per Asset; only idle affected Chargers may move, no silent eviction, same device IDs and historical session-time attribution.  
**Negatief / fail-closed:** Busy/unknown Charger, lost measurement, stale revision or concurrent edits ⇒ no change, no ghost device, no writer duplication.  
**Bewijs:** Registry snapshots, optimistic revisions, Recorder receipts, physical command audit.

## 2. Owner-approved flexible Charger/Asset/identity scope

### Functionele verfijning: independent devices, idle-only reassignments, connected-only active planning and entity colors

**Authority / scope:** The owner clarified the previous FLEX requirements in this conversation: (1) ownership, source identity, readback and progress live on the **correct logical devices**, (2) one registered vehicle may be assigned to **at most one Charger at a time** but must be easy to move **when neither affected Charger is charging**, (3) a vehicle may be registered while **not plugged in**, (4) **only currently connected, correctly identified/explicitly confirmed vehicles may appear in active charging allocations**, and (5) the Charging Plan must communicate *which car / which Charger / when / power / status* intuitively with stable distinguishing **vehicle or Charger colors**. This clarification supersedes earlier FLEX wording about conditional disconnected vehicle power slots, automatic stop-and-swap while charging, and fixed-blue-only proposed vs fixed-green-only actual bars. It is a refinement of the existing UC01–UC29 + approved **five-tab** design, not a sixth view, new device type or independent charging service.

#### Concept, source-of-truth and Home Assistant Device ownership

| Existing canonical logical Device | Sole canonical ownership | Independent HA-native projection / acceptance | Must not own |
| --- | --- | --- | --- |
| **ChargeController** | Site policy/mode, electrical group and phase/circuit budget, 15-minute allocations, acceptance/revision/coverage, fairness/priority, aggregate measured power and plan reasons | One controller device with plan/status and source-qualified read-only Today/Tomorrow query; active candidate set calculated only from verified connected & attributed Charger sessions | Charger hardware state, car OEM SoC, second planner, raw meter copies |
| **Charger** | Stable charging point identity, native source bindings, real cable/occupancy status, physical on/off/current, voltage/phase/circuit capability, real power/energy and quality, exclusive physical writer, session activation/STOP confirmation and charger-level actual history | One logical Charger HA Device; one **authoritative saved asset assignment** (\`charger.asset\`, optionally null), separately exposed physical connection / current-session identity evidence, write/readback and last-session outcome; native provider retains underlying device | Car battery demand/target, OEM vehicle identity inferred from cable, duplicated provider controls |
| **ChargeableAsset / Vehicle** | Stable vehicle identity, selected SoC source/provenance, target, portable kWh/duration intent, priority/Ready By, expiry for Guest, verified delivered progress and remaining need | One logical Asset HA Device even while unplugged/unassigned, with its charger shown as **derived relationship** (not a second authoritative assignment editor); own readiness/intent state and status \`unassigned / waiting / connected-verified / charging / unknown\` | Physical EVSE state or command write, independent second charge plan |
| **Existing HA Recorder + MultiCharge session receipts** | Recorder owns original physical measured power history; MultiCharge stores only session start/stop, source coverage, asset ID **at the time**, Charger ID, qualified energy and attribution evidence | Charger actuals are always safe to display with the original Charger ID; asset history is exposed only where the **time-bounded session association** is confirmed; absent identity stays \`asset_id=null\` | Rewriting old samples with current assignment, a second energy ledger, copying vendor devices |

**Association/cardinality rules:** Each registered Asset has **zero or one selected Charger**; each Charger has **zero or one selected Asset** at a time. Unassigned Chargers and unassigned/unplugged Assets are fully supported, without creating or deleting logical devices to change pairing. Use the one existing Config Entry assignment authority and an explicitly verified **connection-session association** in the existing runtime/HA Store, rather than an independent assignment subsystem. Distinguish saved preference, physical connector presence and verified/explicit user-confirmed vehicle identity; all three may differ. At a physical disconnect, source uncertainty or an unexpected replug, invalidate prior connection-session identity evidence. An ordinary remembered Charger preference is **not** vehicle identification; it can be preselected in UX but cannot silently authorize automatic physical charging.

**Physical safety / reassigning:** Assign/unassign/change the selected Vehicle while the previous and destination Chargers are **idle, physically confirmed not charging and have reliable readback**; protect concurrency using the existing revision/admission lock. If one affected Charger is charging, the rebind action must be **rejected with a clear reason** and an independently available explicit STOP action; never execute hidden STOP + transfer + restart in one click. Unaffected Chargers may continue charging; site-wide electrical limit changes require an appropriately wider safety hold. A confirmed STOP closes the original session, freezes historical attribution and delivered progress **before** an explicit idle-state rebind. On uncertain STOP, power readback unavailable, disconnected backend or competing actor: no rebind/START, visible HOLD until reconciliation. A vehicle cannot be actively planned by two Chargers. A saved vehicle can switch Chargers and keep its **asset-owned** outstanding kWh/deadline, but verified delivered kWh follows the asset; never replay a completed request or assume missing energy was 0.

**Active vs waiting vs history (binding rule for the planner):**
1. **Active future plan candidate** = Charger source currently verifies connected **and** asset attached to this connection is independently identified or explicitly selected/confirmed for this connection session **and** has a validated outstanding need/deadline **and** the one physical owner + budget/capability eligibility passes. If any gate fails, **no proposed/accepted future power slots** for that vehicle. Merely selecting a Charger or saving a vehicle without plugging it in is never enough.
2. **Not connected**: vehicle stays in Chargeable Assets and its intent persists, status \`Waiting for connection\`; it may be listed as a non-energy **pending intention** below the chart, but no future kW bars, no accepted slot, no measured actual and no phantom shortfall attributed to a physical charger for that waiting vehicle. Recompute after verified connection.
3. **Connected, identity unknown**: Charger displays \`Connected · vehicle not identified\`; it is not automatically relabeled as the last selected car. A current-connection manual confirmation can qualify a known/Guest asset; no OEM or SoC is mandatory if user gives a verified finite kWh/duration request.
4. **No registered vehicle**: 0-Asset setup, independent Charger state and empty plan are valid. A connected qualified Charger can allow an **explicit, bounded, manual Charger-only one-off** without a vehicle record if this existing UC05/UC10/UC21 scenario is implemented; receipt \`asset_id=null\`, history and actual charger power stay on Charger, and it **does not create a fictitious Vehicle nor a vehicle-colored automatic plan**. If no connection/readback/limited demand, no START.
5. **After disconnect**: remove **future** allocation immediately, preserve historical actual/accepted energy for the elapsed periods under the immutable session-time association; newly disconnected vehicle need not disappear from history. A source 'unknown' is not the same as 'disconnected' or zero.

#### Owner-directed Charging Plan UX: intuitive color-coded identity

Keep exactly **Overview → Charging Plan → Chargeable Assets → Chargers → Settings**. The prior fixed-blue Planned/fixed-green Actual palette is superseded for **identity-distinguishable series only**, by this express owner requirement; do not redesign the rest of the five-screen baseline.

- **Default visual story:** Today/Tomorrow, current time, all Chargers (or select specific Charger/Asset), physical connection/identity status, **which car → which Charger**, per 15-minute local time slot, allocated kW, estimated completion/Ready By and a one-sentence reason for deferral/priority/shortfall. One identifiable series per Charger/vehicle; do not collapse four Chargers into indistinguishable same-color overlay bars.
- **Color dimension:** toggle **Color by Vehicle** (suggested default) / **Color by Charger**, using a deterministic, stable, theme-aware and contrast-tested palette keyed to the **immutable logical ID**, not list position or display name. One color dimension at a time; same ID retains color after reorder/rename/rebind and across Today/Tomorrow. Guest has a visible name and distinction; anonymous/unattributed uses neutral with explicit label. With 10+ series provide direct text labels and accessible line/border/pattern distinctions, not reliance on color alone.
- **Measurement semantics independent of identity hue:** proposed = lighter/hatching or translucent entity-colored bars, **physically accepted** = strongly filled/outlined entity-colored bars, **measured** = separately solid/marked entity-colored physical actual for elapsed Recorder-covered intervals. Tooltips/legend/ARIA/text must say Proposed / Accepted / Measured and show \`Vehicle · Charger · time · kW\` and source quality. Do not turn a proposal into a measurement or count one time-slot's power twice. The optional qualified price line stays visually distinct and on a properly labeled price scale; null/no data remains a gap, never a 0 kW bar.
- **Readability:** selectable per-Charger lanes or an accurately stacked All Chargers overview, never physically overlapping unlabelled series or double-counted totals. A small compact legend contains identity color chips **and** one independent status key; on mobile, labels and interactive detail remain legible without horizontal page overflow. 15-minute time boundaries and local 23/24/25-hour DST day handling remain true. Past physical actuals may show cars now unplugged, but **future plan only includes currently connected confirmed cars**.
- **UX actions:** from ordinary Charger or Chargeable Asset cards, make **Assign / Change / Unassign** straightforward when safe and idle; show physical connection separately and request explicit current-connection confirmation when necessary. Saved but disconnected vehicles remain easy to find. No vehicle should be a first-class **choice** rather than an error. Guest can be a temporary named asset with expiry/finite goal. Uncommissioned controls stay unavailable with reason.
- **Acceptance screenshots/tests:** same approved real-HA fixture and 390×844 / 1024×768 / 1600×900, light/dark, but include 0 assets, two unplugged saved vehicles, two simultaneously connected known vehicles, connected identity unknown, a Guest, a physically running charger that blocks reassign, a car moving from C1 to C2, and 4 / 10 unique Charger series. Verify color persistence across rename/rebind/day, distinguishability with color-vision deficiency, status patterns, tooltip exact attribution, no future unplugged bars or false actuals. Retain source-only vs real-HA-browser evidence labels.

#### Executable acceptance journeys (additional positive AND complementary negative/failure tests)

| Case | Exact user scenario | Required observable result | Existing UC |
| --- | --- | --- | --- |
| FLEX-01 | Install C1/C2, **0 registered cars**, both unplugged | Valid installation, both physical logical Chargers visible and independently monitored, five tabs available, no active kW plan and no automatic command | UC01/03/16/21 |
| FLEX-02 | Cars A/B registered with targets, C1/C2 both **unplugged** | Show A/B intent + selected preferred Charger, **zero active future power slots**; no phantom planned shortfall/physical actual; waiting state; remember settings | UC03/09/14/21 |
| FLEX-03 | C1 plugged, physically qualified, **no car profile**, explicit 2.0 kWh manual one-off | Charger-only verified limited actuation if energy meter and safety gates pass; receipt \`asset_id=null\`; measured power on Charger lane, no vehicle inferred or car-colored future auto plan | UC05/10/11/15/21 |
| FLEX-04 | Same as FLEX-03 with 30-minute bounded manual demand and no energy meter | Qualified bounded charger-only run; STOP on time; report kWh \`unknown\`, no fabricated value or price; no automatic plan for an invented car | UC05/10/15/22 |
| FLEX-05 | C1 has selected car A but physical **cable off or unknown** | No proposed/accepted active slots for A; physical START denied with zero native write calls; missing-cable vs unknown-source clearly distinct | UC09/10/21/22 |
| FLEX-06 | A on idle C1, user chooses idle C2 (C2 unplugged) | One idle-only atomic reassign; A now selected on C2, C1 is 'No vehicle', original logical IDs/history unchanged; A stays **waiting** until real C2 connection and identity confirmed | UC03/04/16/29 |
| FLEX-07 | A requested 12.0 kWh, C1 measured delivered 4.0 kWh and physically stopped, idle-reassign to C2 and plug/confirm A | C2 must plan at most **8.0 kWh verified remaining**; missing delivery proof triggers HOLD/reconciliation instead of resetting to 12.0; never two active Charging assignments | UC05/06/09/15/29 |
| FLEX-08 | A/C1 and B/C2, C1 physically charging, user clicks Swap/Reassign | Action is **rejected, no hidden STOP**. UI explains manual Stop C1 first. Only after independently confirmed STOP and idle state may user reassign; C2 unaffected if not part of change | UC04/10/22/24/29 |
| FLEX-09 | A's past C1 charge completed; C1 selection later changes to B | Historical Recorder actuals + confirmed receipts remain A-at-that-time; new B data only after new connection-session proof; no current-binding rewrites | UC14/15/26/29 |
| FLEX-10 | C1 physical cable ON, current vehicle unknown, saved A is selected | UI says 'Connected · vehicle unknown'; **A not automatically active-planned**. Explicit user confirms actual connected A/B or chooses bounded anonymous charging | UC18/21/22 |
| FLEX-11 | Create temporary Guest G (no OEM/SoC), finite 3 kWh goal, expiry, physically connect/confirm G to idle C1 | Visible guest/expiry/selected Charger, guest appears in **active future plan only after connection/session confirmation**, standalone from permanent A/B; measured history G-scoped | UC05/13/16/29 |
| FLEX-12 | Guest G expires during charge or after unplug | Protective STOP on expiry with physical readback; historic Guest receipt preserved, no silent restart/reassignment; expiry does not delete source device | UC10/13/15/22/29 |
| FLEX-13 | Disconnect or source becomes unavailable during active charging | Guarded STOP, visible unknown until independent proof, no fictitious successful receipt or restart; no future slots for disconnected vehicle | UC21/22/23/26 |
| FLEX-14 | C1 comes back online after outage; A was formerly selected but not independently identified after replug | Revalidate source, preserve IDs, do not infer 'A reconnected' solely from prior selection; no automatic charging until current plug session confirmed | UC21/23/26 |
| FLEX-15 | C1–C4 mixed on/off/variable, A/B connected-confirmed, C3 empty, C4 guest unconfirmed | Allocate group/phase/circuit budget only to eligible A/B; exclude empty/identity-unknown C3/C4; never count the same car twice; physical writer exclusive | UC04/07/08/09/12/24 |
| FLEX-16 | Guest removed after STOP, A renamed/rebound, native sensors edited | Stable Charger/Asset logical IDs and recorded source provenance; no ghost devices, no historic reassignment; optional deleted asset history still scoped to old ID | UC13/15/26/29 |
| FLEX-17 | Two clients concurrently assign A to C1 vs C2 while idle | Optimistic revision admits at most one winner; loser gets refresh/retry; no dual binding/physical write | UC16/22/26/29 |
| FLEX-18 | C1 cable goes off/on; a different car physically plugs in without identification metadata | Prior session identity invalidated; no silent active plan for former car; ask current-plug confirmation, or support bounded unattributed manual action | UC09/21/22 |
| FLEX-19 | Guest/anonymous Charger demand with missing tariff, PV, signed prices or DST transition | Real safety and strategy semantics; unknown price never zero; no fictional energy/cost; correct UTC 15-minute intervals/local timezone presentation | UC05/07/08/19/20/28 |
| FLEX-20 | Real HA chart: 2 attached cars, 2 unplugged, 1 Guest, 4/10 Chargers | Only connected-confirmed vehicles receive prospective colored bars; color-by-Vehicle or Charger preserves IDs; vehicle↔Charger label visible; separate proposed/accepted/actual styles; accessible 390/1024/1600 dark/light, no overdraw or double sum | UC01/13/14/16/21/29 |
| FLEX-21 | Basic EVSC/Mobility currently controls same native EVSE | Preserve existing physical writer until exact verified exclusive handoff, source IDs/history/settings and rollback; no test-run authorization to energize hardware | UC11/12/22/24/26/29 |

## 3. Native owner state, events en waarneembaar SET-resultaat

### Functionele eis: near-real-time native sensor for every SET/action, including controller aggregate

**Owner instruction:** every supported physical or settings SET/action must have an independently observable native Home Assistant state on its **owning logical Device**, plus an authoritative **ChargeController-wide readout** updated **near-real-time**. This is an acceptance invariant of the existing UC01–UC29 and FLEX-01–FLEX-21, especially UC11, UC12, UC14, UC16, UC21, UC22, UC24, UC25, UC26 and UC29, not an additional implementation owner, database, physical controller or new workflow.

**Required canonical mapping (sensor names represent native logical entity capability; HA may assign entity IDs on installation):**

| SET/action | Primary concept / confirmation | Controller-level observable |
| --- | --- | --- |
| Mode SET | ChargeController: validated mode reloaded from Config Entry; never claim success on request alone | \`Charging mode\`, \`Settings revision\`, \`Last settings action\` expected/observed revision |
| Site max kW, phase limits, max parallel, source selection | ChargeController: authoritative site config and qualified source capacities, not estimated available power | \`Settings revision\` attributes, \`Plan status\`, independently measured total \`Actual power\` |
| Vehicle kWh/duration, target SoC, priority, Ready By, Guest expiry | ChargeableAsset: \`Charging intention\` + observed qualified battery/quality; no physical actuation implied | \`Last settings action\` scope/target/fields + \`Settings revision\`, \`Plan status\` on recomputation |
| Charger/Vehicle assignment, including No vehicle and idle-only switch | Charger: \`Selected vehicle\` (saved assignment), distinct \`Connection\` (physical); Asset derives its selected Charger | \`Last settings action\` and \`Settings revision\`, \`Connected chargers\` with true physical source quality |
| START, STOP, protective STOP | Charger: \`Command status\` requested→confirmed/rejected/execution_unknown and independently observed physical power/STOP | \`Last physical action\` with source Charger/request/readback/reason, \`Action health\`, \`Charging chargers\`, \`Actual power\` |
| Set adjustable current | Charger: \`Confirmed current setpoint\` vs separate independent \`Actual current\` sensor, source quality/time | \`Last physical action\`, \`Action health\`, actual aggregate kW and plan status, never request=current assumption |
| Physical connect/unplug/offline/stale | Charger: native Connection/power/current sensor with observed_at/quality; ChargeableAsset does not fake identity | \`Connected chargers\`, \`Charging chargers\`, \`Actual power\`; unknown is not 0; safe action health/hold |
| Quarter-hour plan allocation / deadlines | Controller: source-backed \`Plan status\` and bounded plan query; Charger/Asset states remain owner projections | \`Plan status\`, proposed vs accepted vs measured only from qualified evidence; no giant 48h sensor attribute |

**Near-real-time, source-first behavior:** subscribed HA sensor state-change and executor request/physical confirmation events should publish the updated logical and aggregate HA sensor values without relying on a page refresh or the 60-second fallback timer. Operational *target* for exact HA/browser qualification: **≤2 seconds from a locally observable HA source or accepted command outcome to emitted owner+controller state-change**, independently timestamped; physical EVSE/provider confirmation can take longer and **remains pending/unknown until fresh readback**. No guaranteed subsecond physical completion when hardware/provider is slower. Settings updates are only \`confirmed\` when the newly loaded Config Entry revision matches the requested revision; \`accepted_unconfirmed\` on pending reload, \`rejected\` on invalid/unsafe change. Source \`observed_at\`, requested_at, readback_at, request correlation, freshness and quality travel to sensors.

**Safety and consistency checks:** 0/1/2/4/10 Chargers; first successful action and rejected same action; concurrent independent Chargers; unknown/disconnected source, physical on/off mismatch, current feedback late, source stale, provider unreadable, persistence/restart hold, rejected/failed settings reload, idle reassignment without stopping unrelated Charger, Guest, absent vehicle, error/rollback. Aggregate connected count becomes **unknown** when one required connection source lacks quality; aggregate charging count and actual power become **unknown** on incomplete independent power coverage. A real measured 0 is 0; no inferred 0. Persistent canonical logical IDs must not change on name/assignment changes; vendor HA devices retain their original entities and history. Source tests are not installed HA timing, real EVSE, mobile/browser or complete UC acceptance.

## 4. Indicatieve forecasting zonder reservering of uitvoering

### Functionele uitbreiding: configurable Vehicle–Charger labels and strictly indicative disconnected forecasting

**Latest owner clarification (same chat, replaces the overly broad statement "unplugged vehicles have no future bars"):** Only physically connected and current-session-confirmed vehicles are eligible for **active, executable-candidate** proposed/accepted charging slots. However, the existing **Charging Plan** is allowed to show **clearly segregated, non-binding and non-executable indicative what-if forecasts** for registered vehicles not yet connected. The two layers must be calculated and visually labelled differently. The requested default identity label is **Vehicle + Charger**, e.g. "Audi Q8 · Wallbox White", with user-configurable **Vehicle / Charger / Both** and independent **Color by Vehicle / Charger**. No new tab, domain device, planner, controller or physical owner.

**Rules:** Use the one Controller planning engine and run active demand allocation first; only then simulate hypothetical disconnected demand using **residual** site/phase/circuit/max-parallel electrical capacity after those active quarters. Forecast is allowed to reflect user-entered expected plug-in time (\`expected_connection_at\`, ISO time with timezone); otherwise show the explicit assumption "**if connected now**" (never infer arrival probability or actual cable state). Future connected/confirmed requests always win; indicative slots never reserve group kW, affect active scheduling, become physically accepted slots, enter command/grant/replay logic, or produce actual energy/cost. Forecast must be excluded when cable quality is unknown (not proven disconnected), demand/source/capability missing, deadline infeasible or mode Off, with truthful non-numeric reason. All guest expiry and per-asset/charger uniqueness rules still apply.

**UX and native contract:** The existing 5-tab Charging Plan shows a visible per-Charger timeline and actual selected Vehicle–Charger combination, with named identity-colored planned/accepted/historic status and a **dashed/transparent labelled "Indicative – not connected"** row that cannot be confused with real charging. The selected fields \`plan_label_mode=vehicle|charger|both\`, \`plan_color_by=vehicle|charger\` and \`show_indicative_forecast=true|false\` belong to the existing controller Config Entry authority (not frontend-only hidden persistence). Display qualified price as independently scaled context only. Show real past physical power from Recorder under Charger; only attribute it to a specific Vehicle when a **session-time confirmed receipt** proves that interval, NEVER using today's selected vehicle. Return \`forecast_slots\` separately from active \`slots\`, with \`status=indicative_only\`, \`may_execute=false\`, \`reserves_capacity=false\`, bounded assumptions and forecast reasons. Only a compact forecast summary belongs on the native Controller \`Plan status\` sensor.

**Executable acceptance extension mapped to existing UC04/05/06/07/08/09/13/14/15/16/18/19/20/21/24/26/28/29:**

| Case | Setup/trigger | Required observable acceptance |
| --- | --- | --- |
| FORECAST-01 | A connected + confirmed on C1; B saved but disconnected on C2 | A gets only normal active proposal; B gets separate dashed indicative scenario; **no active/accepted B slot, no hardware command for B** |
| FORECAST-02 | Forecast B toggled on/off with unchanged sources | Active plan slot IDs/times/kW/revision/physical eligibility stay exactly unchanged; no physical capacity reserved |
| FORECAST-03 | Site 4kW, connected A needs 4kW at quarter T, B disconnected wants 2kW | B must not receive 2kW at T; residual capacity is zero; forecast may place B later if constraints allow |
| FORECAST-04 | Two connected plus one disconnected on shared phase/circuit with strict ampere limits | Forecast+active sum in a hypothetical quarter does not exceed phase/circuit/parallel/binding limits; failure is indicated, not silently overbooked |
| FORECAST-05 | B disconnected, expected plug-in 19:00 entered | Forecast earliest timestamp >=19:00 local converted accurately to UTC; no slot before expected arrival |
| FORECAST-06 | B disconnected, no arrival time known | Explicit "if connected now" what-if, **not** a predicted 19:00 arrival or a probability score |
| FORECAST-07 | B connection sensor unavailable/stale, no Charger selected, missing demand/source or Mode Off | Do not fabricate numeric forecast for unsupported cases; show context/unknown/conditional reason, no real kW |
| FORECAST-08 | User selects Vehicle, Charger, then Both; changes color grouping | Chosen labels and color scheme persist via authoritative Config Entry reload; chart maintains stable canonical identity hue, accessible distinction and meaningful tooltip |
| FORECAST-09 | C1 previously charged vehicle A, now bound to B | Old confirmed Recorder intervals still belong to A where proven; unknown intervals remain charger-only; no rewriting by current B |
| FORECAST-10 | Mobile, tablet, desktop, light/dark, 1/2/4/10 Chargers, Today/Tomorrow/DST | Visible paired identity; per-Charger lanes without overlapping series; future forecast clearly dashed, source/price quality and 92/96/100 intervals correct; no hidden scroll over page or invented actual |
| FORECAST-11 | B physically connects while forecast is displayed | Recompute physical-source state; retire B's forecast; B enters normal active planning **only** once current-plug identity is confirmed; never blindly promote a forecast into executed command |
| FORECAST-12 | Source/controller offline, unexpected session stop, user tries Force Charge | No forecast may bypass the existing one-writer admission, physical STOP/readback, stale/unknown, persistence or restart HOLD checks |

## 5. Per-device native voorkeuren, kleuren, labels en talen

### Functionele UX-eis: native preferences, per-device colors and short multilingual labels

**Owner instruction:** EVERY regular preference is edited through its native HA `select`, `number`, `datetime` or `text` on the correct existing **ChargeController**, **ChargeableAsset/Vehicle** or **Charger** Device. The five-tab card consumes these exact Registry entities; **no parallel Option Flow setter, cloned data store, JS-local setting, second physical writer, fake Charger entity or additional logical Device**. Expert source binding, wiring, phase/circuit proof, commissioning and installation remain governed HA setup, never uncontrolled daily preference actions.

**Exact owner / state contract:**
- **ChargeController**: Mode, color dimension (Vehicle or Charger), label mode (Vehicle, Charger or Both, default Both), Forecast visibility native Selects; site maximum kW, maximum concurrent Chargers native Numbers; site name native Text. Plan and physical outcome diagnostics remain source-backed read-only native sensors.
- **Each Vehicle/ChargeableAsset**: its own `plan_color` Select, vehicle type, recurring Ready By Select; target SoC, requested grid kWh **XOR** duration, priority, max charge kW, battery capacity, efficiency native Numbers; Ready By, expected plug-in, Guest expiry when applicable native DateTimes; name native Text. Unassigned/unplugged Vehicle remains a full HA Device, does **not** receive active future slots.
- **Each Charger**: own `plan_color` Select, `Selected vehicle` Select including `none`/No vehicle, and name Text. Physical connection is a **separate** source-qualified native Binary Sensor; current and power remain Charger-owned measured evidence, never inferred from selected Vehicle. Changing selected car preserves one authoritative `charger.asset`; a car cannot be selected on two Chargers. Idle-only reassign never stops unrelated Chargers; unsafe/busy physical state refuses changes.
- **Color defaults**: Automatically unique, stable palette per owner category (Vehicle vs Charger, at least 10 of each), independent of order, rename, reassignment, Today/Tomorrow. User may explicitly override to any permitted color; persist that override on the correct Device via the one Config Entry authority, not in frontend memory. Match plan identity colors to the owner native select even for clearly separated dashed **Indicative** disconnected forecasts. Actual physical samples without proven vehicle identity remain neutral in Vehicle-color mode.
- **Translations / statuses**: User-facing labels are compact and comprehensible, not programmer comments, source enum strings, request-ID/error-code banners or multi-sentence instructions. Native HA select/number/datetime/text/sensor titles use translations (EN/NL/FR, plus DA/NB/SV native HA locales if translations exist); the bundled card has EN/NL/FR short labels. Backend machine enums and reason attributes can remain stable for existing automations, but ordinary visible state is localized when HA translation contract allows. Screen readers get the meaningful text as well as color/pattern; explanatory diagnostics stay in HA device details.
- **Access/safety**: These entity changes use exactly the same validation/revision/HA Config Entry and guarded executor lock as before. Display-only palette/label/forecast settings must not reload/STOP a charging EVSE. Physical limits, target/intent and pairing require the existing fail-closed safety gates. A completed service call is not positive physical confirmation.
  
**Executable owner acceptance cases (add to existing UC01–UC29/FLEX/FORECAST acceptance; not a new issue):**

| Test | Observable acceptance |
| --- | --- |
| UI-OWNER-01 | Create 10 Vehicles + 10 Chargers: each set has 10 distinct default colors; no copied source devices or new state store |
| UI-OWNER-02 | Change Vehicle A's color via its HA Select: Active Vehicle-colored plan and dashed forecast reflect it; rebind/rename/reload do not reset it |
| UI-OWNER-03 | Change Charger 2 color via Charger HA Select while unrelated Charger 1 charges: visible Charger-colored plan changes; no hidden STOP, no plan capacity reservation |
| UI-OWNER-04 | Switch Color by Vehicle/Charger and labels Vehicle/Charger/Both using Controller HA Select: values persist and immediately show correct combination, no duplicate preference authority |
| UI-OWNER-05 | Change target, finite kWh OR duration, priority, arrival and Ready By via Vehicle native Number/DateTime: source readback and controller planning update; user cannot silently set contradictory kWh+duration |
| UI-OWNER-06 | On an idle Charger choose a different Vehicle or None via native Charger Select: exactly one current assignment, prior session history unaffected, no phantom connection/active slots |
| UI-OWNER-07 | Try to change physical assignment while either affected Charger is charging, physical stop uncertain or source stale: safely rejected; unrelated active charger continues |
| UI-OWNER-08 | Native EN/NL/FR device states and card labels: simple 1–3 word labels for Charging, Stopped, Connected, Disconnected, Waiting, Forecast, Unknown; no technical developer sentence or raw error codes on primary UX |
| UI-OWNER-09 | Native HA EN/NL/FR/DA/NB/SV translation metadata and exact entity IDs survive HA reload/restart/rename; no guess by entity ID or name |
| UI-OWNER-10 | Source temporarily missing, charger empty, anonymous/Guest: no invented actual, car connection or future executor slot; diagnostic attributes remain available without alarming normal users |

## 6. Kwalificatie, evidence en statusregels

Per UC en elk corresponderend FLEX/FORECAST/UI-OWNER-scenario registreert het bestaande issue/PR/testbewijs de exact geïnstalleerde HA- en MultiCharge-versie, commit SHA, native bronentity en observed_at, eigenaar van fysieke sturing, pre/post service en werkelijke readback, een positief en negatief scenario, screenshot/video bij UX, resultaat `PASS|FAIL|BLOCKED|NOT_RUN`, afwijking en rollback. **Een code-/CI-PASS is geen eindgebruikersacceptatie.** Onvoldoende hardware- of browserbewijs blijft zichtbaar BLOCKED/NOT_RUN, nooit stilzwijgend afgeboekt.

**Acceptatiematrix:** lege installatie, 0/1/2/4/10 gemengde Chargers en Assets, 0-car anonieme one-off, Guest/SoC-loos, idle/actieve rebind, deadlines, fase/circuit/max-parallel, on/off en ampère-readback, prijs-PV-DST, onbekende/offline/restart, concurrente HA-admins, 390×844 / 1024×768 / 1600×900 licht/donker, acht ondersteunde talen. Laat de bestaande native aansturing intact tijdens TEST; een kwalificatie op Wessels vereist afzonderlijk bewijs van één fysieke writer, expliciete autorisatie en veilige rollback. Wessels-voertuignamen, leveranciers en specifieke entity IDs zijn acceptatiedata, geen generieke publieke dependency.

**Actuele technische en veldstatus (geen snapshot hier):** [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1), [Draft PR #9](https://github.com/npinguin/robotix-multicharge/pull/9), [Validate workflow](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml) en publieke [Releases](https://github.com/npinguin/robotix-multicharge/releases). MultiCharge mag niet Feature Complete worden genoemd vóór echte UC01–29-eindacceptatie en afzonderlijk vrijgegeven release-/sitegates.
