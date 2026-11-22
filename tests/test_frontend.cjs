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
    controller:{mode:"select.site_mode",plan_label_mode:"select.site_labels",
                plan_color_by:"select.site_colors",
                show_indicative_forecast:"select.site_forecast"},
    assets:{car:{plan_color:"select.car_color",target_soc:"number.car_target",
                 ready_by:"datetime.car_ready_by",priority:"number.car_priority"}},
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
  find(card.shadowRoot,"button","Chargers").click();
  assert.ok(content(card.shadowRoot).includes("Driveway"));
  assert.ok(content(card.shadowRoot).includes("2.3 kW"));
  find(card.shadowRoot,"button","Settings").click();
  for(const name of ["Charging site","Sources & bindings","Charging strategy",
                     "Safety & limits","Integrations","Advanced & YAML"]){
    assert.ok(content(card.shadowRoot).includes(name),name);
  }
  assert.ok(find(card.shadowRoot,"a"),"setting opens real HA integration settings");
  assert.ok(find(card.shadowRoot,"button","Edit"),
            "Site controls use native HA Number entities");
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
  card._tab="Chargeable Assets";card.render();
  find(card.shadowRoot,"button","Details").click();
  assert.ok(find(card.shadowRoot,"select"),"vehicle offers a native color choice");
  assert.ok(find(card.shadowRoot,"button","Edit"),"native vehicle settings open standard HA entity");
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
