/* Source-only browser-like interaction contract. Never claimed as a real HA render. */
"use strict";
const assert=require("node:assert/strict");
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.events={};this.style={};this.textContent="";this.value="";}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=[...items];}
  setAttribute(k,v){this.attributes[k]=v;}
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
  const assignCard=new Card();
  assignCard.setConfig({});
  assignCard.hass={
    user:{is_admin:true},states:{},
    callWS:async request=>{
      assignmentWS.push(request);
      return request.type==="robotix_multicharge/update_settings"?
        {status:"accepted_unconfirmed",expected_revision:"revision-b"}:assignData;
    }
  };
  await new Promise(resolve=>setImmediate(resolve));
  find(assignCard.shadowRoot,"button","Chargeable Assets").click();
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
    x.target_id==="drive"&&Object.hasOwn(x.changes,"asset")&&
    x.changes.asset===null
  ),"Unassign clears the authoritative Charger.asset instead of deleting Asset");
  assert.equal(assignmentWS.filter(x=>x.type==="robotix_multicharge/command").length,0,
    "Move/unassign never sends hidden physical STOP or START");
  const readonlyAssign=new Card();
  readonlyAssign.setConfig({});
  readonlyAssign.hass={
    user:{is_admin:false},states:{},callWS:async()=>assignData
  };
  await new Promise(resolve=>setImmediate(resolve));
  find(readonlyAssign.shadowRoot,"button","Chargeable Assets").click();
  assert.equal(find(readonlyAssign.shadowRoot,"button","Change charger"),undefined,
    "Resident may view assignment but may not edit Charger-owned relation");

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
  assert.ok(content(yamlCard.shadowRoot).includes("YAML · read-only"),
    "YAML-managed settings clearly disclose their authority");
  assert.ok(!find(yamlCard.shadowRoot,"button","Edit"),
    "YAML-managed configuration must not advertise writable settings");
  assert.ok(!find(yamlCard.shadowRoot,"button","Edit YAML"),
    "External YAML source cannot be overwritten from a second UI editor");
  assert.ok(!find(resident.shadowRoot,"button","Edit YAML"),
    "Non-admin must never access native configuration transaction");

  // A real admin begins exactly one official HA Options Flow. The frontend
  // holds a draft only, and sends all validation/review/save to HA.
  const yamlApis=[];
  let yamlApplied=false;
  const initialYaml="controller:\n  id: site\n  name: Sample\n  mode: Off\n  max_parallel: 2\nassets: []\nchargers: []\n";
  const editorCard=new Card();
  editorCard.setConfig({});
  editorCard.hass={user:{is_admin:true},states:{},
    callWS:async()=>fixture,
    callApi:async(method,path,body)=>{
      yamlApis.push({method,path,body});
      if(method==="GET"&&path==="config/config_entries/entry")
        return [{domain:"robotix_multicharge",entry_id:"entry-1"}];
      if(method==="POST"&&path==="config/config_entries/options/flow")
        return {type:"menu",flow_id:"flow-1",step_id:"init"};
      if(method==="DELETE")
        return {};
      assert.equal(path,"config/config_entries/options/flow/flow-1");
      if(body.next_step_id==="yaml")return {type:"form",flow_id:"flow-1",
        step_id:"yaml",data_schema:[
          {name:"yaml_text",default:initialYaml},
          {name:"mode",default:"replace"}
        ]};
      if(body.edit_again)return {type:"form",flow_id:"flow-1",
        step_id:"yaml",data_schema:[]};
      if(body.yaml_text){
        if(body.yaml_text.includes("INVALID"))
          return {type:"form",flow_id:"flow-1",step_id:"yaml",
            errors:{base:"invalid_config"},
            description_placeholders:{note:"Validation: duplicate YAML key"}};
        return {type:"form",flow_id:"flow-1",step_id:"yaml_review",
          description_placeholders:{summary:"Chargers: Add outside\nWriter unchanged"},
          data_schema:[]};
      }
      if(body.confirm){
        yamlApplied=true;
        return {type:"create_entry",title:"",data:{}};
      }
      throw Error("Unsupported Options Flow action");
    }};
  await new Promise(resolve=>setImmediate(resolve));
  editorCard._tab="Settings";editorCard.render();
  assert.ok(find(editorCard.shadowRoot,"button","Edit YAML"),
    "GUI-managed site exposes first-class YAML mode in Settings");
  find(editorCard.shadowRoot,"button","Edit YAML").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(editorCard._yamlFlow?.step_id,"yaml");
  const textarea=find(editorCard.shadowRoot,"textarea");
  assert.ok(textarea&&textarea.value===initialYaml,
    "Editor uses backend-returned native Config Entry, not a local template");
  textarea.value=initialYaml+"# preview only\n";
  textarea.events.input();
  assert.ok(!yamlApplied,"Changing YAML text cannot save by itself");
  find(editorCard.shadowRoot,"button","Continue / review").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(editorCard._yamlFlow.step_id,"yaml_review");
  assert.ok(content(editorCard.shadowRoot).includes("Writer unchanged"),
    "Actual backend review diff is shown verbatim before Save");
  assert.ok(!yamlApplied,"Review must not save or send any physical command");
  find(editorCard.shadowRoot,"button","Back to YAML").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(editorCard._yamlFlow.step_id,"yaml");
  editorCard._yamlText="INVALID";
  editorCard.render();
  find(editorCard.shadowRoot,"button","Continue / review").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(editorCard._yamlFlow.step_id,"yaml");
  assert.ok(content(editorCard.shadowRoot).includes("YAML rejected"),
    "Backend YAML validation failure must remain visible without saving");
  assert.ok(content(editorCard.shadowRoot).includes("duplicate YAML key"),
    "Show actionable server validation, not only a generic failure");
  editorCard._yamlText=initialYaml;
  editorCard.render();
  find(editorCard.shadowRoot,"button","Continue / review").click();
  await new Promise(resolve=>setImmediate(resolve));
  find(editorCard.shadowRoot,"button","Apply reviewed changes").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(yamlApplied);
  assert.equal(editorCard._yamlFlow,null);
  assert.ok(yamlApis.some(call=>call.body?.next_step_id==="yaml"));
  assert.ok(yamlApis.some(call=>call.body?.confirm===true));
  assert.ok(!yamlApis.some(call=>call.method==="POST"&&
    call.path==="config/config_entries/options/flow/flow-1"&&
    call.body?.action==="start"),
    "Config review/save never sends physical actuation");
  find(editorCard.shadowRoot,"button","Edit YAML").click();
  await new Promise(resolve=>setImmediate(resolve));
  find(editorCard.shadowRoot,"button","Cancel YAML").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(yamlApis.some(call=>call.method==="DELETE"),
    "Cancel deletes the server-side draft flow");
  assert.equal(editorCard._yamlFlow,null);

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
  assert.ok(find(emptyCard.shadowRoot,"a","Configure in Home Assistant"),
    "Empty charging plan offers the existing native configuration path");
  assert.ok(!find(emptyCard.shadowRoot,"svg"),
    "Empty charging plan does not render a fictitious plot");
  assert.ok(!content(emptyCard.shadowRoot).includes("Measured power unavailable"),
    "Empty charging plan does not claim a missing measurement incident");
  emptyCard._tab="Overview";emptyCard.render();
  assert.ok(content(emptyCard.shadowRoot).includes("Configure a charger to begin"),
    "Empty overview states the necessary next action");
  assert.ok(find(emptyCard.shadowRoot,"a","Configure in Home Assistant"),
    "Empty overview offers native setup action, not a passive hint");
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
  assert.ok(find(card.shadowRoot,"svg"),"actual quarter timeline chart mounted");
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
  assert.ok(!content(card.shadowRoot).includes("3.6 kW actually charged"),
    "Disconnection forecast must not become measured charging");
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
  assert.ok(content(card.shadowRoot).includes("Charging schedule"),
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
  const addCharger=find(card.shadowRoot,"a","Add charger");
  assert.ok(addCharger&&addCharger.href==="/config/integrations/integration/robotix_multicharge",
    "Add Charger routes to the one native HA setup");
  find(card.shadowRoot,"button","Settings").click();
  card._settingsOpen="";card.render();
  for(const name of ["Charging site","Sources & bindings","Charging strategy",
                     "Safety & limits","Integrations","Advanced & YAML"]){
    assert.ok(content(card.shadowRoot).includes(name),name);
  }
  assert.ok(find(card.shadowRoot,"a"),"Settings open real HA integration configuration");
  assert.ok(content(card.shadowRoot).includes("Expert YAML / JSON configuration"),
    "Settings summary exposes real expert configuration instead of a fake editor");
  card._settingsOpen="Advanced & YAML";card.render();
  assert.ok(content(card.shadowRoot).includes("Home Assistant Energy Dashboard sources may be reused"),
    "GUI config reuses HA Energy and standalone sources");
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
  assert.equal(card._lastMoreInfo?.detail?.entityId,"text.site_name");
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
  assert.ok(find(card.shadowRoot,"a"),
    "Advanced source mappings open the existing HA configuration");
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
    if(x.tag==="select"&&x.attributes.id==="multicharge-plan-color")colorSelect=x;
  });
  assert.ok(colorSelect,"vehicle plan color shown on Vehicle");
  colorSelect.value="blue";
  colorSelect.events.change();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(nativeCalls.some(c=>c.args.entity_id==="select.car_color"&&
    c.args.option==="blue"),"vehicle palette is changed through its own HA entity");
  card._tab="Chargers";card._open="";card.render();
  find(card.shadowRoot,"button","Details").click();
  assert.ok(content(card.shadowRoot).includes("Plan color"));
  let chargerColor;
  visit(card.shadowRoot,x=>{
    if(x.tag==="select"&&x.attributes.id==="multicharge-plan-color")chargerColor=x;
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
  const pressed=[];
  card._hass.callService=async(domain,action,args)=>{
    pressed.push({domain,action,args});
    if(domain!=="button"||action!=="press")
      throw new Error("Only actual native confirm button allowed");
    fixture.connection_identity={
      drive:{asset_id:"car",confirmed_at:new Date().toISOString()}
    };
  };
  card.render();
  assert.ok(find(card.shadowRoot,"button","Confirm connected vehicle"),
    "Connected unidentified asset must expose a real HA-native confirmation");
  find(card.shadowRoot,"button","Confirm connected vehicle").click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(pressed.some(c=>c.args.entity_id==="button.drive_confirm"),
    "Confirmation invokes the owning native HA button, never frontend identity inference");

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
