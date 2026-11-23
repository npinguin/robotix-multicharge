# Architecture and user experience

## Purpose and ownership

Robotix MultiCharge is an independent Home Assistant integration for coordinating electrical charging. It starts with cars but can support other rechargeable mobility assets when their real charging capabilities are known.

| Logical object | Responsibility |
| --- | --- |
| `ChargeController` | One coordinated plan for a group of charge points and a configured charging power ceiling |
| `Charger` | The logical charge point, its supported controls, assigned asset and physical readback |
| `ChargeableAsset` | The object needing energy, its requested amount, target and Ready By deadline |

One Controller coordinates its Chargers. A Charger has one authorized physical command owner. A logical association is not evidence that a particular vehicle is physically connected or identified.

The original Home Assistant integrations keep ownership of the physical devices, source data and their entity IDs. MultiCharge exposes stable logical charging devices without copying or reparenting the source devices.

## Charging Asset type and effective charging power

**Owner clarification, 22 November 2026:** Keep exactly the existing three logical HA concepts: `ChargeController`, `Charger` and `ChargeableAsset`. **No separate Vehicle, Bicycle or other charge-domain module/device.** The existing `ChargeableAsset.kind` is the native, device-owned editable `select.kind` (car, bicycle, motorcycle, scooter, other), translated as **Asset type**. It is **taxonomy, not charging physics**: the same demand model, source qualifiers, charger electrical limits, physical writer and timetable serve all supported kinds. Do not infer SoC, connector availability, session identity, battery losses or specialized charge curves from the type. A bicycle can request kWh/duration without an OEM battery sensor. Additional type-specific capabilities need separate evidence and user approval; never silently branch the planner on a display label.

**One real power observation, two owned HA views:** The physical provider retains the authoritative `Charger.power_entity`, expressed as fresh W/kW and normalized once by the existing `source_evidence.number` reader. The existing Charger native power sensor `robotix_multicharge:charger:<id>:power` retains its Unique ID and projects this actual **charger-side** measured power. The new Charging Asset native power sensor `robotix_multicharge:asset:<id>:power` reuses the exact same `Evidence` object **only when** the one existing executor has a confirmed active session naming that Asset on the assigned Charger, and its current cable source is positively verified connected. A selected/saved assignment, hypothetical forecast, historic receipt or unknown connection is never sufficient proof for live Asset attribution. No second meter, device or separate charging-power estimation engine is introduced.

**Measurement semantics:** Both HA sensors are labelled **Effective charging power** in the supported languages, meaning *physically observed charger-side charging power at the selected measurement point*, **not** net DC power delivered to a battery or charge efficiency–adjusted storage power. The source entity ID, source timestamp, quality and attribution basis remain visible as entity attributes. If the source is absent, invalid, stale or not attributable, the sensor is **unknown/unavailable**, not a made-up zero or planned kW. A genuine source reading of 0 is preserved when supported and attributed. Asset projected kW becomes unknown as soon as the plug is disconnected, assignment/session provenance disappears or the source loses quality; Charger raw physical power remains independently reported. Existing Recorder history remains owned by the charger/source and cannot be relabelled by a later assignment. This is source-observation transparency, not a replacement for physical session commissioning.

**HA native ownership and languages:** Native Controls/Config/Sensors/Diagnostics stay on their owning Charger, Charging Asset or ChargeController. Existing generic `kind` remains the single asset type editor in the HA device's Config group; no parallel type settings or domain layer. The original five-view UX keeps short translated labels and shows asset type + the qualified power value. Eight native HA and card locales: **English, Nederlands, Français, Dansk, Norsk bokmål, Svenska, Deutsch, Español**. Translate HA entity keys/states without changing machine values, stable IDs, device association or existing Recorder semantics. Missing languages or mismatched keys fail developer tests.

**Explicit acceptance:** Test car, bicycle, motorcycle, scooter and other with the same `ChargeDemand` contract, and no-SoC kWh/duration case; current-plug attribution with a source of 2.3 kW, genuine measured 0 and missing/stale sources; assignment-only/forecast cannot claim asset power; unplug, session reassignment or restart hold removes the asset reading but never rewrites Charger history; German and Spanish entity/UX labels render under native HA; entity identity and Config Entry survive reload. **Source tests do not establish real HA rendering or EVSE/battery-side qualification.**

## Configuration

**Recommended:** native Config Flow and Options Flow, with guided steps for controller → chargers → assets → optional sources → verification. Clear names and safe defaults for beginners.

**Expert:** optional declarative YAML import. The YAML representation and UI use the same schema, field meanings and validation. The active configuration has one owner: YAML when imported or HA Options when UI-authored. There is no YAML/Jinja planning engine or duplicate settings store.

Illustrative expert configuration (shape is under development; not yet qualified in HA):

```yaml
# configuration.yaml
robotix_multicharge: !include multicharge.yaml

# multicharge.yaml
controller:
  id: home
  name: Home charging
  max_parallel: 2
  max_power_kw: 11
assets:
  - id: family_car
    name: Family car
    kind: car
    soc_entity: sensor.family_car_battery
    target_soc: 80
chargers:
  - id: driveway
    name: Driveway
    kind: variable_current
    rated_power_kw: 11
    phase_count: 3
    min_current_a: 6
    max_current_a: 16
    power_entity: sensor.driveway_power
```

Config/Options Flow code, YAML structural validation and read-only logical setup devices have been committed. Real HA setup, import/reload, Options editing and rollback still require qualification. On `dev`, physical actuation is source-tested but remains gated by explicit owner selection, verified capabilities, a commissioning declaration and real independent readback. No field commissioning is approved.

## User experience and native entities

| View | Primary task |
| --- | --- |
| **Overview** | See what is charging, what comes next and what needs attention |
| **Charging Plan** | View today/tomorrow planned vs measured charging and readiness |
| **Chargeable Assets** | Manage energy needs, targets, deadlines and source quality |
| **Chargers** | See connection, assignment, capabilities and true hardware feedback |
| **Settings** | Guided setup, source mapping, strategy, limits and diagnostics |

The six requested modes are Automatic, Solar, Economy, Ready By, Force Charge and Off. A manual command still obeys the configured limits and physical equipment protections.

Expose stable native HA device and entity IDs for the three logical concepts. Ordinary HA dashboards and automations must remain possible even without a bespoke card. A dedicated chart is justified for the future interval timeline; no second planner or data store belongs in the frontend.

Logical identity and selected source bindings change only through deliberate structural edits. Live SoC, energy, current and availability updates never rebuild device registry topology. Missing and unknown must never be rendered as zero or as a successful charge.

## Charging plan timeline

A single responsive, bundled timeline will be usable at ChargeController level and filtered by Charger or ChargeableAsset.

- 15-minute slots for today and tomorrow in the HA timezone, including 23/25-hour daylight-saving days. A vehicle gets **active, executable-candidate** kW slots only when the Charger is physically connected and the vehicle identity has been verified or user-confirmed for the current plug session. A saved Charger preference is never connection proof. Disconnected vehicles may have **separate dashed, non-reserving what-if forecast slots** when a selected Charger and valid demand/capacity evidence exist; they never enter the active plan or authorize a command. Past actuals remain visible.
- Proposed plan, accepted plan and **measured** actuals distinguished, with power (kW), energy (kWh) and source freshness. Give the user a **Color by Vehicle / Color by Charger** identity toggle with stable colors derived from immutable IDs (never array index). Each Vehicle and each Charger has its own **user-changeable plan_color on its owning native HA Device**. MultiCharge assigns unique automatic defaults per owner category (Vehicle vs Charger); user choices persist across days, renames and reassignment. Encode Proposed/Accepted/Measured separately by opacity, stroke/pattern and explicit label, not a single shared color. The chart shows the selected vehicle **and** Charger for each slot, and does not double-count physical measured kW.
- Ready By and expected shortfall clearly indicated; optional electricity price and solar/context sources when available.
- A simple mobile view, accessible labels, readable legends and explicit unavailable/unknown states.
- Future slots queried through one bounded, read-only plan view; measured history from native HA telemetry and Recorder. Do not rewrite 48-hour plan arrays into giant sensor attributes or compute a new plan in the chart.

The source contains a deterministic 15-minute proposal planner, an admin-only bounded native HA query and one source-tested five-tab UI with separate proposed, accepted and actual signals. A single guarded actuator handles selected native switch and adjustable-current commands and 15-minute Automatic/Solar/Economy/Ready By execution; manual Force Charge and Off use the same writer. It requires explicit exclusive ownership, commissioning, qualified source/capability/phase/circuit evidence and independent power/current readback. The implementation now also includes native completed-session receipts, conservative tariff costing, an admin-validated Config Entry preferences editor, safe native STOP button, temporary guest expiry and stable historic session attribution. **Source and simulated HA-service tests are not actual HA/browser or EVSE commissioning. Another provider may still retain physical authority; full session recovery, user permission scope, all five rendered views and complete UC01–UC29 end-to-end qualification remain OPEN.**

## Planning, physical execution and safety

```text
Native HA sources (charger, asset, price, solar, available site power)
    -> validated binding and source freshness
ChargeableAsset needs + Charger capabilities
    -> ChargeController: coordinated charging plan
    -> one authorized Charger actuator
    -> independent actual hardware readback
```

The configured power budget, circuit and charger limits are binding safety constraints, not soft suggestions. Missing or stale safety-critical capacity is never treated as unlimited. A verified on/off switch cannot be represented as variable-current control. A command acknowledgment is not proof of actual physical power change.

**Durable Pause/Resume (development candidate):** the existing Charger executor
records a per-Charger user pause hold in its existing native HA control Store
*before* attempting a physical STOP. The confirmed Pause response requires
independent physical switch/power readback. A failed or uncertain STOP remains
held and quarantined. Pause excludes the Charger from both firm and indicative
plans; it cannot be auto-restarted by the next quarter. Resume requires an HA
administrator, a qualified physically idle Charger and successful persistence;
it **only releases the hold**. A future eligible quarter or a separately
admitted manual START must pass the original exclusive writer and safety
checks. The Charger native Pause/Resume buttons and the existing admin
WebSocket use this one path. A measured, physically closed session may clear
its former in-flight intent lock only after time-bounded receipt qualification;
unknown delivered energy retains the hold. Stored pauses survive a normal HA
restart, never restore a former active physical session. User journeys,
provider failures, native permissions and real-hardware readback remain
unqualified by source CI alone.

**Expert JSON (development candidate):** direct human-readable Controller,
Charger and ChargingAsset objects are mapped to the same canonical validated
Config Entry and HA source-import lifecycle. Fully described electrical
bindings are required for a Charger owned by MultiCharge; incomplete
commissioning cannot be inferred from a default rating. Imported JSON is
still read-only from the native settings interface. Its ownership declaration
does not verify external writer handoff; real hardware and field safety
qualification remain separate.

The installed equipment and built-in charger protections remain authoritative. Any physical execution must remain disabled until real hardware and fail-safe behavior are qualified.

## Acceptance and tracking

The [functional use case matrix and qualification checklist](https://github.com/npinguin/robotix-multicharge/issues/1) are maintained in one issue. Include 1/2/4/10 charger scenarios; no-SoC, missing price and meter sources; time zones/DST; deadline feasibility; unsafe or rejected commands; real readback; configuration persistence; and HA restart/unload/rollback.

This document describes public implementation boundaries, not confidential project integration plans. Do not mark source CI, mock screens or an unqualified package Feature Complete.

## Fixed five-tab UX — approved no-drift implementation specification

**Visual reference:** owner-approved five-screen presentation in the 2026-11-22 conversation. It is the design acceptance target, not permission to create a new layout. Target **≥99% fidelity** to the approved appearance; it is NOT measured or achieved yet. Engineers without the earlier conversation use the explicit screen anatomy below, then capture the original illustrated reference before any quantified claim. Real screenshots, equal seeded data and owner review determine final acceptance.

**Exactly these five tabs in this order:** **Overview → Charging Plan → Chargeable Assets → Chargers → Settings**. One self-contained frontend experience included with the community integration, enabled by default for ordinary HA frontend installations with a supported opt-out. No sixth product screen, alternative dashboard, redundant scheduler or external frontend dependency. Native HA devices/entities also remain independently usable in ordinary dashboards.

| Tab | Visible screen anatomy in the approved order | Required interaction |
| --- | --- | --- |
| **Overview** | Site title + mode badge; one row of **three compact equal KPIs**: active chargers, total **actual** power in kW, qualified current price/currency per kWh; stacked compact chargeable-asset rows with icon, actual battery→target or unknown/manual demand, progress, status badge, Ready By and charger; divider; **Next action** with one clear recommendation/attention | Show **Automatic, Solar, Economy, Ready By, Force Charge, Off** as daily modes. An unqualified mode is visibly unavailable with reason, never silently selectable |
| **Charging Plan** | Title; **Today/Tomorrow** switch; **All Chargers / selected Charger or Asset** filter; intuitive full-width 15-minute power chart with **Color by Vehicle / Color by Charger**, stable and accessible per-ID hues and identity legend; distinct proposed/accepted/measured patterns and qualified-price line; divider; **Next planned session** and **Reason** | Show firm proposed/accepted slots **only** for connected/current-connection-confirmed cars, while an explicitly separated **Indicative** dashed row may represent unplugged vehicle what-if demand. Vehicle↔Charger labels may be saved as Vehicle / Charger / Both (default Both); entity hue is independently selectable by Vehicle / Charger. The indicative row consumes only residual *hypothetical* capacity after firm planning, never binds power or sends commands. Actuals remain physical Recorder evidence, including after unplug/rebind; no invented cost, energy, user identity or DST slots |
| **Chargeable Assets** | Title + configured count; stacked expandable asset cards, including unplugged/Guest; name/icon, vehicle intent/readiness, 2-column Battery/Target/Ready By/selected Charger, priority/source provenance, Add | Persist identity, SoC/targets/finite kWh/duration/deadline regardless of cable. Make Assign/Change/Unassign an **idle-only** routine operation. Vehicle is selected on **at most one** Charger and only counted in active charging after separate real connection and session-identity verification |
| **Chargers** | Title + configured count; cards for all physical Chargers even when no vehicle is registered; observed connection, actual kW, control capability, **selected vs confirmed connected vehicle** and Details | Show independent native connection/readback and selected assignment. Allow a safe idle-only change or No vehicle, require current-plug identity confirmation for active vehicle planning. A Charger with a connected unknown vehicle may offer only an explicit finite manual unattributed session if qualified. Unsafe/active reassignment blocked; leave vendor device untouched |
| **Settings** | Title + setup badge; six items in this **exact** order: **Charging site**, **Sources & bindings**, **Charging strategy**, **Safety & limits**, **Integrations**, **Advanced & YAML** | Beginner wizard **Site → Charger → Asset → Sources → Verify**; inline selectors/validation, advanced progressive disclosure; optional expert YAML import to the same validated configuration authority |

**Visual rules:** compact rounded HA-theme cards, consistent density and spacing, readable units and headings, restrained badges, simple meaningful icons and accessible colors/legends. First-view attention and action before low-level diagnostics. No giant hero, multi-step unrelated dialogs, banners or expert-only material on beginner home screen. One bundled lightweight frontend implementation; no extra framework or frontend-owned planner.

**Screenshot acceptance matrix:** fixed populated fixture (2 assets/3 chargers), empty fresh install, unknown/stale source, missing price, infeasible deadline, pending/unknown command; mobile **390×844**, tablet **1024×768**, desktop **1600×900**; light/dark. Inspect scrolling, focus, touch, axes and labels, true card order, conditional states, actual readback, error presentation. Capture original approved reference and the real HA rendering in the same state and viewport. Changes to this screen contract require owner approval recorded in existing Issue #1 BEFORE changing the implementation.

## Native logical devices — no historical facades

One stable logical HA Device Registry identity per product Controller/Charger/ChargeableAsset ID; native source devices retain their identifiers, entity registry entries and Recorder history. Never duplicate original physical devices or copy provider entities/controls into a new logical device. No legacy EVSC entity aliases or bridge sensors, no semantic parentage with HA `via_device`. Source observations only update runtime values; structural changes require explicit validated configuration revisions.

| Logical device | Canonical specialist properties/actions at Feature Complete | Excluded |
| --- | --- | --- |
| **ChargeController** | Site-wide mode, electrical group/phase/circuit budget, active-eligible charging candidate allocation, 15-minute proposed/accepted/actual plan/reasons, aggregate verified actual kW and scheduling priority | Vehicle SoC and connection identity, raw charger duplicate, secondary energy planner, giant 48h sensor payload |
| **Charger** | Stable source/physical connection/occupancy, verified capabilities/phase/circuit/current, exact native command ownership and readback, own charging session and meter/provenance, **one saved asset assignment (nullable)** plus separate **current-connection identity evidence** | Battery demand/SoC truth, inference that selected saved Asset is physically plugged in, reparented vendor device or second EVSE writer |
| **ChargeableAsset** | Stable registered Vehicle/Guest identity, OEM/manual/unknown SoC provenance, portable target/kWh/duration/Ready By/priority/remaining measured need, expiry; selected Charger as **derived, read-only relation** and waiting/connected/active state | Physical switch, duplicate writable assignment, a second OEM truth, second energy planner, direct wire control |

Normal HA sensors/selects/buttons must be independently usable in user dashboards and automations, with current values and safe role-based admission. A single `Readiness` diagnostic is a valid canonical property; the current constant `not_commissioned` is development-only and must become true runtime evidence. No permanent placeholders, unqualified control buttons or silently renamed unique IDs.

## Owner-approved functional clarification: interchangeable vehicles, independent Chargers and chart colors

Recorded in the **existing [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1)**, 22 November 2026; this expressly updates the previously fixed identity color treatment **only**, not the five-tab anatomy or product design baseline. The only authoritative saved Asset↔Charger assignment is `charger.asset` in the existing Config Entry: zero/one per Charger, zero/one Charger per Asset. Both devices live independently. Unplugged vehicles and unassigned Chargers remain usable and visible. The currently connected car's identity requires separate current-plug proof or explicit user confirmation. Idle-only ordinary selection changes must not implicitly stop/energize equipment; active/unknown affected Chargers reject rebind until separately confirmed stopped. Preserve asset-owned demand, independently measured remaining kWh, immutable session-time attribution and source identities. A connected but unknown Charger may offer an explicitly bounded anonymous **manual** session without inventing a vehicle record, but not future vehicle-colored auto slots.

The Charging Plan colors an identity dimension **per Vehicle or per Charger** with stable distinguishable hues from the corresponding native owner `select.plan_color` (not frontend-owned or index-based). The initial distinct defaults are allocated deterministically by immutable logical IDs; explicit choices always win. Proposed, physically accepted and measured are independent statuses rendered with a second non-color-only pattern/weight/opacity/legend; no one-color blue overlay of all planned Chargers. Pending disconnected vehicles appear as a compact non-energy waiting status, not kW bars. Actual elapsed history may show now-disconnected vehicles. Accessible responsive tests cover 0/1/2/4/10 chargers; known/unidentified/Guest, disconnected, moving car, light/dark, and exact HA screenshot widths. The full end-to-end FLEX-01–21 matrix is part of UC01–UC29 in Issue #1. No changed implementation or passing field qualification is implied by this documentation change.

## Owner-approved extension: indicative disconnected-vehicle forecasting

**22 November 2026:** Owner permits **unplugged saved vehicles in the same Charging Plan as clearly separated forecasting only**. This extends, but does not weaken, the earlier connected-only **active** plan contract. No new device type, planning implementation, command writer, backend scheduler or sixth UI tab.

**One engine, two truths:** \`ChargeController\` builds the authoritative connected-eligible proposed plan first; only that plan is consumed by the existing executor. A second, **non-executable what-if assessment** runs through the SAME \`compile_plan\` algorithm with the connected proposals passed as already occupied quarter-hour slots. This preserves group kW, phase current, circuit current, parallel charger count, qualified solar/price and expiring binding envelope across both sets. Forecast demand can only use the **hypothetical residual**; it neither changes a real proposal nor holds/accepts capacity, alters dispatch priority, issues a service call or creates fictitious measured energy. The scenario is always labelled conditional; real arrivals invalidate and trigger refresh of the actual plan, not automatic promotion of an old forecast slot to accepted.

**Inputs/provenance:** A saved but disconnected Vehicle with a selected Charger, valid energy/duration/target demand and qualified disconnected source may appear as dashed indicative slots. Unknown/missing connection source is **not** assumed disconnected. If the user gives \`expected_connection_at\` (timezone-aware) its future start bounds the hypothetical. Otherwise the explicit assumption is **"if connected now"**, not a guessed arrival. Absence of demand, selected Charger, valid electrical budget or tariff/solar source as required by the strategy yields a visible reason, never invented kW/price, never fake readiness certainty. A vehicle with no selected Charger can appear as a waiting intention but lacks capacity evidence for a numeric forecast; a Guest follows the same expiry and qualification rules.

**Presentation:** One readable visual timeline per Charger, each with a correct Vehicle–Charger identity combination. User-selectable, Config Entry-backed \`plan_label_mode=vehicle|charger|both\` (default \`both\`), independent \`plan_color_by=vehicle|charger\`, and \`show_indicative_forecast\` flag. The **everyday** preferences are native HA `select`, `number`, `datetime` and `text` entities attached to their respective owning logical Devices, backed by the same validated Config Entry. Wiring, verified phase/circuit capabilities, source binding and commissioning remain expert installation configuration, not casual preference controls. Proposed, physically accepted, Recorder actual and forecast are different visual status rows (light vs solid vs independent physical evidence vs dashed outline); identity colors remain stable by canonical ID. Historical actual data is attributed to a Vehicle only when a confirmed session-time receipt proves the full interval, never by today's \`charger.asset\`. Signed qualified tariff remains an independent contextual line with its own EUR/other currency/kWh scale. On an everyday Home Assistant dashboard keep 0/1/2/4/10 Chargers legible, including light/dark and accessible text for users who cannot discriminate color.

**Contract/readback:** Existing bounded read-only \`get_plan\` includes \`slots\` (executable candidates, immutable semantics), a distinct \`forecast_slots\` array with \`status=indicative_only\`, \`may_execute=false\`, \`reserves_capacity=false\`, assumptions and reasons. Native Controller \`Plan status\` exposes only compact indicative kWh/reasons, never another giant 48h payload. This is scenario assistance and may change as cars connect, site capacity changes or weather/prices update. No forecast probability, hard expected arrival, economic promise or measured session is manufactured.

**Feature acceptance:** Tests must verify (1) 2 connected vehicles have active allocation; 1 disconnected has only dashed indicative load, (2) active slots are bit-for-bit unchanged when forecast is enabled or disabled, (3) the same quarter's hypothetical power plus active power never exceeds qualified site/phase/circuit/parallel ceilings in that scenario, (4) optional expected plug-in time excludes earlier quarters, (5) missing/unknown connection or missing demand prevents a numeric forecast, (6) "Off" never schedules indicative power, (7) a disconnected forecast cannot reach \`advance_plan\`/executor or accepted slots, (8) Vehicle/Charger/Both labels and identity color preferences survive native reload/rename, (9) rebind cannot rewrite historic actuals, and (10) real HA mobile/tablet/desktop and near-real-time behavior qualify with actual sources. Source green CI is **not** proof of real-HA/EVSE/browser completion. Keep physical activation, HACS TEST/STABLE, merge and release HOLD until overall Feature Complete and field qualification.

## Owner requirement — native HA preferences, local colors and plain-language UX

**22 November 2026, acceptance within existing UC01–UC29 / Issue #1:** Every configured Vehicle and Charger has a stable per-device plan color. Assign distinct defaults automatically for all IDs in the category (1/2/4/10 tested); expose **Plan color** as a native `select` on that Vehicle or Charger. A user override must persist through native Configuration Entry re-read, rename and reassignment. Distinct automatic defaults do not restrict the user from intentionally choosing the same color for two items. Plan rendering reads these persisted owner colors, with a separate Controller `Color by: Vehicle/Charger` setting and `Show: Vehicle/Charger/Both` option, default Both. Indicative unplugged forecasts retain the selected identity hue but are dashed/non-reserved and never executable. Never invent asset identity for physically measured charger slots; historical attribution must follow a proven session receipt.

**Ordinary controls must appear on the owning native HA Device**, not a redundant integration Options editor or JS-only hidden state:

| Owner | Normal user preferences exposed via HA-native entities | Installation-only (advanced setup, not ordinary preference) |
| --- | --- | --- |
| ChargeController | Selects: charging mode, label arrangement, color grouping, indicative forecast visibility. Numbers: group kW ceiling and parallel Charger count. Text: site name. | Exact source and power-binding mappings, validated phase/circuit wiring, external integration and commissioning verification |
| ChargeableAsset / Vehicle | Selects: Plan color, vehicle type, Ready By repetition. Numbers: requested kWh **or** duration, target battery %, priority, charge-power cap, usable capacity, charging efficiency. DateTimes: Ready By, expected connection, Guest expiry where applicable. Text: user-visible Vehicle name. | Provider/OEM SoC source mapping, initial identity provisioning and Guest lifecycle |
| Charger | Selects: Plan color and **Selected vehicle / No vehicle** with single assignment authority. Text: Charger name. | Physical protocol, source entities, measured energy/current source, electrical capabilities, physical writer and commissioning |

All native user controls call the **one existing** validated Config Entry preference authority; the card must use actual Entity Registry IDs, never guess HA `entity_id` from a friendly name. Visual-only color/label/forecast choices must not unload or STOP an otherwise running EVSE. Safety-impacting numeric demand and assignment changes retain the executor lock, physical idle/readback and source qualification. No second writable identity, duplicate OEM source, shadow store, HA control implementation or raw frontend charger service.

**Simple multilingual UX:** The five original tabs stay fixed. Device/entity names and supported enum states are localized using native Home Assistant translations (EN/NL/FR/DA/NB/SV where provided); the bundled card has short English/Dutch/French labels. On household views, use compact labels like *Charging, Stopped, Connected, Waiting, Indicative, Unknown, Plan color, Vehicle, Charger*; never show module names, exception identifiers, engineering status, commissioning tutorials, internal state codes, test evidence or long instructional sentences. Reasons remain available for troubleshooting through native diagnostic attributes, not prominent user copy. Keep labels accessible without relying only on color. Full locale completeness and device/browser accessibility are acceptance criteria, not source-green claims.

**Acceptance examples:** Add ten Vehicles and ten Chargers -> each category receives ten distinct default colors. Set a Vehicle to Violet and Charger to Green using their HA entities -> chart immediately reflects each owner; switching Color by changes the palette dimension; renaming/rebinding preserves each selected color. Reload HA and verify the same Config Entry values, native entity unique IDs, selected colours and plan. Configure mode/targets/arrival via native controls without opening Options Flow. Confirm that changing a display-only color while another Charger is active does not issue STOP/reload or alter accepted slots. Confirm short English/Dutch/French labels and native select/sensor translations, no raw codes or developer prose, across 390/1024/1600 viewports light/dark and 1/2/4/10 chargers. Real HA/browser/native-service and physical operation remain unqualified; no release authorization.

## Near-real-time action evidence on canonical HA devices

**Owner requirement (22 November 2026):** Every native MultiCharge **SET/action** and its resulting observed state must be visible on the owning logical HA Device **and** on the overarching ChargeController. No UX-only success flag, no optimistic entity state, no second controller/writer, no separate meter/ledger. Reuse existing HA push-state subscriptions and the established Config Entry, executor, source-evidence and Recorder owners.

| Set/action | Owning logical device and canonical readback | ChargeController native projection |
| --- | --- | --- |
| Strategy change (Automatic/Solar/Economy/Ready By/Force Charge/Off) | Controller's selected \`Charging mode\` read from reloaded native Config Entry; requested mode is never called executed before re-read | \`Charging mode\`, \`Settings revision\`, \`Last settings action\` with requested/confirmed/rejected and expected/observed revision |
| Charging site / phase/group power limits / provider binding | Controller configuration + qualified source availability and physical envelope; no guessed site power | Settings revision attributes for group max kW, parallel count, phase ceilings; plan status/reason and qualified actual group kW |
| Vehicle demand, target, Ready By or guest expiry | ChargeableAsset \`Charging intention\` (target/request/duration/priority/expiry), plus native measured SoC quality and assigned Charger derived | Settings revision and last settings action identify target Asset/fields; actual scheduling changes only after source/connection/identity qualification |
| Vehicle selection, charger assignment or "No vehicle" | Charger \`Selected vehicle\` from single Config Entry authoritative assignment; asset derives the selected Charger, never a second writable ownership record. The source physical connection is separate | Settings revision + last settings action with affected Charger and status; connection-count sensor is physical only and does **not** prove vehicle identity |
| START / STOP / Force / quarter-slot admission | Charger \`Command status\` with request ID, action, requested timestamp, source readback at/time and reason; physical switch/meter remain source-owned | \`Last physical action\`, \`Action health\`, \`Charging chargers\`, \`Connected chargers\`, qualified \`Actual power\` and existing \`Plan status\` |
| Variable current setpoint | Charger \`Confirmed current setpoint\` from physically confirmed owned session; independent native measured-current source and freshness as attributes | \`Last physical action\` (set_current, request and readback status), aggregate health, actual kW; no claim that a requested current equals delivered current |
| Source disconnect, stale/unknown EVSE, exhausted capacity, protective STOP | Actual Charger \`Connection\`, actual power/current, command status and fail-closed reason; Vehicle is waiting/disconnected, never guaranteed connected from saved assignment | Aggregated connected/charging counts become \`unknown\` if any mandatory native source is stale; last action and controller health show unconfirmed outcomes. Physical STOP remains with the one writer |

**Push/update contract:** Native source entity state changes, executor \`requested → confirmed/rejected/execution_unknown\` and Config Entry settings updates notify subscribed logical sensors in the HA event loop; source refresh is event-driven, with the existing minute tick only as an integrity/freshness fallback, **not** the normal propagation mechanism. The desired qualification objective is **≤2 seconds from a native HA state event or command result to the corresponding logical and Controller sensor update in a running HA instance**; physical confirmation is separately bounded by the native provider's readback and command timeout. Provider latency is never hidden; expose source \`observed_at\`, \`quality\`, requested/readback times, IDs and reason. Verify with event timestamps and real HA recorder/browser traces, including rapid updates and 1/2/4/10 chargers; this latency objective has **not yet been field measured**.

Controller aggregation must be sourced from **all** configured Chargers: connected count is \`unknown\` if any required connector observation is invalid/stale, charging count and aggregate actual kW are \`unknown\` on incomplete physical power coverage, and a verified physical zero is exactly zero. \`Action health\` and \`Last physical action\` are an event summary of the one real executor, **not an additional command gateway**. \`Last settings action\` uses the existing HA control Store only for a bounded settings action receipt (not copied settings or a second persistent configuration): accepted-unconfirmed remains pending until a matching \`Settings revision\` is actually read from the reloaded Config Entry. A rejected setting never appears confirmed. All native entities retain stable logical Unique IDs through rename/rebind; sources retain their own physical HA devices and history.

**Acceptance:** a START/STOP/set_current and its independently measured response produce two distinct ordered observables at Charger and Controller levels; an admin mode/site/asset/assignment setting shows its own requested action and actual reloaded setting, including rejected changes; a physical cable/power change updates both Charger and controller projections without relying on the 60-second fallback. Simulate missing/stale sensors, delayed power, failed STOP, store/reload failure, concurrent commands and an unplugged Charger: nobody reports false success, connected vehicle, measured zero or duplicated execution. Qualify native Home Assistant automation usability in headless mode and real browser near-real-time behavior before G4/G5 closure.

## Implementation and release gates

**G1 Contract first:** for every UC01–UC29, specify one owner, stable identity, canonical input/source quality, public read/write surface, failure behavior and executable test. Versioned generic HA interface; no duplicate sources, command writers, schedules, ledgers or UX inferencing.

**G2 Complete functionality in this dev batch:** guided HA setup + optional YAML parity, validated sources, targets/deadlines/priority, six qualified strategies, one group planner (1/2/4/10 chargers), true physical control/readback, persistence, canonical logical entities, one bounded read-only chart query and the above exact five-tab frontend.

**G3 Targeted tests during coding:** negative safety/ownership, different phase/current limits, 23/25-hour days, missing/partial prices, signed PV/net, source staleness, no-SoC, source rebind, event storms/duplicate commands, command timeout, restart/unload, identity/history and headless operation.

**G4 Feature Complete before full qualification:** all 29 scenarios, five rendered UX tabs and source/negative/permission behavior complete with no open agreed functional debt. Green syntax/unit tests do not meet G4.

**G5 Qualify exact candidate:** HACS/Hassfest, actual HA setup/reload/unload/upgrades/rollback, frontend browser screenshots at the three viewports, provider interoperability, owner-safe physical commissioning and explicit release permission. Public HACS TEST must follow the validated exact-`main` governance path. Keep the existing Draft PR on `dev` for the ongoing agreed batch.

**Present status (2026-11-22): the same `dev` batch now includes verified source/config schema, phase/circuit-aware stepped planning, native switch/current commands and independent readback, quarter-hour admission for Automatic/Solar/Economy/Ready By, guarded Force Charge/Off, a bounded accepted/proposed/actual query and native storage replay hold. These are development/source-tested capabilities only. Actual HA/browser and hardware qualification, complete session/UX editing and exact-candidate release gates remain OPEN.

## Initial whole-site setup from native Home Assistant (UC01/UC02/UC17)

The normal community installation must offer **Guided setup** or **Configure entire charging site** at the first native Home Assistant Add Integration screen. Expert setup accepts a **single data-only** `controller` / `assets` / `chargers` YAML document, using exactly the same validator, IDs and persistence authority as the existing Settings → Edit YAML Options Flow; it does not require a preliminary dummy site, YAML package, extra Config Entry, template sensors or any Robotix Basic/Core/Premium runtime. A new full-site file remains an optional, separate expert workflow, not a required component of initial setup.

**Positive path:** A fresh HA install opens MultiCharge, chooses expert setup, pastes one complete Wessels-shaped generic configuration (1 Controller, 4 Chargers, 4 Assets, native provider entity IDs and optional source bindings), reviews the exact object/number of logical devices, confirms, then sees the same three kinds of HA logical devices and five-view dashboard. The entry source is `ui`, so ongoing in-card settings remain editable. The guided setup and existing native Options editor continue unchanged. No physical start/STOP or ownership switch occurs during preview or save.

**Negative/recovery paths:** Invalid/duplicate YAML keys, unsupported HA `template:` blocks, conflicting or duplicate source bindings, forged commissioning or physical ownership changes, malformed source IDs and user cancellation must not create an entry, publish a charger command or hide an error. Empty Controller-only setup is valid; users may return and edit the draft before confirming. Duplicate integration setup is rejected. Existing YAML/JSON-file-managed entries keep their file authority and are never silently adopted as GUI-owned. Existing registry and Recorder identities must be preserved after GUI updates/reload. Actual HA flow acceptance must exercise both successful and rejected paths, not just static signatures.

**Standalone source requirement across UC01–UC29:** MultiCharge source normalization, charging planning, execution and GUI must have no runtime import, mandatory HA entity naming convention or setup prerequisite from other Robotix products. Any site-specific Basic EVSC/Energy `evsc_bridge_*` or `sensor.energy_*` wiring is fixture input rather than a public product dependency. Native HA providers still own their measured sensor data. Missing semantic evidence stays unknown and physical ownership remains exclusive and separately commissioned.

### Direct native price sensor acceptance (UC07/UC15/UC17/UC19/UC28)

MultiCharge may consume a native Home Assistant provider's price-interval attributes directly. This is **not** a mandatory Robotix or site-owned template bridge. A selected sensor offering `raw_today` and optional `raw_tomorrow` lists of real `{start,end,value}` intervals with a validated explicit `EUR/kWh` / `EUR/MWh`-style ISO currency price unit may drive Economy **ranking** as spot-only data, without pretending to know the resident's effective all-in price. Negative and zero prices remain valid. The existing explicit `kind=effective_price_kwh`, `currency`, `valid_until` and `intervals` contract remains supported for a genuinely qualified effective tariff.

Native-source validation requires native observed freshness, finite values, aware start/end timestamps, non-overlap, consistent currency/units, bounded interval count and no stale coverage. Missing/ambiguous units, malformed intervals or stale source give no qualified prices. No quotation is extended beyond its actual supplied interval. Native spot price may schedule Economy but **never produce a billed/effective session-cost receipt**; a session cost is qualified only for effective all-in tariff intervals covering the entire measured session. Expose source basis in plan/diagnostic projections to avoid misleading the user. Existing manual/physical source access and safety gates are unchanged. Test a genuine native source with 23/25-hour DST intervals and negative quotes as separate exact-source cases; source-only unit tests are not provider/browser acceptance.

### Explicit native Charger status value mapping (UC04/UC11/UC17/UC21/UC23/UC29)

A native provider `sensor.*` may report cable state as provider-defined raw enum values rather than literal `connected`/`disconnected`. **For every selected Charger**, the GUI-owned canonical configuration can optionally supply `connected_states: [..]` and `disconnected_states: [..]`, two explicit nonempty, case-insensitive, disjoint lists of exactly observed states for its one `connected_entity`. This enables direct native status binding on a clean Home Assistant install without any required `evsc_bridge_*` helper, custom template or Robotix package. No brand is assumed and the source provides the actual raw state, freshness and observation timestamp. A binary_sensor with native on/off semantics requires no mapping; a switch or manually toggled smart plug cannot be treated as independently verified physical cable evidence.

**Positive:** status `Charging` with a configured connected label is connected only while freshly observed; `Available` with an explicitly configured disconnected label is disconnected. Missing or unexpected provider statuses stay unknown and prevent START. The exact physical connection instance still needs current-plug vehicle confirmation; saved assignment alone never authorizes charging. **Negative:** duplicate/overlapping/empty mappings, unqualified entity domain, stale provider status, ambiguous status or physically changing the mapping during an active/unknown command must be rejected without a physical write. Historical source/device IDs are not recreated; existing raw literal connected/disconnected and binary_sensor behavior remains compatible. **Raw status substate continuity:** A fresh, positively mapped transition between two connected native EVSE states (e.g. `Preparing → Charging`) must preserve the explicitly confirmed current-plug association and not demand repeated vehicle confirmation while charging. The single executor tracks a volatile connection epoch from observed native state changes; any observed disconnected/unknown/stale source, entity rebinding or integration restart invalidates it and demands a new explicit vehicle confirmation. No epoch is persisted or inferred from a previously selected vehicle. Verify connected-substate transition, disconnect/replug, stale status and restart against the real HA event subscription. Field hardware proof remains required.
 Native tests alone do not establish real vendor-state semantics or physical handoff.
