/* Source-only browser-like interaction contract. Never claimed as a real HA render. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
// UX-OWNER-01 schema-bound coverage. Every accepted persisted owner field
// must be visible on precisely its owning logical object at D3/D4.
const configurationSource=fs.readFileSync(path.join(__dirname,
  "../custom_components/robotix_multicharge/configuration.py"),"utf8");
const uiSource=fs.readFileSync(path.join(__dirname,
  "../custom_components/robotix_multicharge/frontend/robotix-multicharge.js"),"utf8");
const groupSource=uiSource.slice(
  uiSource.indexOf("const MC_OWNER_GROUPS = {"),
  uiSource.indexOf("const MC_OWNER_NAMES = {")
);
assert.ok(groupSource.startsWith("const MC_OWNER_GROUPS = {"));
const scopeList=["controller","asset","charger"];
for(let index=0;index<scopeList.length;index++){
  const scope=scopeList[index];
  // Bound the regex to the actual owning schema. Asset and Charger
  // both use _allowed(source, ...); spanning both falsely reports Asset
  // fields as missing from the Charger when validating against its UX.
  const assetStart=configurationSource.indexOf("    assets = []");
  const chargerStart=configurationSource.indexOf("    chargers = []");
  assert.ok(assetStart>=0&&chargerStart>assetStart,
    "Owning schema sections must be separately identifiable");
  const schemaSection=scope==="controller"?
    configurationSource.slice(0,assetStart):
    scope==="asset"?
      configurationSource.slice(assetStart,chargerStart):
      configurationSource.slice(chargerStart);
  const sourceMatch=schemaSection.match(
    new RegExp("_allowed\\("+(scope==="controller"?"ctl":"source")+
      ", \\(([\\s\\S]*?)\\), \""+scope+"\"\\)")
  );
  assert.ok(sourceMatch,"Schema for "+scope+" must be readable");
  const permitted=[...sourceMatch[1].matchAll(/"([a-z][a-z0-9_]*)"/g)]
    .map(match=>match[1]);
  const start=groupSource.indexOf("  "+scope+": [");
  const after=index+1<scopeList.length?
    groupSource.indexOf("  "+scopeList[index+1]+": [",start):
    groupSource.indexOf("\n};",start);
  assert.ok(start>=0&&after>start,"Owner field groups for "+scope);
  const uiFields=new Set([...groupSource.slice(start,after)
    .matchAll(/"([a-z][a-z0-9_]*)"/g)].map(match=>match[1]));
  // Legacy commissioning is a derived compatibility projection, not a UX setting.
  const missing=[...new Set(permitted)].filter(field=>!uiFields.has(field) &&
    !(scope==="charger"&&["physical_commissioned","dedicated_asset_id"].includes(field)));
  assert.deepEqual(missing,[],"No "+scope+
    " configuration field may silently disappear from its logical UX object");
}

class Element {
  constructor(tag){this.tag=tag;this.tagName=String(tag||"").toUpperCase();this.children=[];this.attributes={};this.events={};this.style={};this.textContent="";this.value="";}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=[...items];}
  setAttribute(k,v){this.attributes[k]=v;}
  getAttribute(k){return this.attributes[k]??null;}
  addEventListener(k,handler){this.events[k]=handler;}
  attachShadow(){this.shadowRoot=new Element("shadow");return this.shadowRoot;}
  click(){if(this.events.click)this.events.click();}
}
const registry=new Map();
global.HTMLElement=Element;
global.customElements={get:(n)=>registry.get(n),define:(n,c)=>registry.set(n,c)};
global.window={};
global.document={
  createElement:(tag)=>registry.has(tag)?new (registry.get(tag))():new Element(tag),
  createElementNS:(_ns,tag)=>new Element(tag),
  createTextNode:(text)=>{const n=new Element("#text");n.textContent=text;return n;}
};
require("../custom_components/robotix_multicharge/frontend/robotix-multicharge.js");
assert.ok(uiSource.includes('mcEl("ha-icon"') && uiSource.includes("mcSocBar"),
  "Native semantic icons and qualified battery indicator must remain available");
assert.ok(uiSource.includes("this.dashboardEditField(parent,scope,record,field)"),
  "Every persisted owner field is edited directly inside MultiCharge");
assert.ok(uiSource.includes("robotix_multicharge/yaml_configuration")&&
  uiSource.includes('const save=mcButton("Save",async ()=>'),
  "UC02 direct Save YAML editor must use guarded native writer");
assert.ok(!uiSource.includes("config/config_entries/options/flow"),
  "YAML must not open Home Assistant Options Flow");
assert.ok(uiSource.includes("this.dashboardChargerCreate(container)"),
  "New Chargers are created inside MultiCharge with native source selectors");
const Card=customElements.get("robotix-multicharge-card");
assert.ok(Card,"native custom card registered");
const Panel=customElements.get("robotix-multicharge-panel");
assert.ok(Panel,"native HA sidebar panel element registered");
const nativePanel=new Panel();
assert.ok(nativePanel._card instanceof Card,
  "sidebar reuses exactly the existing five-view native card");
assert.ok(nativePanel.shadowRoot.children.includes(nativePanel._content),
  "sidebar has standalone rendered content");

assert.equal(window.customCards.filter(c=>c.type==="robotix-multicharge-card").length,1);
const fixture={
  controller_id:"site",timezone:"Europe/Brussels",start:"2026-11-22T00:00:00+01:00",
  end:"2026-11-23T00:00:00+01:00",status:"proposed",
  configuration:{
    controller:{id:"site",name:"Sample",mode:"Ready By",max_parallel:2,max_power_kw:7},
    assets:[{id:"car",name:"Family car",kind:"car",plan_color:"pink",target_soc:80,
             ready_by:"2026-11-22T18:00:00+01:00"}],
    chargers:[{id:"drive",name:"Driveway",plan_color:"green",kind:"on_off",rated_power_kw:3.6,
               asset:"car",phase_count:1}]
  },
  plan_palette:{pink:"#B05D81",green:"#32816E",blue:"#3779B9"},
  preference_entities:{
    controller:{name:"text.site_name",mode:"select.site_mode",
                max_parallel:"number.site_parallel",max_power_kw:"number.site_kw",
                plan_label_mode:"select.site_labels",
                plan_color_by:"select.site_colors",
                show_indicative_forecast:"select.site_forecast"},
    assets:{car:{plan_color:"select.car_color",target_soc:"number.car_target",
                 ready_by:"datetime.car_ready_by",ready_by_repeat:"select.car_repeat",
                 priority:"number.car_priority"}},
    chargers:{drive:{plan_color:"select.drive_color",asset:"select.drive_vehicle"}}
  },
  observations:{
    assets:{car:{soc:{quality:"ok",value:20,reason:"OK"}}},
    chargers:{drive:{connected:{quality:"ok",value:true,reason:"OK"},
                     power_kw:{quality:"ok",value:2.3,reason:"OK"}}},
    sources:{tariff_quality:"SOURCE_NOT_SELECTED"}
  },
  slots:[{charger_id:"drive",asset_id:"car",start:"2026-11-22T12:00:00+01:00",
          end:"2026-11-22T12:15:00+01:00",proposed_power_kw:3.6,
          actual_power_kw:null,accepted_power_kw:null}],
  reasons:{drive:"PROPOSED"},shortfall_kwh:{drive:0}
};
function visit(node,visitor){
  visitor(node);
  for(const child of node.children||[])visit(child,visitor);
}
function find(node,tag,label){
  let found;
  visit(node,x=>{
    if(!found&&x.tag===tag&&(label===undefined||x.textContent===label))found=x;
  });
  return found;
}
function content(node){
  let text="";visit(node,x=>{if(x.textContent)text+=x.textContent+"\n";});return text;
}
async function main(){
  // UX-OWNER-01 one canonical object, complete settings and no second store.
  const owners=JSON.parse(JSON.stringify(fixture));
  Object.assign(owners.configuration.controller,{
    solar_source_kind:"grid_export",
    grid_power_direction:"import_positive",
    grid_power_entity:"sensor.site_grid",
    current_price_entity:"sensor.import_eur",
    export_price_entity:"sensor.export_eur",
    solar_power_entity:"sensor.roof_pv",
    home_power_entity:"sensor.house",
    solar_surplus_entity:"sensor.surplus",
    phase_limits_a:{L1:25,L2:32,L3:32},
    plan_label_mode:"both",
    plan_color_by:"vehicle",
    show_indicative_forecast:true,
  });
  Object.assign(owners.configuration.assets[0],{
    soc_stale_entity:"binary_sensor.car_soc_stale",
    vehicle_control_entity:"switch.vehicle_charge",
    vehicle_current_entity:"number.vehicle_current",
    capacity_kwh:72,
    charge_efficiency:0.92,
    max_charge_kw:11,
    minimum_soc_pct:30,
    price_currency:"EUR",
    maximum_price_per_kwh:0.20,
    ready_by_repeat:"specific_days",
    ready_by_weekdays:{mon:"07:00",fri:"18:00"},
    charging_windows:{sun:{start:"22:00",end:"06:00"}},
    expected_connection_at:"2026-11-24T19:00:00+01:00",
    opportunistic_kind:"type1",
  });
  Object.assign(owners.configuration.chargers[0],{
    control_owner:"external",physical_commissioned:false,
    control_entity:"switch.charger",
    connected_entity:"binary_sensor.plug",
    power_entity:"sensor.charge_power",
    energy_entity:"sensor.charge_energy",
    session_entity:"sensor.session",
    min_current_a:6,max_current_a:32,current_step_a:1,
    fixed_current_a:16,phase_ids:["L1"],phase_count:1,
    voltage_v:230,circuit_id:"garage",circuit_limit_a:32,
  });
  owners.completed_sessions=[{
    charger_id:"drive",asset_id:"historical_guest",
    started_at:"2026-11-21T20:00:00+01:00",
    ended_at:"2026-11-21T21:00:00+01:00",
    actual_energy_kwh:3.5,cost:null,
    stop_reason:"USER_STOP",physical_stop_confirmed:true,
  }];
  owners.preference_entities.controller.solar_source_kind="select.site_solar_kind";
  owners.preference_entities.controller.grid_power_direction="select.site_meter_sign";
  owners.preference_entities.controller.grid_power_entity="text.site_grid";
  owners.preference_entities.controller.current_price_entity="text.site_import";
  const siteCommands=[];
  const site=new Card();site.setConfig({});
  site.hass={user:{is_admin:true},language:"en",states:{},
    callWS:async()=>owners,
    callService:async(domain,action,args)=>{
      siteCommands.push({domain,action,args});
    }};
  await new Promise(resolve=>setImmediate(resolve));
  site._tab="Overview";site.render();
  const icon=find(site.shadowRoot,"ha-icon");
  assert.ok(icon&&icon.attributes.icon.startsWith("mdi:"),"Native visual icons must render");
  let battery;visit(site.shadowRoot,x=>{if(x.attributes?.role==="progressbar")battery=x;});
  assert.equal(battery?.attributes["aria-valuenow"],"20","Qualified battery is rendered");
  owners.observations.assets.car.soc={quality:"stale",value:20};
  site.render();battery=undefined;visit(site.shadowRoot,x=>{if(x.attributes?.role==="progressbar")battery=x;});
  assert.equal(battery,undefined,"Do not render an unqualified battery level");
  owners.observations.assets.car.soc={quality:"ok",value:20,reason:"OK"};
  site._tab="Settings";site._settingsOpen="Charging site";site.render();
  const siteText=content(site.shadowRoot);
  for(const label of ["Complete object settings & sources",
                      "Maximum per-phase current","Solar production sensor",
                      "Current import price source","Grid sensor sign",
                      "Show unreserved forecast"]){
    assert.ok(siteText.includes(label),"Site owner must expose "+label);
  }
  assert.ok(siteText.includes("L1: 25"),"Verified source phase limits visible");
  site._settingsOpen="Sources & bindings";site.render();
  const sourceText=content(site.shadowRoot);
  assert.ok(sourceText.includes("Solar source type"));
  assert.ok(sourceText.includes("sensor.site_grid"));
  assert.ok(sourceText.includes("Grid meter direction"));
  function ownerField(root,label){
    let x=null;visit(root,node=>{
      if(node.className==="field"&&node.children[0]?.textContent===label)
        x=node.children[1];
    });return x;
  }
  const sourceType=ownerField(site.shadowRoot,"Solar source type (native)");
  assert.ok(sourceType,"native solar source model editable on Site");
  sourceType.value="direct_surplus";sourceType.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(siteCommands.some(x=>x.domain==="select"&&
    x.args.entity_id==="select.site_solar_kind"&&
    x.args.option==="direct_surplus"),
    "Controller-native source mode uses owning HA service");
  const meterSign=ownerField(site.shadowRoot,"Grid meter direction (native)");
  assert.ok(meterSign);
  meterSign.value="export_positive";meterSign.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(siteCommands.some(x=>x.domain==="select"&&
    x.args.entity_id==="select.site_meter_sign"&&
    x.args.option==="export_positive"));

  const vehicle=new Card();vehicle.setConfig({});
  vehicle.hass={user:{is_admin:true},language:"en",states:{},
    callWS:async()=>owners};
  await new Promise(resolve=>setImmediate(resolve));
  vehicle._tab="Chargeable Assets";vehicle.render();
  find(vehicle.shadowRoot,"button","Details").click();
  const vehicleText=content(vehicle.shadowRoot);
  for(const label of ["Vehicle identity & lifetime","Goal & timing",
                      "Price & charging decisions","Battery & source references",
                      "Battery freshness sensor","Vehicle-native current setting",
                      "Allowed charging time windows","Opportunistic strategy"]){
    assert.ok(vehicleText.includes(label),"Vehicle object must expose "+label);
  }
  // Object-first D0 keeps novice actions visible; D3/D4 grouped properties
  // are native keyboard-accessible folds, not an intimidating long form.
  const vehicleFolds=[];
  visit(vehicle.shadowRoot,node=>{
    if(node.tag==="details"&&node.attributes["data-owner-group"])
      vehicleFolds.push(node);
  });
  assert.equal(vehicleFolds.length,4,
    "Every persisted Asset group must be in one owning foldable row");
  assert.ok(vehicleFolds.every(row=>row.open===false),
    "Expert Asset fields are initially collapsed without hiding novice actions");
  assert.ok(vehicleFolds.every(row=>
    row.children[0]?.tag==="summary"&&row.children[1]?.className==="owner-fields"),
    "Native summary/fields semantics support keyboard and dense layout");
  assert.ok(find(vehicle.shadowRoot,"button","Set charging goal"),
    "Novice Goal is not hidden in a technical fold");
  assert.ok(vehicleText.includes("binary_sensor.car_soc_stale"));
  assert.ok(vehicleText.includes("FRI: 18:00"),
    "Per-day Ready By remains under owning Vehicle");

  const evse=new Card();evse.setConfig({});
  evse.hass={user:{is_admin:true},language:"en",states:{},
    callWS:async()=>owners};
  await new Promise(resolve=>setImmediate(resolve));
  evse._tab="Chargers";evse.render();
  find(evse.shadowRoot,"button","Details").click();
  const evseText=content(evse.shadowRoot);
  for(const label of ["Physical Charger & verified sources",
                      "Identity & ownership","Connection & meter sources",
                      "Electrical hardware & circuit",
                      "Native Charger control switch","Circuit breaker limit",
                      "Cumulative Charger energy meter",
                      "Original vehicle at session time",
                      "historical_guest","Activation","Charging session","Charging state"]){
    assert.ok(evseText.includes(label),"Charger owner must expose "+label);
  }
  const chargerFolds=[];
  visit(evse.shadowRoot,node=>{
    if(node.tag==="details"&&node.attributes["data-owner-group"])
      chargerFolds.push(node);
  });
  assert.equal(chargerFolds.length,3,
    "Every persisted Charger group must remain in its owning foldable row");
  assert.ok(chargerFolds.every(row=>row.open===false));
  const historyFold=[];
  visit(evse.shadowRoot,node=>{
    if(node.tag==="details"&&node.attributes["data-disclosure"]===
       "charger:drive:history")historyFold.push(node);
  });
  assert.equal(historyFold.length,1,"Historical session must stay available");
  assert.equal(historyFold[0].open,false,
    "Previous sessions do not overwhelm the daily Charger status");
  assert.ok(evseText.includes("sensor.charge_energy"));
  assert.ok(evseText.includes("garage"));
  assert.ok(evseText.includes("USER_STOP")||evseText.includes("User stop"),
    "Receipt must show physical STOP reason");
  const ro=new Card();ro.setConfig({});
  ro.hass={user:{is_admin:false},states:{},callWS:async()=>owners};
  await new Promise(resolve=>setImmediate(resolve));
  ro._tab="Chargers";ro.render();
  find(ro.shadowRoot,"button","Details").click();
  assert.ok(content(ro.shadowRoot).includes("Native Charger control switch"),
    "Read-only user can observe owning technical configuration");
  assert.equal(find(ro.shadowRoot,"a","Configure in Home Assistant"),undefined,
    "Resident cannot acquire a configuration action from technical inventory");

  // UX-OWNER-03 quick-action from Overview must target the *chosen* Vehicle.
  const focused=JSON.parse(JSON.stringify(owners));
  focused.configuration.assets.push({
    id:"visitor",name:"Visitor",kind:"car",temporary:true,
    expires_at:"2026-11-24T22:00:00+01:00",requested_kwh:8.0,
  });
  const focus=new Card();focus.setConfig({});
  focus.hass={user:{is_admin:true},states:{},callWS:async()=>focused};
  await new Promise(resolve=>setImmediate(resolve));
  focus._tab="Overview";focus.render();
  const scheduleButtons=[];
  visit(focus.shadowRoot,node=>{
    if(node.tag==="button"&&node.textContent==="Schedule charging")
      scheduleButtons.push(node);
  });
  assert.equal(scheduleButtons.length,2);
  scheduleButtons[1].click();
  const focusedText=content(focus.shadowRoot);
  assert.equal(focus._tab,"Overview","Schedule editing stays on the selected vehicle card");
  assert.equal(focus._scheduleEditor,"visitor");
  assert.ok(focusedText.includes("When should the vehicle be ready?"));
  assert.ok(focusedText.includes("8 kWh"));
  assert.ok(!focusedText.includes("Vehicle + Charger ID inferred"),
    "Overview never rewrites historical identity from current assignment");

  // UX-ROW-01 novice goals: four goal types are visible on a normal Asset
  // without opening a hidden Settings or Details view. Exactly one atomic
  // Config Entry revision; no physical command or frontend goal database.
  function cardField(root,title){
    let field=null;
    visit(root,node=>{
      if(node.className==="field"&&node.children[0]?.textContent===title)
        field=node.children[1];
    });
    return field;
  }
  for(const [kind,value,field] of [
    ["soc",75,"target_soc"],
    ["energy",8.5,"requested_kwh"],
    ["duration",45,"requested_duration_minutes"],
    ["budget",10,"requested_budget_amount"],
  ]){
    const source=JSON.parse(JSON.stringify(fixture));
    source.configuration_revision="goal-1";
    const writes=[];
    const novice=new Card();
    novice.setConfig({});
    novice.hass={user:{is_admin:true},states:{},
      callWS:async request=>{
        writes.push(request);
        return request.type==="robotix_multicharge/update_settings"?
          {status:"accepted_unconfirmed",expected_revision:"goal-2"}:source;
      }
    };
    await new Promise(resolve=>setImmediate(resolve));
    novice._tab="Chargeable Assets";novice.render();
    const goalButton=find(novice.shadowRoot,"button","Set charging goal");
    assert.ok(goalButton,"A novice must see the primary Goal action on the Asset card");
    assert.equal(find(novice.shadowRoot,"button","Save charging goal"),undefined);
    goalButton.click();
    assert.ok(find(novice.shadowRoot,"button","Schedule charging"),
      "Charging days and times are one explicitly named action away");
    const choice=cardField(novice.shadowRoot,"I want to charge to");
    assert.ok(choice);
    assert.deepEqual(choice.children.map(x=>x.value),
                     ["soc","energy","duration","budget"]);
    choice.value=kind;choice.events.change();
    const amount=cardField(novice.shadowRoot,"Amount");
    assert.ok(amount);
    amount.value=String(value);amount.events.input();
    find(novice.shadowRoot,"button","Save charging goal").click();
    await new Promise(resolve=>setImmediate(resolve));
    const saves=writes.filter(x=>x.type==="robotix_multicharge/update_settings");
    assert.equal(saves.length,1,"one goal produces one transaction");
    assert.equal(saves[0].scope,"asset");
    assert.equal(saves[0].target_id,"car");
    assert.equal(saves[0].changes[field],value);
    for(const other of ["requested_kwh","requested_duration_minutes",
                        "requested_budget_amount"]){
      if(other!==field)assert.equal(saves[0].changes[other],null,
        "exclusive finite goal clears the previous requested type");
    }
    if(kind==="budget")assert.equal(saves[0].changes.requested_budget_currency,"EUR");
    assert.equal(writes.filter(x=>x.type==="robotix_multicharge/command").length,0);
  }
  // UX-ROW-02 the same visible Schedule action opens *both* native
  // weekday/deadline and allowed charging-time controls on the Asset card.
  const scheduleQuick=JSON.parse(JSON.stringify(fixture));
  scheduleQuick.configuration_revision="weekday-a";
  scheduleQuick.preference_entities.assets.car.ready_day_mon="select.mon_ready";
  scheduleQuick.preference_entities.assets.car.charging_window_mon="text.mon_window";
  const quickCard=new Card();
  quickCard.setConfig({});
  quickCard.hass={user:{is_admin:true},states:{},callWS:async()=>scheduleQuick};
  await new Promise(resolve=>setImmediate(resolve));
  quickCard._tab="Chargeable Assets";quickCard.render();
  find(quickCard.shadowRoot,"button","Schedule charging").click();
  assert.ok(content(quickCard.shadowRoot).includes("Charging days"),
    "Ready By weekday selector is shown without Details");
  assert.ok(content(quickCard.shadowRoot).includes("Allowed charging times"),
    "Actual permitted time windows are separately visible");
  assert.ok(find(quickCard.shadowRoot,"button","Hide charging schedule"));
  const readOnlyQuick=new Card();
  readOnlyQuick.setConfig({});
  readOnlyQuick.hass={user:{is_admin:false},states:{},callWS:async()=>scheduleQuick};
  await new Promise(resolve=>setImmediate(resolve));
  readOnlyQuick._tab="Chargeable Assets";readOnlyQuick.render();
  assert.equal(find(readOnlyQuick.shadowRoot,"button","Save charging goal"),undefined,
    "Non-admin only observes true goal and never gains write authority");

  // SCHEDULE-06 owner-native Specific days and time windows.
  const scheduleData=JSON.parse(JSON.stringify(fixture));
  scheduleData.configuration_revision="before-schedule";
  const asset=scheduleData.configuration.assets[0];
  asset.ready_by_repeat="specific_days";
  asset.ready_by_weekdays={mon:"06:45",wed:"08:30"};
  asset.charging_windows={mon:{start:"22:00",end:"06:00"}};
  const owned=scheduleData.preference_entities.assets.car;
  for(const day of ["mon","tue","wed","thu","fri","sat","sun"]){
    owned["ready_day_"+day]="select.car_day_"+day;
    owned["charging_window_"+day]="text.car_window_"+day;
  }
  owned.continuous_charging="select.car_continuity";
  owned.opportunistic_kind="select.car_opportunity";
  owned.price_currency="text.car_price_currency";
  owned.earliest_start_at="datetime.car_earliest";
  for(const field of ["minimum_soc_pct","maximum_price_per_kwh",
                       "low_price_trigger_per_kwh","low_soc_trigger_pct",
                       "opportunistic_level_pct"])
    owned[field]="number.car_"+field;
  const scheduleCalls=[];
  const scheduleCard=new Card();
  scheduleCard.setConfig({});
  scheduleCard.hass={
    user:{is_admin:true},language:"en",
    states:{
      "select.car_day_mon":{state:"06:45"},
      "select.car_day_wed":{state:"08:30"},
    },
    callWS:async msg=>{
      if(msg.type==="robotix_multicharge/update_settings"){
        scheduleCalls.push(msg);Object.assign(asset,msg.changes);scheduleData.configuration_revision="saved-schedule";
        return {status:"accepted_unconfirmed",expected_revision:"saved-schedule"};
      }
      return scheduleData;
    },
    callService:async(domain,service,args)=>{
      scheduleCalls.push({domain,service,args});
    },
  };
  await new Promise(resolve=>setImmediate(resolve));
  scheduleCard._tab="Chargeable Assets";scheduleCard.render();
  find(scheduleCard.shadowRoot,"button","Details").click();
  // PARITY-07 native continuous Select on the same Asset and Config Entry.
  let pattern;
  visit(scheduleCard.shadowRoot,node=>{
    if(node.className==="field"&&node.children[0]?.textContent==="Charging pattern")
      pattern=node.children[1];
  });
  assert.ok(pattern,"continuity is editable on the normal Asset card");
  assert.deepEqual(pattern.children.map(x=>x.value),["flexible","continuous"]);
  pattern.value="continuous";pattern.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(scheduleCalls.some(x=>x.domain==="select"&&
    x.args.entity_id==="select.car_continuity"&&x.args.option==="continuous"),
    "Continuous selection reaches native owner, not a second JS store");
  // PARITY-08 per-Asset price/SoC policy controls live on the same
  // owner-native device, and never write the provider tariff or OEM SoC.
  assert.ok(find(scheduleCard.shadowRoot,"button","Set price currency"));
  assert.ok(find(scheduleCard.shadowRoot,"button","Set earliest start"));
  assert.ok(content(scheduleCard.shadowRoot).includes(
    "Minimum charge before price limits"));
  assert.ok(content(scheduleCard.shadowRoot).includes(
    "Price ceiling per kWh"));
  let opportunity;
  visit(scheduleCard.shadowRoot,node=>{
    if(node.className==="field"&&
       node.children[0]?.textContent==="Opportunistic charging")
      opportunity=node.children[1];
  });
  assert.ok(opportunity);
  opportunity.value="type1";opportunity.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(scheduleCalls.some(call=>call.domain==="select"&&
    call.args.entity_id==="select.car_opportunity"&&
    call.args.option==="type1"),
    "native per-Asset opportunistic selection uses only existing settings writer");
  find(scheduleCard.shadowRoot,"button","Schedule charging").click();
  assert.ok(content(scheduleCard.shadowRoot).includes("Specific days"),
    "Single Weekly user option replaced by Specific days");
  assert.ok(!content(scheduleCard.shadowRoot).includes("Every week"),
    "Legacy single-weekday recurring option must not appear");
  let monday;
  visit(scheduleCard.shadowRoot,node=>{
    if(node.tag==="input"&&String(node.attributes.id||"").startsWith("multicharge-monday-"))monday=node;
  });
  assert.ok(monday,"Monday has an owned native weekday picker");
  const fieldIds=[];
  visit(scheduleCard.shadowRoot,node=>{
    if(node.attributes?.id)fieldIds.push(node.attributes.id);
  });
  assert.equal(new Set(fieldIds).size,fieldIds.length,
    "All displayed goal/weekday/price inputs must have unique DOM label IDs");
  monday.value="07:00";monday.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(!scheduleCalls.some(x=>x.type==="robotix_multicharge/update_settings"),"weekday remains a draft before Save");
  find(scheduleCard.shadowRoot,"button","Save schedule").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(scheduleCalls.some(x=>x.type==="robotix_multicharge/update_settings"&&x.changes.ready_by_weekdays.mon==="07:00"&&x.changes.ready_by_weekdays.wed==="08:30"),"one atomic schedule Save preserves other weekdays");
  find(scheduleCard.shadowRoot,"button","Schedule charging").click();
  find(scheduleCard.shadowRoot,"button","Allowed charging times").click();
  assert.ok(content(scheduleCard.shadowRoot).includes("Start hour"),
    "Allowed charging hours are distinct from Ready By");
  let startHour;
  visit(scheduleCard.shadowRoot,node=>{
    if(node.tag==="input"&&
      String(node.attributes.id||"").startsWith("multicharge-monday-start-hour-"))startHour=node;
  });
  assert.ok(startHour,"native time input exists for Monday");
  startHour.value="23:00";startHour.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(scheduleCalls.some(x=>x.domain==="text"&&
    x.args.entity_id==="text.car_window_mon"&&x.args.value==="23:00-06:00"),
    "allowed local charging window updates existing Asset HA Text");

  // Daily -> weekday chips -> individual override, without implicit Save.
  asset.ready_by_repeat="daily";asset.ready_by="2026-11-25T06:00:00+01:00";
  delete asset.ready_by_weekdays;
  scheduleCard._scheduleEditor="car";scheduleCard._windowsOpen="";scheduleCard._calendarDrafts={};scheduleCard.render();
  const priorSaves=scheduleCalls.filter(x=>x.type==="robotix_multicharge/update_settings").length;
  find(scheduleCard.shadowRoot,"button","Specific days").click();
  const dayButton=label=>{
    let result;visit(scheduleCard.shadowRoot,node=>{
      if(node.tag==="button"&&node.attributes["aria-label"]===label)result=node;
    });return result;
  };
  assert.equal(dayButton("Saturday").attributes["aria-pressed"],"true");
  dayButton("Saturday").click();dayButton("Sunday").click();
  find(scheduleCard.shadowRoot,"button","Different times per day").click();
  const friday=cardField(scheduleCard.shadowRoot,"Friday");
  assert.equal(friday.value,"06:00");
  friday.value="08:00";friday.events.change();
  assert.equal(scheduleCalls.filter(x=>x.type==="robotix_multicharge/update_settings").length,priorSaves);
  find(scheduleCard.shadowRoot,"button","Save schedule").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(scheduleCalls.filter(x=>x.type==="robotix_multicharge/update_settings").at(-1).changes.ready_by_weekdays,
    {mon:"06:00",tue:"06:00",wed:"06:00",thu:"06:00",fri:"08:00"});
  find(scheduleCard.shadowRoot,"button","Schedule charging").click();
  assert.equal(cardField(scheduleCard.shadowRoot,"Friday").value,"08:00");
  find(scheduleCard.shadowRoot,"button","Cancel").click();
  assert.equal(scheduleCalls.filter(x=>x.type==="robotix_multicharge/update_settings").length,priorSaves+1);

  // FLEX-06/08/11/17: Asset-side charger assignment writes to the one
  // Charger-owned Config Entry, never to a physical switch or duplicate store.
  const assignData=JSON.parse(JSON.stringify(fixture));
  assignData.configuration_revision="revision-a";
  assignData.configuration.assets.push(
    {id:"other_car",name:"Other car",kind:"car",requested_kwh:1}
  );
  assignData.configuration.chargers.push(
    {id:"patio",name:"Patio",kind:"on_off",rated_power_kw:3.6},
    {id:"occupied",name:"Occupied",kind:"on_off",rated_power_kw:3.6,
     asset:"other_car"}
  );
  const assignmentWS=[];
  const assignReadback=JSON.parse(JSON.stringify(assignData));
  const assignCard=new Card();
  assignCard.setConfig({});
  assignCard.hass={
    user:{is_admin:true},states:{},
    callWS:async request=>{
      assignmentWS.push(request);
      if(request.type==="robotix_multicharge/update_settings"){
        const assigned=request.changes.asset;
        for(const row of assignReadback.configuration.chargers){
          if(row.id===request.target_id){
            if(assigned===null)delete row.asset;else row.asset=assigned;
          }else if(assigned&&row.asset===assigned)delete row.asset;
        }
        assignReadback.configuration_revision="revision-"+assignmentWS.length;
        return {status:"accepted_unconfirmed",expected_revision:assignReadback.configuration_revision};
      }
      return assignReadback;
    }
  };
  await new Promise(resolve=>setImmediate(resolve));
  assignCard._tab="Overview";assignCard.render();
  assert.ok(content(assignCard.shadowRoot).indexOf("Charging site")<content(assignCard.shadowRoot).indexOf("Other car"));
  assert.ok(!content(assignCard.shadowRoot).includes("Quick charger assignment"));
  const changeCharger=find(assignCard.shadowRoot,"button","Change charger");
  assert.ok(changeCharger,
    "Asset offers a direct Charger assignment action on its normal card");
  changeCharger.click();
  let choice;
  visit(assignCard.shadowRoot,x=>{
    if(x.tag==="select"&&x.attributes["aria-label"]==="Select charger")choice=x;
  });
  assert.ok(choice,"Asset-side assignment offers a real native select");
  assert.deepEqual(choice.children.map(x=>x.value),["drive","patio"],
    "Occupied Charger must not silently evict its existing Vehicle");
  choice.value="patio";
  choice.events.change();
  const assignButton=find(assignCard.shadowRoot,"button","Assign selected charger");
  assert.equal(assignButton.disabled,false);
  assignButton.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(assignmentWS.some(x=>
    x.type==="robotix_multicharge/update_settings"&&x.scope==="charger"&&
    x.target_id==="patio"&&x.changes.asset==="car"&&
    x.expected_revision==="revision-a"
  ),"Asset-side move uses existing Charger writer with optimistic revision");
  const detach=find(assignCard.shadowRoot,"button","Unassign charger");
  assert.ok(detach,"Existing selected Charger offers explicit unassign");
  detach.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(assignmentWS.some(x=>
    x.type==="robotix_multicharge/update_settings"&&x.scope==="charger"&&
    x.target_id==="patio"&&Object.hasOwn(x.changes,"asset")&&
    x.changes.asset===null
  ),"Unassign clears the authoritative Charger.asset instead of deleting Asset");
  assert.equal(assignmentWS.filter(x=>x.type==="robotix_multicharge/command").length,0,
    "Move/unassign never sends hidden physical STOP or START");
  const blockedCard=new Card();
  blockedCard.setConfig({});
  blockedCard.hass={
    user:{is_admin:true},states:{},
    callWS:async request=>{
      if(request.type==="robotix_multicharge/update_settings")
        throw new Error("CHARGER_BUSY_STOP_FIRST");
      return assignData;
    }
  };
  await new Promise(resolve=>setImmediate(resolve));
  find(blockedCard.shadowRoot,"button","Chargeable Assets").click();
  find(blockedCard.shadowRoot,"button","Change charger").click();
  let blockedChoice;
  visit(blockedCard.shadowRoot,x=>{
    if(x.tag==="select"&&x.attributes["aria-label"]==="Select charger")
      blockedChoice=x;
  });
  blockedChoice.value="patio";blockedChoice.events.change();
  find(blockedCard.shadowRoot,"button","Assign selected charger").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(content(blockedCard.shadowRoot).includes(
    "Stop charging before changing charger"),
    "Denied physical idle readback must show a concrete user action");
  assert.equal(blockedCard._settingsFeedback.status,"rejected");
  const readonlyAssign=new Card();
  readonlyAssign.setConfig({});
  readonlyAssign.hass={
    user:{is_admin:false},states:{},callWS:async()=>assignData
  };
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(find(readonlyAssign.shadowRoot,"button","Change charger"),undefined,
    "Overview read-only resident cannot edit Charger assignment");
  find(readonlyAssign.shadowRoot,"button","Chargeable Assets").click();
  assert.equal(find(readonlyAssign.shadowRoot,"button","Change charger"),undefined,
    "Resident may view assignment but may not edit Charger-owned relation");

  // UC05/11/17: the empty/uncommissioned Charger remains usable for
  // finite request preparation. Physical START is disabled until independently
  // qualified native sources exist; no fake smart-plug cable evidence.
  const minimalData=JSON.parse(JSON.stringify(fixture));
  minimalData.configuration_revision="minimal-rev-a";
  minimalData.configuration.assets=[];
  minimalData.configuration.chargers=[{
    id:"plug",name:"Simple charger",kind:"on_off",rated_power_kw:1.8,
    control_entity:"switch.suitable_smart_plug"
  }];
  minimalData.command_capabilities={plug:{
    manual_one_off_allowed:false,
    manual_one_off_reason:"PHYSICAL_CONNECTION_UNVERIFIED",
    start_allowed:false,stop_allowed:false
  }};
  const manualWS=[];
  const minimalCard=new Card();
  minimalCard.setConfig({});
  minimalCard.hass={
    user:{is_admin:true},states:{},
    callWS:async request=>{
      manualWS.push(request);
      return request.type==="robotix_multicharge/command"?
        {status:"confirmed",action:"start"}:JSON.parse(JSON.stringify(minimalData));
    }
  };
  await new Promise(resolve=>setImmediate(resolve));
  find(minimalCard.shadowRoot,"button","Chargers").click();
  assert.ok(content(minimalCard.shadowRoot).includes("Manual one-off charge"),
    "An unassigned Charger must show bounded manual preparation even before commissioning");
  assert.ok(content(minimalCard.shadowRoot).includes("Connection not verified"),
    "Missing native cable evidence must produce a specific HOLD, not invented Connected");
  assert.equal(find(minimalCard.shadowRoot,"button","Start bounded session").disabled,true);
  function finiteInput(card,label){
    let input;
    visit(card.shadowRoot,node=>{
      if(node.className==="field" && node.children[0]?.textContent===label)
        input=node.children[1];
    });
    return input;
  }
  const minutesInput=finiteInput(minimalCard,"Time limit (minutes)");
  assert.ok(minutesInput);
  minutesInput.value="15";
  minutesInput.events.input();
  minimalCard.render();
  assert.equal(finiteInput(minimalCard,"Time limit (minutes)").value,"15",
    "Non-executed user draft survives a normal source repaint");
  assert.equal(manualWS.filter(r=>r.type==="robotix_multicharge/command").length,0,
    "No physical command may originate from a disabled manual setup");

  minimalData.command_capabilities.plug.manual_one_off_allowed=true;
  minimalData.command_capabilities.plug.manual_one_off_reason="READY";
  await minimalCard.load();
  const enabledStart=find(minimalCard.shadowRoot,"button","Start bounded session");
  assert.equal(enabledStart.disabled,false,
    "Existing safe executor remains reachable once qualification succeeds");
  enabledStart.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(manualWS.some(r=>r.type==="robotix_multicharge/command"&&
    r.charger_id==="plug"&&r.action==="start"&&r.duration_minutes===15),
    "Only a bounded real executor request can start an eligible manual session");

  // GUEST-UX-02: the selected objective alone determines readiness and request.
  minimalData.command_capabilities.plug.manual_goal_reasons={
    duration:"READY",energy:"MEASURED_ENERGY_METER_REQUIRED",budget:"BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE"
  };
  await minimalCard.load();
  const goalPicker=finiteInput(minimalCard,"Charging goal");
  goalPicker.value="budget";goalPicker.events.change();
  assert.equal(finiteInput(minimalCard,"Time limit (minutes)"),undefined,
    "Only the selected charging objective has a visible amount field");
  const moneyDraft=finiteInput(minimalCard,"Budget limit (€)");
  assert.ok(moneyDraft);
  moneyDraft.value="10";moneyDraft.events.input();
  assert.equal(find(minimalCard.shadowRoot,"button","Start bounded session").disabled,true);
  const beforeMoney=manualWS.filter(r=>r.type==="robotix_multicharge/command").length;
  assert.equal(manualWS.filter(r=>r.type==="robotix_multicharge/command").length,beforeMoney);
  minimalData.command_capabilities.plug.manual_goal_reasons.budget="READY";
  await minimalCard.load();
  assert.equal(finiteInput(minimalCard,"Budget limit (€)").value,"10");
  find(minimalCard.shadowRoot,"button","Start bounded session").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(manualWS.some(r=>r.type==="robotix_multicharge/command"&&
    r.action==="start"&&r.cost_amount===10&&r.currency==="EUR"&&r.duration_minutes===undefined),
    "Only the selected €10 objective reaches the owner-protected executor");

  // GUEST-UX-01: an ordinary Guest is created with an amount and relative
  // expiry, not a raw ISO timestamp edited by a resident.
  const guestData=JSON.parse(JSON.stringify(fixture));
  guestData.configuration.chargers.push({
    id:"guest_charger",name:"Guest Charger",kind:"on_off",
    rated_power_kw:3.6,
  });
  guestData.configuration_revision="guest-rev";
  const guestWS=[];
  const guestCard=new Card();
  guestCard.setConfig({});
  guestCard.hass={user:{is_admin:true},states:{},
    callWS:async msg=>{
      guestWS.push(msg);
      return msg.type==="robotix_multicharge/update_settings"?
        {status:"accepted_unconfirmed",expected_revision:"guest-next"}:guestData;
    }
  };
  await new Promise(resolve=>setImmediate(resolve));
  guestCard._tab="Chargeable Assets";guestCard.render();
  find(guestCard.shadowRoot,"button","Add asset").click();
  assert.ok(content(guestCard.shadowRoot).includes("Guest for"),
    "guest creation uses relative expiry rather than technical ISO text");
  function formField(card,label){
    let result;
    visit(card.shadowRoot,node=>{
      if(node.className==="field"&&node.children[0]?.textContent===label)
        result=node.children[1];
    });
    return result;
  }
  const guestName=formField(guestCard,"Asset name");
  const guestGoal=formField(guestCard,"Charging goal");
  const guestAmount=formField(guestCard,"Charging amount");
  const guestFreeCharger=formField(guestCard,"Select free charger (optional)");
  assert.ok(guestName&&guestGoal&&guestAmount&&guestFreeCharger);
  assert.deepEqual(guestFreeCharger.children.map(x=>x.value),
                   ["none","guest_charger"],
                   "one-step Guest can choose only a currently unassigned EVSE");
  guestName.value="Visitor";
  formField(guestCard,"Temporary guest").value="yes";
  guestGoal.value="budget";guestAmount.value="10";
  guestFreeCharger.value="guest_charger";
  find(guestCard.shadowRoot,"button","Create asset").click();
  await new Promise(resolve=>setImmediate(resolve));
  const create=guestWS.find(x=>
    x.type==="robotix_multicharge/update_settings"&&x.action==="create");
  assert.ok(create);
  assert.equal(create.changes.requested_budget_amount,10);
  assert.equal(create.changes.requested_budget_currency,"EUR");
  assert.equal(create.changes.assign_charger_id,"guest_charger",
               "one atomic revision binds a free EVSE to the new Guest");
  assert.equal(create.changes.temporary,true);
  assert.ok(Number.isFinite(Date.parse(create.changes.expires_at)),
    "Guest expiry is a real timestamp derived from selected duration");

  // MC-17: missing battery data can be completed directly from the plan.
  const incomplete=JSON.parse(JSON.stringify(fixture));
  incomplete.configuration_revision="battery-before";
  incomplete.goal_assessments={drive:{asset_id:"car",status:"cannot_assess",
    reason:"BATTERY_CAPACITY_NOT_CONFIGURED",conditional:true}};
  const batteryWrites=[];
  const batteryCard=new Card();batteryCard.setConfig({});
  batteryCard.hass={user:{is_admin:true},states:{},callWS:async msg=>{
    if(msg.type==="robotix_multicharge/update_settings"){
      batteryWrites.push(msg);
      Object.assign(incomplete.configuration.assets[0],msg.changes);
      incomplete.configuration_revision="battery-after";
      incomplete.goal_assessments.drive={asset_id:"car",status:"achievable",
        conditional:true,required_grid_kwh:1.56,planned_grid_kwh:1.8,shortfall_grid_kwh:0};
      return {status:"accepted_unconfirmed",expected_revision:"battery-after"};
    }
    return incomplete;
  }};
  await new Promise(resolve=>setImmediate(resolve));
  batteryCard._tab="Charging Plan";batteryCard.render();
  find(batteryCard.shadowRoot,"button","Complete battery data").click();
  const cap=cardField(batteryCard.shadowRoot,"Usable battery capacity (kWh)");
  const eff=cardField(batteryCard.shadowRoot,"Charging efficiency (%)");
  assert.ok(cap&&eff);
  cap.value="20";eff.value="90";cap.events.input();eff.events.input();
  find(batteryCard.shadowRoot,"button","Save battery data").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(batteryWrites.length,1);
  assert.deepEqual(batteryWrites[0].changes,{capacity_kwh:20,charge_efficiency:0.9});
  assert.ok(content(batteryCard.shadowRoot).includes("Goal achievable by deadline"));
  batteryCard.disconnectedCallback();

  // MC-18: view preferences survive remount; never store control settings.
  const displayStore=new Map();
  global.localStorage={getItem:key=>displayStore.get(key)||null,
    setItem:(key,value)=>displayStore.set(key,value)};
  const viewCard=new Card();
  viewCard.hass={user:{id:"view-user",is_admin:true},states:{},callWS:async()=>fixture};
  await new Promise(resolve=>setImmediate(resolve));
  viewCard.selectViewRange("both","charger:drive");
  await new Promise(resolve=>setImmediate(resolve));
  const reopened=new Card();
  const viewCalls=[];
  reopened.hass={user:{id:"view-user",is_admin:true},states:{},
    callWS:async msg=>{viewCalls.push(msg);return fixture;}};
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(reopened._day,"both");
  assert.equal(reopened._filter,"charger:drive");
  assert.equal(viewCalls[0].day,"both");
  assert.ok(!viewCalls[0].charger_id,"restored filter is validated against current configuration");
  find(reopened.shadowRoot,"button","Charging Plan").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(reopened._filter,"","Main plan tab resets the drill-down filter");
  assert.ok(!viewCalls.at(-1).charger_id&&!viewCalls.at(-1).asset_id);
  reopened.selectViewRange("both","asset:car");
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(viewCalls.at(-1).asset_id,"car");
  assert.ok(find(reopened.shadowRoot,"button","All chargers"));
  find(reopened.shadowRoot,"button","All chargers").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(reopened._filter,"");
  reopened.selectViewRange("both","asset:car");
  await new Promise(resolve=>setImmediate(resolve));
  find(reopened.shadowRoot,"button","Overview").click();
  find(reopened.shadowRoot,"button","Charging Plan").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(reopened._filter,"");
  assert.ok(!viewCalls.at(-1).asset_id);
  assert.equal(reopened._day,"both");
  reopened.disconnectedCallback();
  const retained=viewCard._data;
  viewCard._hass={...viewCard._hass,callWS:async()=>{throw Error("timeout");}};
  await viewCard.load();
  assert.equal(viewCard._data,retained);
  assert.equal(viewCard.canManage(),false);
  assert.ok(content(viewCard.shadowRoot).includes("Last available data"));
  assert.ok(!content(viewCard.shadowRoot).includes("Install MultiCharge once"));
  viewCard.disconnectedCallback();
  delete global.localStorage;

  // A structural/config revision ends a pending local draft. It is never a
  // second persisted charge-request store or a physical session.
  minimalData.configuration_revision="minimal-rev-b";
  await minimalCard.load();
  assert.equal(finiteInput(minimalCard,"Time limit (minutes)").value,"");
  const residentMinimal=new Card();
  residentMinimal.setConfig({});
  residentMinimal.hass={user:{is_admin:false},states:{},callWS:async()=>minimalData};
  await new Promise(resolve=>setImmediate(resolve));
  find(residentMinimal.shadowRoot,"button","Chargers").click();
  assert.equal(find(residentMinimal.shadowRoot,"button","Start bounded session"),undefined,
    "Resident read access never exposes admin-only manual command");

  // UC15: tariff-period native Recorder costs are explicitly indicative,
  // never displayed as a verified bill or written back to HA persistence.
  const pricedData=JSON.parse(JSON.stringify(fixture));
  pricedData.completed_sessions=[{
    charger_id:"drive",asset_id:"car",ended_at:"2026-11-22T12:30:00+01:00",
    actual_energy_kwh:1.5,energy_quality:"measured",cost:null,currency:null,
    cost_quality:"unknown",physical_stop_confirmed:true,
    estimated_variable_cost:0.42,estimated_variable_cost_currency:"EUR",
    estimated_variable_cost_energy_kwh:1.5,
    estimated_variable_cost_quality:"observed_power_integral_effective_tariff",
    estimated_variable_cost_basis:"indicative_variable_energy_only"
  }];
  const pricedCard=new Card();
  pricedCard.setConfig({});
  pricedCard.hass={user:{is_admin:false},states:{},
    callWS:async()=>pricedData};
  await new Promise(resolve=>setImmediate(resolve));
  find(pricedCard.shadowRoot,"button","Chargers").click();
  const pricedText=content(pricedCard.shadowRoot);
  assert.ok(pricedText.includes("Indicative variable energy cost"),
    "Multi-tariff measured power estimate must have a distinct honest label");
  assert.ok(pricedText.includes("0.42 EUR"));
  assert.ok(pricedText.includes("Power-derived estimate, not a bill"),
    "A derived variable estimate must never impersonate billed actual money");
  assert.equal(pricedData.completed_sessions[0].cost,null,
    "Read-only financial presentation cannot overwrite persisted cost");

  // UC07: native variable all-in references and spot quotes are not bills.
  const referenceData=JSON.parse(JSON.stringify(fixture));
  referenceData.observations.sources.current_price={
    quality:"ok",value:0.24,currency:"EUR",basis:"variable_reference"
  };
  const priceCard=new Card();
  priceCard.setConfig({});
  priceCard.hass={user:{is_admin:false},states:{},
    callWS:async()=>referenceData};
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(content(priceCard.shadowRoot).includes("Variable reference price"),
    "Overview must disclose native all-in prices as reference not invoices");
  referenceData.observations.sources.current_price.basis="spot";
  await priceCard.load();
  assert.ok(content(priceCard.shadowRoot).includes("Spot price"),
    "Wholesale/spot quote must not be labelled an all-in bill");

  const adjustableFixture=JSON.parse(JSON.stringify(fixture));
  adjustableFixture.configuration.chargers[0].kind="variable_current";
  Object.assign(adjustableFixture.configuration.chargers[0],{
    min_current_a:6,max_current_a:16,voltage_v:230,phase_ids:["L1"],
    min_charging_power_kw:1.84,max_charging_power_kw:3.22
  });
  Object.assign(adjustableFixture.preference_entities.chargers.drive,{
    min_charging_power_kw:"number.drive_min_kw",
    max_charging_power_kw:"number.drive_max_kw",
    set_charging_power_kw:"number.drive_set_kw"
  });
  const adjustableCard=new Card();
  adjustableCard.setConfig({});
  adjustableCard.hass={user:{is_admin:true},states:{},
    callWS:async()=>adjustableFixture};
  await new Promise(resolve=>setImmediate(resolve));
  find(adjustableCard.shadowRoot,"button","Chargers").click();
  find(adjustableCard.shadowRoot,"button","Details").click();
  const adjustableText=content(adjustableCard.shadowRoot);
  assert.ok(adjustableText.includes("Minimum charging power"));
  assert.ok(adjustableText.includes("Maximum charging power"));
  assert.ok(adjustableText.includes("Set charging power"));
  const fixedCard=new Card();
  fixedCard.setConfig({});
  fixedCard.hass={user:{is_admin:true},states:{},callWS:async()=>fixture};
  await new Promise(resolve=>setImmediate(resolve));
  find(fixedCard.shadowRoot,"button","Chargers").click();
  find(fixedCard.shadowRoot,"button","Details").click();
  assert.ok(content(fixedCard.shadowRoot).includes("On/off only"));
  // Power controls live directly in the Charger view and write ONLY the
  // MultiCharge-owned HA Number entity (never a provider Amp endpoint).
  const chargeNative=[];
  adjustableCard._hass.callService=async(domain,service,payload)=>{
    chargeNative.push({domain,service,payload});
  };
  let powerInput, powerApply;
  visit(adjustableCard.shadowRoot,node=>{
    if(node.tag==="div"&&node.children?.some(child=>
      child.tag==="input"&&child.attributes["aria-label"]==="Set charging power")){
      powerInput=node.children.find(child=>child.tag==="input");
      powerApply=node.children.find(child=>child.tag==="button");
    }
  });
  assert.ok(powerInput&&powerApply,"Set power is directly editable in Charger dashboard");
  powerInput.value="2.30";
  powerApply.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(chargeNative[0],{
    domain:"number",service:"set_value",
    payload:{entity_id:"number.drive_set_kw",value:2.3}
  });
  assert.equal(adjustableCard._settingsFeedback.status,"accepted_unconfirmed",
    "An HA service call cannot invent physical power readback");

  const commands=[];
  const card=new Card();
  card.setConfig({});
  card.hass={user:{is_admin:true},states:{},callWS:async request=>{commands.push(request);return fixture;}};
  await new Promise(resolve=>setImmediate(resolve));
  const resident=new Card();
  const residentCommands=[];
  resident.setConfig({});
  resident.hass={user:{is_admin:false},states:{},
    callWS:async request=>{residentCommands.push(request);return fixture;}};
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(residentCommands[0].type,"robotix_multicharge/get_plan",
    "resident reads same canonical authenticated dashboard");
  assert.ok(content(resident.shadowRoot).includes("Family car"),
    "resident can see actual source-backed dashboard");
  find(resident.shadowRoot,"button","Settings").click();
  assert.ok(content(resident.shadowRoot).includes("Charging site"),
    "resident can inspect settings without admin writes");
  assert.ok(!find(resident.shadowRoot,"a"),
    "resident has no admin configuration navigation");
  assert.ok(!find(resident.shadowRoot,"button","Edit"),
    "resident cannot invoke owning HA settings controls");
  // Imported YAML is the only settings authority, even for HA admins.
  // Monitoring and qualified physical commands remain separate concerns.
  const yamlCard=new Card();
  yamlCard.setConfig({});
  yamlCard.hass={user:{is_admin:true},states:{},
    callWS:async request=>({...fixture,configuration_managed_by_yaml:true})};
  await new Promise(resolve=>setImmediate(resolve));
  yamlCard._tab="Settings";yamlCard.render();
  assert.ok(content(yamlCard.shadowRoot).includes("Legacy file-owned configuration is read-only"),
    "YAML-managed settings clearly disclose their authority");
  assert.ok(!find(yamlCard.shadowRoot,"button","Edit"),
    "YAML-managed configuration must not advertise writable settings");
  assert.ok(!find(yamlCard.shadowRoot,"button","Edit JSON"),
    "External YAML source cannot be overwritten from a second UI editor");
  assert.ok(!find(resident.shadowRoot,"button","Edit JSON"),
    "Non-admin must never access native configuration transaction");
  assert.ok(find(resident.shadowRoot,"button","Edit YAML"),
    "Editor action is discoverable even when frontend admin role is unavailable");
  assert.ok(find(yamlCard.shadowRoot,"button","Edit YAML"),
    "File-owned origin is visible; server authority rejects any attempted write");


  // Dashboard-only: one typed object field, one secured Config Entry writer.
  const dashboardCalls=[];
  const editorFixture=JSON.parse(JSON.stringify(fixture));
  editorFixture.configuration_revision="12345678901234567890";
  const editorCard=new Card();
  editorCard.setConfig({});
  editorCard.hass={user:{is_admin:true},states:{
    "sensor.live_price":{state:"0.23"}
  },callWS:async request=>{
    dashboardCalls.push(request);
    if(request.type==="robotix_multicharge/get_plan")return editorFixture;
    if(request.type==="robotix_multicharge/yaml_configuration"){
      assert.equal(request.expected_revision,"98765432109876543210");
      assert.ok(!Object.hasOwn(request,"operation"));
      assert.ok(!Object.hasOwn(request,"reviewed_revision"));
      editorFixture.configuration=JSON.parse(request.yaml_text);
      editorFixture.configuration_revision="yaml-change-2";
      return {status:"accepted_unconfirmed",
        expected_revision:"yaml-change-2"};
    }
    assert.equal(request.type,"robotix_multicharge/update_settings");
    assert.equal(request.structural,true);
    if(request.scope==="controller"&&request.changes.name){
      editorFixture.configuration.controller.name=request.changes.name;
    }else if(request.scope==="charger"&&request.action==="create"){
      editorFixture.configuration.chargers.push({
        id:request.target_id,...request.changes,control_owner:"external",
        physical_commissioned:false
      });
    }
    editorFixture.configuration_revision="98765432109876543210";
    return {status:"accepted_unconfirmed",
      expected_revision:"98765432109876543210"};
  }};
  await new Promise(resolve=>setImmediate(resolve));
  editorCard._tab="Settings";
  editorCard._settingsOpen="Charging site";
  editorCard._editingField="controller:site:name";
  editorCard.render();
  let typed=null;
  visit(editorCard.shadowRoot,x=>{
    if(x.className==="dashboard-field-edit")typed=x;
  });
  assert.ok(typed,"Controller fields expose typed in-dashboard editor");
  const typedInput=find(typed,"input");
  assert.ok(typedInput);
  typedInput.value="Updated Wessels home";
  find(typed,"button","Save").click();
  await new Promise(resolve=>setImmediate(resolve));
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(dashboardCalls.some(x=>x.scope==="controller"&&
    x.changes.name==="Updated Wessels home"&&x.structural===true),
    "Dashboard Save sends one typed field to the canonical Config Entry");
  assert.equal(editorFixture.configuration.controller.name,"Updated Wessels home");
  assert.equal(editorCard._editingField,"");
  editorCard._tab="Chargers";editorCard.render();
  const addChargerInDashboard=find(editorCard.shadowRoot,"button","Add charger");
  assert.ok(addChargerInDashboard,
    "Chargers can be created without opening Home Assistant Options");
  addChargerInDashboard.click();
  assert.ok(content(editorCard.shadowRoot).includes("Stable charger ID"));
  assert.ok(!dashboardCalls.some(x=>
    String(x.type).includes("yaml_configuration")||
    String(x.type).includes("dashboard_config")),
    "Typed everyday configuration never uses raw document editors or physical commands");

  // UC02: one prefilled large editor, one direct Save into canonical Config Entry.
  editorCard._tab="Settings";editorCard._settingsOpen="";editorCard.render();
  const editYaml=find(editorCard.shadowRoot,"button","Edit YAML");
  assert.ok(editYaml,"Settings exposes the owner-requested YAML editor");
  editYaml.click();
  const yamlInput=find(editorCard.shadowRoot,"textarea");
  assert.ok(yamlInput&&yamlInput.value.includes('"controller"')&&
    yamlInput.value.includes('"chargers"'),
    "Multiline editor starts from the authoritative full configuration");
  assert.ok(yamlInput.attributes.rows==="22");
  const yamlRoot=editorCard.shadowRoot;
  const newDocument=JSON.parse(yamlInput.value);
  newDocument.controller.name="Edited complete YAML";
  yamlInput.value=JSON.stringify(newDocument,null,2);
  yamlInput.events.input();
  const saveYaml=find(yamlRoot,"button","Save");
  assert.ok(saveYaml&&!saveYaml.disabled,"Save available immediately without Review");
  assert.ok(!find(yamlRoot,"button","Review changes"),"No artificial Review step");
  // HA source refresh while typing cannot unmount or replace the textarea.
  editorCard.hass={...editorCard._hass,states:{
    "sensor.live_price":{state:"0.45"}
  }};
  assert.equal(editorCard.shadowRoot,yamlRoot);
  assert.equal(find(editorCard.shadowRoot,"textarea"),yamlInput);
  assert.equal(yamlInput.value,JSON.stringify(newDocument,null,2));
  saveYaml.click();
  await new Promise(resolve=>setImmediate(resolve));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(editorFixture.configuration.controller.name,"Edited complete YAML");
  assert.ok(dashboardCalls.some(x=>x.type==="robotix_multicharge/yaml_configuration"&&
    x.expected_revision==="98765432109876543210"&&
    !Object.hasOwn(x,"operation")),
    "Single Save sends YAML to the same existing HA Config Entry");
  assert.ok(!find(editorCard.shadowRoot,"textarea"),
    "Editor closes only after authoritative configuration readback");
  assert.ok(!dashboardCalls.some(x=>String(x.type).includes("options/flow")),
    "YAML editing never opens the retired Home Assistant Options Flow");

  const cancelYaml=find(editorCard.shadowRoot,"button","Edit YAML");
  cancelYaml.click();
  const abandoned=find(editorCard.shadowRoot,"textarea");
  abandoned.value="not valid yet";
  abandoned.events.input();
  find(editorCard.shadowRoot,"button","Cancel").click();
  assert.ok(!find(editorCard.shadowRoot,"textarea"),
    "Explicit Cancel exits without writing an unsaved draft");
  assert.equal(editorFixture.configuration.controller.name,"Edited complete YAML");

  // A detached sidebar/card cannot leak retries or accept an old snapshot.
  const lifecycleCard=new Card();
  let resolveOld;
  const oldResponse=new Promise(resolve=>{resolveOld=resolve;});
  let lifecycleReads=0;
  const lifecycleData=JSON.parse(JSON.stringify(fixture));
  lifecycleData.configuration.controller.home_power_entity="sensor.lifecycle_home";
  lifecycleCard._hass={user:{is_admin:true},states:{},callWS:async()=>{
    lifecycleReads++;return lifecycleReads===1?oldResponse:lifecycleData;
  }};
  const oldLoad=lifecycleCard.load();
  lifecycleCard.scheduleSourceRefresh();
  lifecycleCard.disconnectedCallback();
  resolveOld(lifecycleData);
  await oldLoad;
  assert.equal(lifecycleCard._data,null,"Detached view rejects its late snapshot");
  assert.equal(lifecycleCard._refreshTimer,null);
  assert.equal(lifecycleCard._refreshPending,false);
  lifecycleCard.connectedCallback();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(lifecycleReads,2);
  assert.equal(lifecycleCard._data,lifecycleData,"Reconnect reads a fresh snapshot");
  const watch=lifecycleCard.watchedEntities();
  assert.ok(watch.includes("sensor.lifecycle_home"));
  assert.equal(lifecycleCard.watchedEntities(),watch,"Unchanged snapshot reuses watch list");
  lifecycleCard._data={...lifecycleData,configuration:{...lifecycleData.configuration,
    controller:{...lifecycleData.configuration.controller,home_power_entity:"sensor.new_home"}}};
  assert.ok(lifecycleCard.watchedEntities().includes("sensor.new_home"));
  assert.ok(!lifecycleCard.watchedEntities().includes("sensor.lifecycle_home"));
  lifecycleCard.disconnectedCallback();

  // UC14-UX-INPUT-PERSISTENCE-01: passive HA/Sensor refresh must never
  // unmount an editor or discard a typed field, even after input blur.
  const typingData=JSON.parse(JSON.stringify(fixture));
  typingData.configuration_revision="typed-1";
  typingData.configuration.controller.solar_power_entity="sensor.first";
  const typingCard=new Card();
  let received=typingData;
  let reads=0;
  const makeHass=power=>({
    user:{is_admin:true},
    states:{"sensor.first":{state:String(power)}},
    callWS:async message=>{
      assert.equal(message.type,"robotix_multicharge/get_plan");
      reads++;return received;
    }
  });
  typingCard.hass=makeHass(1);
  await new Promise(resolve=>setImmediate(resolve));
  typingCard._tab="Settings";
  typingCard._settingsOpen="Sources & bindings";
  typingCard._editingField="controller:site:solar_power_entity";
  typingCard.render();
  let inputPanel=null;
  visit(typingCard.shadowRoot,node=>{
    if(node.className==="dashboard-field-edit")inputPanel=node;
  });
  assert.ok(inputPanel,"Settings must show typed dashboard edit field");
  const typedDraft=find(inputPanel,"input");
  assert.ok(typedDraft);
  typedDraft.value="sensor.user_is_typing_slowly";
  typingCard.shadowRoot.activeElement=typedDraft;
  const originalNodes=typingCard.shadowRoot.children;
  received={...typingData,observations:{
    ...typingData.observations,sources:{tariff_quality:"SOURCE_LATE"}
  }};
  const before=reads;
  typingCard.hass=makeHass(2);
  await typingCard.load();
  assert.ok(reads>before,"A source refresh still fetches new real data");
  assert.equal(typingCard._data.observations.sources.tariff_quality,"SOURCE_LATE");
  assert.equal(typingCard.shadowRoot.children,originalNodes,
    "Focus must retain the exact DOM and keyboard during background source refresh");
  assert.equal(typedDraft.value,"sensor.user_is_typing_slowly");
  assert.equal(typingCard._editingField,"controller:site:solar_power_entity",
    "The open editor never auto closes");
  typingCard.shadowRoot.activeElement=null;
  typingCard.shadowRoot.events.input({target:{tagName:"INPUT"}});
  await typingCard.load();
  assert.equal(typingCard.shadowRoot.children,originalNodes,
    "Dirty data remains mounted even after the keyboard loses focus");
  // The actual 350ms coalescing timer must not cause a redraw either.
  typingCard.scheduleSourceRefresh();
  await new Promise(resolve=>setTimeout(resolve,420));
  assert.equal(typingCard.shadowRoot.children,originalNodes);
  assert.equal(typedDraft.value,"sensor.user_is_typing_slowly");
  // A user-initiated Cancel or navigation is the only exit from an edit.
  typingCard._editingField="";
  typingCard.render();
  assert.notEqual(typingCard.shadowRoot.children,originalNodes,
    "Explicit Cancel allows a fresh paint");
  assert.equal(typingCard._unsavedInput,false);
  // Every form family uses the same source-safe repaint path, including
  // always-visible native Number fields and new Guest/Charger forms.
  typingCard._settingsOpen="Charging site";
  typingCard.render();
  let nativeNumberInput;
  visit(typingCard.shadowRoot,node=>{
    if(node.tag==="input"&&node.attributes["aria-label"]==="Parallel chargers")
      nativeNumberInput=node;
  });
  assert.ok(nativeNumberInput,"Native site number exists without a popup");
  nativeNumberInput.value="9";
  typingCard.shadowRoot.activeElement=nativeNumberInput;
  const numberNodes=typingCard.shadowRoot.children;
  await typingCard.load();
  assert.equal(typingCard.shadowRoot.children,numberNodes,
    "A focused native number survives source-only updates");
  typingCard.shadowRoot.events.input({target:{tagName:"INPUT"}});
  typingCard.shadowRoot.activeElement=null;
  await typingCard.load();
  assert.equal(nativeNumberInput.value,"9",
    "A blurred but dirty native number is never reset by passive refresh");

  typingCard._tab="Chargeable Assets";
  typingCard._assetEditor="new";
  typingCard.render();
  let guestForm;
  visit(typingCard.shadowRoot,node=>{
    if(node.tag==="form"&&content(node).includes("Add a chargeable asset"))
      guestForm=node;
  });
  assert.ok(guestForm);
  const pendingGuestName=find(guestForm,"input");
  pendingGuestName.value="A slow guest name";
  const guestNodes=typingCard.shadowRoot.children;
  await typingCard.load();
  assert.equal(typingCard.shadowRoot.children,guestNodes,
    "New Guest form must stay mounted with an unsubmitted name");
  assert.equal(pendingGuestName.value,"A slow guest name");

  typingCard._tab="Chargers";
  typingCard._createCharger=true;
  typingCard.render();
  let chargerForm;
  visit(typingCard.shadowRoot,node=>{
    if(node.className==="card dashboard-create")chargerForm=node;
  });
  assert.ok(chargerForm);
  const chargerName=find(chargerForm,"input");
  chargerName.value="My new charger";
  const chargerNodes=typingCard.shadowRoot.children;
  await typingCard.load();
  assert.equal(typingCard.shadowRoot.children,chargerNodes,
    "New Charger form must stay mounted during sensor refresh");
  assert.equal(chargerName.value,"My new charger");

  typingCard._createCharger=false;
  typingCard.render();
  const normalNodes=typingCard.shadowRoot.children;
  await typingCard.load();
  assert.notEqual(typingCard.shadowRoot.children,normalNodes,
    "After explicit form close, idle tab source refresh must resume");
  typingCard.disconnectedCallback();

  // The native sidebar forwards HA's authenticated hass object to the
  // same canonical card and exposes all five tabs to a non-admin resident.
  const residentPanel=new Panel();
  const residentPanelCalls=[];
  residentPanel.hass={user:{is_admin:false},states:{},
    callWS:async request=>{residentPanelCalls.push(request);return fixture;}};
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(residentPanelCalls[0]?.type,"robotix_multicharge/get_plan");
  assert.equal(residentPanel._card._data,fixture);
  for(const view of ["Overview","Charging Plan","Chargeable Assets","Chargers","Settings"]){
    residentPanel._card._tab=view;
    residentPanel._card.render();
    assert.ok(content(residentPanel._card.shadowRoot).length>0,
      "resident sidebar renders "+view);
  }
  assert.ok(commands.length>0);
  assert.equal(commands[0].type,"robotix_multicharge/get_plan");
  // A newly installed Controller with no Chargers must not show an empty
  // hour grid, tariff legend or fictitious missing-measurement incident.
  const emptyCard=new Card();
  emptyCard.setConfig({});
  emptyCard.hass={user:{is_admin:true},states:{},callWS:async()=>({
    ...fixture,configuration:{
      controller:{id:"home",name:"Home charging",mode:"Off",max_parallel:1},
      assets:[],chargers:[]
    },slots:[],forecast_slots:[],measured_slots:[],price_slots:[]
  })};
  await new Promise(resolve=>setImmediate(resolve));
  emptyCard._tab="Charging Plan";emptyCard.render();
  assert.ok(content(emptyCard.shadowRoot).includes("No charging points"),
    "Empty charging plan explains why there is no chart");
  emptyCard._tab="Chargers";emptyCard.render();
  assert.ok(find(emptyCard.shadowRoot,"button","Add charger"),
    "Empty setup is completed in dashboard, not HA Options");
  emptyCard._tab="Charging Plan";emptyCard.render();
  assert.ok(!find(emptyCard.shadowRoot,"svg"),
    "Empty charging plan does not render a fictitious plot");
  assert.ok(!content(emptyCard.shadowRoot).includes("Measured power unavailable"),
    "Empty charging plan does not claim a missing measurement incident");
  emptyCard._tab="Overview";emptyCard.render();
  assert.ok(content(emptyCard.shadowRoot).includes("Configure a charger to begin"),
    "Empty overview states the necessary next action");
  assert.ok(find(emptyCard.shadowRoot,"button","Add charger"),
    "Empty overview opens the actual MultiCharge Charger setup form");
  assert.ok(!content(emptyCard.shadowRoot).includes("No data"),
    "Empty overview does not misrepresent unconfigured site as failed readings");
  assert.ok(!require("node:fs").readFileSync(
    require("node:path").join(__dirname,
      "../custom_components/robotix_multicharge/frontend/robotix-multicharge.js"),
    "utf8").includes("mcIdentityColor"),
    "plan colors only use the owning Charger or ChargeableAsset preference");
  assert.ok(content(card.shadowRoot).includes("Family car"));
  assert.ok(content(card.shadowRoot).includes("2.30 kW"));
  find(card.shadowRoot,"button","Charging Plan").click();
  const apexRegions=[];
  visit(card.shadowRoot,node=>{
    if(node.attributes?.["data-chart-engine"]==="apexcharts-3.49.1")
      apexRegions.push(node);
  });
  assert.ok(apexRegions.length>=1,
    "Locally packaged ApexCharts power-price and native Charger timelines configured");
  assert.ok(apexRegions.every(node=>node.attributes["role"]==="img"),
    "Every interactive chart includes a readable alternative");

  // UX-ROW-03 aggregate power-price chart: one combined Basic-inspired
  // timeline above every dynamic vehicle/EVSE row, no static Wessels IDs.
  assert.ok(find(card.shadowRoot,"button","48h"),
    "Today, Tomorrow and 48h period choice must be visible");
  let combined=[];
  visit(card.shadowRoot,node=>{
    if(String(node.className||"").split(" ").includes("combined-plan"))combined.push(node);
  });
  assert.equal(combined.length,1,
    "exactly one power/price overview, not separate duplicate graphs");
  assert.ok(content(combined[0]).includes("All charging · Power & price"));
  assert.ok(content(card.shadowRoot).includes("Charging per vehicle and charger"));
  assert.ok(content(card.shadowRoot).includes("Family car · Driveway"));
  find(card.shadowRoot,"button","48h").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(commands.at(-1).day,"both",
    "48h uses one native read-only HA query, not a second price source");
  const multiPlan=JSON.parse(JSON.stringify(fixture));
  multiPlan.configuration.chargers=[
    ...fixture.configuration.chargers,
    ...Array.from({length:9},(_,i)=>({
      id:"charger_"+(i+2),name:"Charger "+(i+2),
      kind:"on_off",rated_power_kw:3.6,phase_count:1,
      asset:i%2===0?"car":undefined
    }))
  ];
  multiPlan.price_slots=[
    {start:"2026-11-22T12:00:00+01:00",
     end:"2026-11-22T12:15:00+01:00",
     price_per_kwh:0.24,currency:"EUR",basis:"spot"},
    {start:"2026-11-22T12:15:00+01:00",
     end:"2026-11-22T12:30:00+01:00",
     price_per_kwh:0.10,currency:"EUR",basis:"spot"}
  ];
  multiPlan.actual_slots=[{
    charger_id:"drive",asset_id:null,
    start:"2026-11-22T12:00:00+01:00",
    end:"2026-11-22T12:15:00+01:00",
    actual_power_kw:2.2,
    asset_provenance:"unattributed_charger_actual",
    quality:"measured_power_integral",
  }];
  const many=new Card();many.setConfig({});
  many.hass={user:{is_admin:false},states:{},callWS:async()=>multiPlan};
  await new Promise(resolve=>setImmediate(resolve));
  many._tab="Charging Plan";many.render();
  let lanes=[],plot;
  visit(many.shadowRoot,node=>{
    if(node.className==="plan-lane")lanes.push(node);
    if(String(node.className||"").split(" ").includes("combined-plan"))plot=node;
  });
  assert.equal(lanes.length,10,
    "All 10 real Charger objects get their own dynamic detail lane");
  assert.ok(content(plot).includes("spot · EUR/kWh"),
    "Price is explicitly marked as spot and never an invoice");
  assert.ok(content(plot).includes("Measured"),
    "Actual kW stays separate from proposed or accepted");
  assert.ok(content(many.shadowRoot).includes("vehicle may be unknown"),
    "Charger metering is shown without fabricating historical Vehicle identity");
  multiPlan.observations.sources.tariff_tomorrow_quality="INTERVAL_COVERAGE_INCOMPLETE";
  many.render();
  assert.ok(content(many.shadowRoot).includes("Tomorrow · Future tariff intervals · Interval coverage incomplete"),
    "Invalid tomorrow is disclosed even while today has valid price slots");
  assert.ok(content(many.shadowRoot).includes("spot · EUR/kWh"),
    "Tomorrow coverage warning must preserve today's valid chart");
  const last=multiPlan.configuration.chargers[9];
  assert.ok(content(many.shadowRoot).includes(last.name),
    "Last Charger lane remains available; no four-fixed-charger limit");
  multiPlan.price_slots=[];
  many.render();
  let without;
  visit(many.shadowRoot,node=>{
    if(String(node.className||"").split(" ").includes("combined-plan"))without=node;
  });
  assert.ok(content(without).includes("Price unavailable"),
    "No missing price is silently rendered as zero");
  assert.ok(!content(without).includes("spot · EUR/kWh"),
    "Expired or removed price has no stale implicit displayed tariff");
  multiPlan.price_slots=[];
  multiPlan.configuration.chargers=[];
  many.render();
  assert.ok(content(many.shadowRoot).includes("No charging points"),
    "0-Charger overview shows setup rather than inventing power lanes");

  assert.ok(content(card.shadowRoot).includes("Vehicle + Charger"),
    "Plan offers the user vehicle, charger or combined labels");
  assert.ok(content(card.shadowRoot).includes("Indicative forecasting"),
    "Indication is independently configurable");
  assert.ok(content(card.shadowRoot).includes("Measured power unavailable"));
  assert.ok(!content(card.shadowRoot).includes("3.6 kW actually charged"),
            "future proposal must never be presented as real charging");
  const selects=[];
  visit(card.shadowRoot,x=>{
    if(x.tag==="select")selects.push(x.attributes["aria-label"]);
  });
  assert.ok(selects.includes("Show labels"),"Label choice must be configurable");
  assert.ok(selects.includes("Color by"),"Color dimension must be configurable");
  assert.ok(selects.includes("Indicative forecasting"),
            "Forecast visibility is explicitly configurable");
  fixture.forecast_assumptions={
    drive:{asset_id:"car",charger_id:"drive",
           assumption:"IF_CONNECTED_NOW",assumed_connection_at:fixture.start}
  };
  fixture.forecast_slots=[{
    charger_id:"drive",asset_id:"car",
    start:"2026-11-22T13:00:00+01:00",
    end:"2026-11-22T13:15:00+01:00",
    indicative_power_kw:3.6,status:"indicative_only",
    may_execute:false,reserves_capacity:false
  }];
  const firm=fixture.slots;
  fixture.slots=[];
  fixture.observations.chargers.drive.connected={quality:"ok",value:false};
  card.render();
  assert.ok(content(card.shadowRoot).includes("Indicative · Disconnected"),
    "Disconnected asset is visible as explicitly hypothetical forecasting");
  assert.ok(content(card.shadowRoot).includes("Not reserved"),
    "Forecast must never imply a power reservation");
  const planHosts=[];
  visit(card.shadowRoot,node=>{if(node.attributes?.["data-chart-engine"])planHosts.push(node);});
  assert.equal(planHosts.length,2,"Combined and individual interval plots");
  for(const host of planHosts){
    const options=JSON.parse(host._mcSignature);
    assert.equal(options.xaxis.min,Date.parse(fixture.start));
    assert.equal(options.xaxis.max,Date.parse(fixture.end));
    const ix=options.series.findIndex(s=>s.name.includes("Indicative"));
    assert.ok(ix>=0);
    assert.equal(options.colors[ix],"#B05D81");
    const points=options.series[ix].data.filter(p=>p.y===3.6);
    assert.equal(points.length,2);
    assert.equal(points[1].x-points[0].x,899999,"Single quarter has real width");
  }
  assert.ok(!content(card.shadowRoot).includes("3.6 kW actually charged"),
    "Disconnection forecast must not become measured charging");
  // All graphs share backend-selected civil-day bounds, even if goal
  // horizons/deadlines differ. Verify cross-midnight, DST and charger color.
  const originalRange=[fixture.start,fixture.end], originalForecast=fixture.forecast_slots;
  const previousGoals=fixture.goal_assessments;
  const previousColor=fixture.configuration.controller.plan_color_by;
  for(const [start,end,slotStart,slotEnd] of [
    ["2026-11-22T00:00:00+01:00","2026-11-24T00:00:00+01:00",
     "2026-11-23T00:00:00+01:00","2026-11-23T00:15:00+01:00"],
    ["2026-10-25T00:00:00+02:00","2026-10-26T00:00:00+01:00",
     "2026-10-25T02:00:00+01:00","2026-10-25T02:15:00+01:00"],
    ["2026-03-29T00:00:00+01:00","2026-03-30T00:00:00+02:00",
     "2026-03-29T03:00:00+02:00","2026-03-29T03:15:00+02:00"]
  ]){
    fixture.start=start;fixture.end=end;
    fixture.configuration.controller.plan_color_by="charger";
    fixture.forecast_slots=[{charger_id:"drive",asset_id:"car",start:slotStart,end:slotEnd,
      indicative_power_kw:3.6,may_execute:false,reserves_capacity:false}];
    fixture.goal_assessments={drive:{asset_id:"car",status:"achievable",conditional:true,
      timeline_start:slotStart,timeline_end:slotEnd,deadline:slotEnd,
      timeline_windows:[{start:slotStart,end:slotEnd}]}};
    card.render();
    const ranges=[], bars=[];
    visit(card.shadowRoot,node=>{
      if(node.attributes?.["data-range-start"])ranges.push(node);
      if(String(node.className||"").startsWith("goal-window"))bars.push(node);
    });
    assert.equal(ranges.length,3,"Combined, lane and bar all share one range");
    assert.ok(ranges.every(node=>node.attributes["data-range-start"]===String(Date.parse(start))&&
      node.attributes["data-range-end"]===String(Date.parse(end))));
    assert.equal(bars.length,1);
    assert.equal(bars[0].style.background,"#32816E");
    const width=parseFloat(bars[0].style.width);
    assert.ok(Math.abs(width-100*900000/(Date.parse(end)-Date.parse(start)))<1e-8);
    for(const host of ranges.filter(n=>n._mcSignature)){
      const opts=JSON.parse(host._mcSignature);
      assert.equal(opts.colors[opts.series.findIndex(s=>s.name.includes("Indicative"))],"#32816E");
      assert.equal(opts.chart.zoom.enabled,false);
      assert.equal(opts.xaxis.tickAmount,4);
    }
  }
  [fixture.start,fixture.end]=originalRange;
  fixture.configuration.controller.plan_color_by=previousColor;
  fixture.goal_assessments=previousGoals;fixture.forecast_slots=originalForecast;
  fixture.slots=firm;
  fixture.forecast_slots=[];
  fixture.forecast_assumptions={};
  fixture.observations.chargers.drive.connected={quality:"ok",value:true};
  find(card.shadowRoot,"button","Tomorrow").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(commands.at(-1).day,"tomorrow");
  find(card.shadowRoot,"button","Chargeable Assets").click();
  assert.ok(content(card.shadowRoot).includes("Family car"));
  assert.ok(content(card.shadowRoot).includes("20%"));
  find(card.shadowRoot,"button","Details").click();
  assert.ok(content(card.shadowRoot).includes("Charging limit"),
    "Asset dashboard directly presents user 80% target");
  assert.ok(find(card.shadowRoot,"button","Schedule charging"),
    "Daily/weekly recurrence is on the Asset dashboard, not Options Flow");
  assert.ok(find(card.shadowRoot,"button","Set charging deadline"),
    "HA device-owned Ready By datetime is reachable directly from dashboard");
  find(card.shadowRoot,"button","Chargers").click();
  assert.ok(content(card.shadowRoot).includes("Driveway"));
  assert.ok(content(card.shadowRoot).includes("2.3 kW"));
  fixture.command_capabilities={drive:{
    pause_allowed:true,stop_allowed:true,paused:false
  }};
  card.render();
  const pause=find(card.shadowRoot,"button","Pause charging");
  assert.ok(pause,"native Charger offers real durable Pause action");
  pause.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(commands.some(c=>c.type==="robotix_multicharge/command"&&
    c.action==="pause"&&c.charger_id==="drive"));
  fixture.command_capabilities={drive:{
    resume_allowed:true,paused:true,start_allowed:false
  }};
  card.render();
  const resume=find(card.shadowRoot,"button","Resume charging");
  assert.ok(resume,"paused Charger exposes explicit Resume");
  resume.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(commands.some(c=>c.type==="robotix_multicharge/command"&&
    c.action==="resume"&&c.charger_id==="drive"));
  fixture.command_capabilities={};
  card.render();
  const addCharger=find(card.shadowRoot,"button","Add charger");
  assert.ok(addCharger,
    "Add Charger is configured entirely through this dashboard");
  find(card.shadowRoot,"button","Settings").click();
  card._settingsOpen="";card.render();
  for(const name of ["Charging site","Sources & bindings","Charging strategy",
                     "Safety & limits","Integrations"]){
    assert.ok(content(card.shadowRoot).includes(name),name);
  }

  assert.ok(find(card.shadowRoot,"button","Edit YAML"),
    "Admin Settings must expose complete YAML editor next to typed fields");
  assert.ok(!content(card.shadowRoot).includes("/config/packages/multicharge.yaml"),
    "No YAML package is required to configure standalone MultiCharge");
  card._settingsOpen="Sources & bindings";card.render();
  for(const label of ["Solar production","Home consumption","Grid power",
                      "Solar surplus","Future tariff intervals",
                      "Current import price","Current export price"]){
    assert.ok(content(card.shadowRoot).includes(label),
      "Settings must expose "+label+" as an HA-native source option");
  }
  card._settingsOpen="";card.render();
  const settingsGrids=[];
  visit(card.shadowRoot,x=>{if(x.className==="settings-grid")settingsGrids.push(x);});
  assert.equal(settingsGrids.length,1,
    "Settings use one compact responsive grid, not six full-width accordions");
  assert.ok(find(card.shadowRoot,"button","Details"),
            "Settings groups disclose details instead of an inert edit action");
  card.dispatchEvent=event=>{card._lastMoreInfo=event;return true;};
  card._settingsOpen="Charging site";card.render();
  assert.ok(content(card.shadowRoot).includes("Site name"));
  const siteEdit=find(card.shadowRoot,"button","Edit");
  assert.ok(siteEdit,"Site name exposes its native HA text editor");
  siteEdit.click();
  assert.equal(card._editingField,"controller:site:name",
    "Native entity shortcut expands the in-dashboard Controller field");
  card._settingsOpen="Safety & limits";card.render();
  assert.ok(content(card.shadowRoot).includes("Electrical limits"),
    "Safety Settings show the configured electrical limits");
  assert.ok(find(card.shadowRoot,"button","Apply"),
    "Site power limits are directly editable through Controller native Numbers");
  card._settingsOpen="Sources & bindings";card.render();
  assert.ok(content(card.shadowRoot).includes("Future tariff intervals"),
    "Source bindings disclose actual future tariff source selection");
  assert.ok(content(card.shadowRoot).includes("Home consumption"),
    "Home-wide power source remains a native selectable sensor");
  assert.ok(find(card.shadowRoot,"button","Edit"),
    "Every source binding is editable directly in dashboard");
  const nativeCalls=[];
  card._hass.callService=async(domain,action,args)=>{
    nativeCalls.push({domain,action,args});
    assert.equal(domain,"select");
    assert.equal(action,"select_option");
    if(args.entity_id==="select.site_mode"){
      assert.equal(args.option,"economy");
      fixture.configuration.controller.mode="Economy";
    } else if(args.entity_id==="select.car_color"){
      fixture.configuration.assets[0].plan_color=args.option;
    } else if(args.entity_id==="select.drive_color"){
      fixture.configuration.chargers[0].plan_color=args.option;
    } else if(args.entity_id==="select.drive_vehicle"){
      fixture.configuration.chargers[0].asset=
        args.option==="none"?undefined:"car";
    }
  };
  card._tab="Settings";card._settingsOpen="Charging strategy";card.render();
  const modeButton=find(card.shadowRoot,"button","Economy");
  assert.ok(modeButton,"charging mode available as an owning native HA select");
  modeButton.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(nativeCalls.some(c=>c.args.entity_id==="select.site_mode"&&
    c.args.option==="economy"),"native select owner receives strategy");
  card._tab="Chargeable Assets";card._open="";card.render();
  find(card.shadowRoot,"button","Details").click();
  assert.ok(find(card.shadowRoot,"select"),"vehicle offers a native color choice");
  assert.ok(find(card.shadowRoot,"button","Apply"),
    "Vehicle target and energy settings are controlled inline by native HA Numbers");
  assert.ok(find(card.shadowRoot,"button","Set charging deadline"),
    "Vehicle Ready By opens its native HA DateTime entity from the dashboard");
  let colorSelect;
  visit(card.shadowRoot,x=>{
    if(x.tag==="select"&&String(x.attributes.id||"").startsWith("multicharge-plan-color-"))colorSelect=x;
  });
  assert.ok(colorSelect,"vehicle plan color shown on Vehicle");
  colorSelect.value="blue";
  colorSelect.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(nativeCalls.some(c=>c.args.entity_id==="select.car_color"&&
    c.args.option==="blue"),"vehicle palette is changed through its own HA entity");
  card._tab="Chargers";card._open="";card.render();
  const quicks=[];
  visit(card.shadowRoot,node=>{
    if(node.tag==="select"&&node.attributes?.["data-quick-assignment"]==="drive")
      quicks.push(node);
  });
  assert.equal(quicks.length,1,
    "Charger chosen vehicle must be editable without opening Details");
  assert.equal(quicks[0].value,"Family car");
  quicks[0].value="none";quicks[0].events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(nativeCalls.some(x=>x.args.entity_id==="select.drive_vehicle"&&
    x.args.option==="none"),
    "Quick vehicle None selection must use real native HA Charger Select Entity");
  card._tab="Overview";card._open="";card.render();
  const overviewQuicks=[];
  visit(card.shadowRoot,node=>{
    if(node.tag==="select"&&node.attributes?.["data-quick-assignment"]==="drive")
      overviewQuicks.push(node);
  });
  assert.equal(overviewQuicks.length,0,
    "Overview no longer duplicates Charger-first assignment");
  assert.ok(find(card.shadowRoot,"button","Assign charger"),
    "Unassigned asset offers assignment directly on Overview");
  // Preserve the independent native Charger-side workflow.
  card._tab="Chargers";card._open="";card.render();
  const nativeQuick=[];
  visit(card.shadowRoot,node=>{
    if(node.tag==="select"&&node.attributes?.["data-quick-assignment"]==="drive")nativeQuick.push(node);
  });
  nativeQuick[0].value="Family car";nativeQuick[0].events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(fixture.configuration.chargers[0].asset,"car",
    "Native Charger selection persists in the canonical object");
  card._tab="Chargers";card._open="";card.render();
  find(card.shadowRoot,"button","Details").click();
  assert.ok(content(card.shadowRoot).includes("Plan color"));
  let chargerColor;
  visit(card.shadowRoot,x=>{
    if(x.tag==="select"&&String(x.attributes.id||"").startsWith("multicharge-plan-color-"))chargerColor=x;
    // The selected vehicle belongs to the native Charger device, not a copy.
  });
  assert.ok(chargerColor,"charger owns its configurable plan color");
  assert.ok(content(card.shadowRoot).includes("Selected vehicle"),
    "Charger shows its selected vehicle on its own detail view");
  chargerColor.value="pink";
  chargerColor.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(nativeCalls.some(c=>c.args.entity_id==="select.drive_color"&&
    c.args.option==="pink"),"charger color is a native owner setting");
  card._hass.language="nl";card.render();
  assert.ok(content(card.shadowRoot).includes("Laadpalen"),"Dutch card labels");
  card._hass.language="fr";card.render();
  assert.ok(content(card.shadowRoot).includes("Bornes"),"French card labels");
  for(const [lang,label] of [
    ["da","Ladere"],["nb","Ladere"],["sv","Laddare"],
    ["de","Ladepunkte"],["es","Puntos de carga"]
  ]){
    card._hass.language=lang;card.render();
    assert.ok(content(card.shadowRoot).includes(label),
      lang+" must translate the Charger view");
  }
  card._tab="Chargeable Assets";
  for(const [lang,power] of [
    ["de","Effektive Ladeleistung"],["es","Potencia efectiva de carga"]
  ]){
    card._hass.language=lang;card.render();
    assert.ok(content(card.shadowRoot).includes(power),
      lang+" must show the Asset-owned power sensor label");
  }
  card._tab="Chargers";
  card._hass.language="en";card.render();
  fixture.preference_entities.chargers.drive.confirm_connection="button.drive_confirm";
  fixture.connection_identity={drive:null};
  card.render();
  assert.ok(!find(card.shadowRoot,"button","Confirm connected vehicle"),
    "Normal resident surfaces must never require an extra confirmation");
  fixture.connection_identity={drive:{asset_id:"car",basis:"user_assignment"}};
  const statusEvse=fixture.configuration.chargers[0], statusVehicle=fixture.configuration.assets[0];
  const originalStates=fixture.charger_states;
  const originalPower=fixture.observations.chargers.drive.power_kw;
  const originalAssetPower=fixture.observations.assets.car.effective_power_kw;
  fixture.charger_states={drive:{activation:"active",charging_session:"charging",charging_state:"ready",operational_status:{status:"charging"},asset_operational_status:{status:"charging"}}};
  fixture.observations.chargers.drive.power_kw={quality:"ok",value:1.5};
  fixture.observations.assets.car.effective_power_kw={quality:"ok",value:1.5};
  assert.equal(card.operationalIndicator(statusEvse,statusVehicle).getAttribute("data-operational-status"),"charging");
  assert.equal(card.operationalIndicator(statusEvse).getAttribute("data-operational-status"),"charging");
  fixture.charger_states.drive.charging_state="error";
  fixture.charger_states.drive.operational_status=fixture.charger_states.drive.asset_operational_status={status:"problem",reason:"CHARGER_REPORTED_FAULT"};
  assert.equal(card.operationalIndicator(statusEvse).getAttribute("data-operational-status"),"problem");
  assert.equal(card.operationalIndicator(statusEvse,statusVehicle).getAttribute("data-operational-status"),"problem");
  fixture.charger_states.drive.charging_state="ready";
  fixture.charger_states.drive.charging_session="stopped";
  fixture.charger_states.drive.operational_status=fixture.charger_states.drive.asset_operational_status={status:"idle"};
  fixture.observations.chargers.drive.power_kw={quality:"ok",value:0};
  fixture.observations.assets.car.effective_power_kw={quality:"ok",value:0};
  assert.equal(card.operationalIndicator(statusEvse).getAttribute("data-operational-status"),"idle");
  assert.equal(card.operationalIndicator(statusEvse,statusVehicle).getAttribute("data-operational-status"),"idle");
  fixture.charger_states=originalStates;
  fixture.observations.chargers.drive.power_kw=originalPower;
  fixture.observations.assets.car.effective_power_kw=originalAssetPower;
  for(const tab of ["Overview","Chargeable Assets","Chargers"]){
    card._tab=tab;card.render();
    assert.ok(!find(card.shadowRoot,"button","Confirm connected vehicle"),
      "Ordinary assignment must not require repeated action on "+tab);
    assert.ok(!content(card.shadowRoot).includes("Use fixed assignment"));
  }
  fixture.connection_identity={drive:null};
  fixture.observations.chargers.drive.connected={quality:"ok",value:false};
  card._tab="Chargers";card.render();
  assert.ok(!find(card.shadowRoot,"button","Confirm connected vehicle"),
    "Disconnected charger must not ask for confirmation");
  fixture.observations.chargers.drive.connected={quality:"ok",value:true};
  card.render();
  assert.ok(!find(card.shadowRoot,"button","Start charging"),
            "uncommissioned hardware cannot gain optimistic action");
  fixture.command_capabilities={drive:{start_allowed:true,stop_allowed:true,reason:"READY"}};
  card._hass.callWS=async request=>{
    commands.push(request);
    if(request.type==="robotix_multicharge/command"){
      return {
        charger_id:request.charger_id,action:request.action,
        status:"confirmed",reason:"INDEPENDENT_POWER_READBACK",
        readback_at:new Date().toISOString(),measured_power_kw:request.action==="start"?1.6:0
      };
    }
    return fixture;
  };
  card._tab="Chargers";card._last=0;
  await card.load();
  assert.ok(find(card.shadowRoot,"button","Start charging"));
  find(card.shadowRoot,"button","Start charging").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(commands.some(c=>c.type==="robotix_multicharge/command"&&c.action==="start"),
            "Start button must invoke real native WS command API");
  assert.ok(content(card.shadowRoot).includes("Charging"),
            "display only a returned physical confirmation");
  assert.ok(find(card.shadowRoot,"button","Stop charging"),
            "physically admitted Stop action is present");
  find(card.shadowRoot,"button","Stop charging").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(commands.some(c=>c.type==="robotix_multicharge/command"&&c.action==="stop"),
            "Stop button must invoke real native WS command API");
  console.log("MultiCharge source-only five-view and native-command wiring PASS (not HA browser acceptance)");
}
main().catch(error=>{console.error(error);process.exitCode=1;});
