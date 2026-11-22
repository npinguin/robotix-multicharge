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
  createElement:(tag)=>new Element(tag),
  createElementNS:(_ns,tag)=>new Element(tag),
  createTextNode:(text)=>{const n=new Element("#text");n.textContent=text;return n;}
};
require("../custom_components/robotix_multicharge/frontend/robotix-multicharge.js");
const Card=customElements.get("robotix-multicharge-card");
assert.ok(Card,"native custom card registered");
assert.equal(window.customCards.filter(c=>c.type==="robotix-multicharge-card").length,1);
const fixture={
  controller_id:"site",timezone:"Europe/Brussels",start:"2026-11-22T00:00:00+01:00",
  end:"2026-11-23T00:00:00+01:00",status:"proposed",
  configuration:{
    controller:{id:"site",name:"Sample",mode:"Ready By",max_parallel:2,max_power_kw:7},
    assets:[{id:"car",name:"Family car",kind:"car",target_soc:80,
             ready_by:"2026-11-22T18:00:00+01:00"}],
    chargers:[{id:"drive",name:"Driveway",kind:"on_off",rated_power_kw:3.6,
               asset:"car",phase_count:1}]
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
  card.hass={callWS:async request=>{commands.push(request);return fixture;}};
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(commands.length>0);
  assert.equal(commands[0].type,"robotix_multicharge/get_plan");
  assert.ok(content(card.shadowRoot).includes("Family car"));
  assert.ok(content(card.shadowRoot).includes("2.30 kW"));
  find(card.shadowRoot,"button","Charging Plan").click();
  assert.ok(find(card.shadowRoot,"svg"),"actual quarter timeline chart mounted");
  assert.ok(content(card.shadowRoot).includes("Measured interval history is unavailable"));
  assert.ok(!content(card.shadowRoot).includes("3.6 kW actually charged"),
            "future proposal must never be presented as real charging");
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
  assert.ok(!find(card.shadowRoot,"button","Start charging"),
            "uncommissioned hardware cannot gain optimistic action");
  console.log("MultiCharge source-only five-view interactions PASS (not HA browser acceptance)");
}
main().catch(error=>{console.error(error);process.exitCode=1;});
