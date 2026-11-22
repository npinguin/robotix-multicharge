/* Robotix MultiCharge native Home Assistant card: one backend, five honest views. */
const MC_TABS = ["Overview", "Charging Plan", "Chargeable Assets", "Chargers", "Settings"];
const MC_SETTINGS = ["Charging site", "Sources & bindings", "Charging strategy", "Safety & limits", "Integrations", "Advanced & YAML"];
const MC_MODES = ["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"];
const MC_STYLE = [
  ":host{display:block;color:var(--primary-text-color,#20252b);font:inherit}",
  ".root{background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:16px;padding:16px;box-shadow:var(--ha-card-box-shadow,0 2px 8px #0002)}",
  ".heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}",
  "h2{font-size:20px;line-height:1.4;margin:0 0 8px}h3{font-size:16px;margin:0}p{margin:5px 0;line-height:1.5}",
  ".muted{color:var(--secondary-text-color,#65717e)}.small{font-size:12px}.value{font-weight:700;font-size:22px}",
  ".tabs,.controls,.chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}",
  "input,button,select,textarea,a.action{font:inherit;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:10px;padding:9px 11px;cursor:pointer;text-decoration:none;min-height:42px}",
  "button[aria-selected=true],button.active{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);border-color:var(--primary-color,#1976d2)}",
  "button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#1976d2);outline-offset:2px}",
  ".grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}",
  ".card{border:1px solid var(--divider-color,#e1e4e8);border-radius:12px;padding:13px;min-width:0;margin:8px 0}",
  ".metric{background:var(--secondary-background-color,#f6f8fa);border-radius:12px;padding:12px;min-width:0}",
  ".row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}",
  ".details{margin-top:10px;padding-top:9px;border-top:1px solid var(--divider-color,#ddd)}",
  ".pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:5px 0}",
  ".field{display:flex;flex-direction:column;gap:4px;margin:8px 0}.field label{font-size:13px;color:var(--secondary-text-color,#65717e)}",
  ".field input,.field select{width:100%;box-sizing:border-box;padding:10px;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px}",
  ".message{font-size:13px;margin:9px 0}.pending{color:var(--warning-color,#b57418)}.confirmed{color:var(--success-color,#278355)}",
  ".notice{border-left:3px solid var(--warning-color,#e59e31);padding:9px 12px;background:var(--secondary-background-color,#f6f8fa);margin:12px 0;font-size:13px}",
  ".error{border-left-color:var(--error-color,#d43b38)}.chart{overflow-x:auto;width:100%}",
  ".legend{display:flex;flex-wrap:wrap;gap:15px;font-size:12px;color:var(--secondary-text-color,#65717e)}",
  ".dot{display:inline-block;width:11px;height:11px;margin-right:5px;border-radius:2px}",
  "svg{width:100%;min-width:440px;height:220px}svg text{fill:var(--secondary-text-color,#65717e);font-size:11px}",
  "@media(max-width:600px){.root{padding:12px}.grid{grid-template-columns:1fr}.tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.tabs button{font-size:12px;padding:8px 5px}}"
].join("");

function mcEl(tag, css, text) {
  const node = document.createElement(tag);
  if (css) node.className = css;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function mcButton(text, action, css) {
  const node = mcEl("button", css || "", text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function mcValue(observation, suffix) {
  if (!observation || observation.quality !== "ok" || observation.value === null || observation.value === undefined) return "Unknown";
  if (typeof observation.value === "boolean") return observation.value ? "Connected" : "Disconnected";
  return String(observation.value) + (suffix || "");
}
function mcTime(value, zone) {
  if (!value) return "Not set";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString(undefined, {timeZone: zone || "UTC", month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function mcPair(target, left, right) {
  const pair=mcEl("div","pair");
  pair.append(mcEl("span","muted",left),mcEl("span","",right));
  target.append(pair);
}
function mcSVG(tag, attrs, text) {
  const node=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for (const [name,value] of Object.entries(attrs||{})) node.setAttribute(name,String(value));
  if(text!==undefined)node.textContent=String(text);
  return node;
}

class RobotixMultiChargeCard extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    this._tab="Overview";
    this._day="today";
    this._filter="";
    this._open="";
    this._settingsOpen="Charging site";
    this._data=null;
    this._error="";
    this._last=0;
    this._loading=false;
    this._commandBusy=false;
    this._commandFeedback={};
    this._settingsBusy=false;
    this._settingsFeedback=null;
    this._pendingSettings=null;
    this._assetEditor="";
  }
  setConfig(config){this._cardConfig=config||{};this.render();}
  getCardSize(){return 10;}
  set hass(value){
    this._hass=value;
    if(!this._loading&&(!this._last||Date.now()-this._last>60000)) this.load();
    else if(this._data) this.render();
  }
  async load(){
    if(!this._hass||this._loading)return;
    this._loading=true;this._error="";this.render();
    try {
      const cmd={type:"robotix_multicharge/get_plan",day:this._day};
      if(this._filter.startsWith("charger:"))cmd.charger_id=this._filter.slice(8);
      if(this._filter.startsWith("asset:"))cmd.asset_id=this._filter.slice(6);
      this._data=await this._hass.callWS(cmd);
      if(this._pendingSettings&&
         this._data.configuration_revision===this._pendingSettings.expected_revision){
        this._settingsFeedback={status:"confirmed",message:"Settings confirmed after Home Assistant readback."};
        this._pendingSettings=null;
      }
      this._last=Date.now();
    }catch(error){
      this._error=error && (error.message||error.code) ? String(error.message||error.code) : "Read access unavailable";
      this._data=null;
      this._last=Date.now();
    }finally{this._loading=false;this.render();}
  }
  async command(charger,action){
    if(this._commandBusy||!this._hass)return;
    this._commandBusy=true;
    this._commandFeedback[charger]={status:"requested",reason:"Submitting physical command…"};
    this.render();
    try {
      const request={type:"robotix_multicharge/command",
                     charger_id:charger,action};
      if(typeof crypto!=="undefined"&&typeof crypto.randomUUID==="function")
        request.request_id=crypto.randomUUID();
      const outcome=await this._hass.callWS(request);
      this._commandFeedback[charger]=outcome;
      if(outcome.status==="confirmed"){
        this._last=0;
        await this.load();
      }
    }catch(error){
      this._commandFeedback[charger]={
        status:"rejected",
        reason:"COMMAND_REQUEST_FAILED: "+String(error.message||error)
      };
    }finally{this._commandBusy=false;this.render();}
  }
  async saveSettings(scope,targetId,changes,action){
    if(this._settingsBusy||!this._hass||!this._data)return;
    if(!this._data.configuration_revision){
      this._settingsFeedback={status:"rejected",message:"Settings revision unavailable. Refresh first."};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Validating settings…"};
    this.render();
    try{
      const receipt=await this._hass.callWS({
        type:"robotix_multicharge/update_settings",
        scope,target_id:targetId,changes,action:action||"save",
        expected_revision:this._data.configuration_revision
      });
      if(receipt.status!=="accepted_unconfirmed"||!receipt.expected_revision)
        throw new Error("Settings change was not admitted");
      this._pendingSettings={expected_revision:receipt.expected_revision};
      this._settingsFeedback={status:"accepted_unconfirmed",message:"Saved to Home Assistant; checking the reloaded configuration…"};
      this._last=0;
    }catch(error){
      this._settingsFeedback={status:"rejected",message:String(error.message||error)};
    }finally{
      this._settingsBusy=false;
      if(this._pendingSettings)await this.load();
      this.render();
    }
  }
  field(container,title,value,type,choices){
    const wrapper=mcEl("div","field"),label=mcEl("label","",title);
    const input=mcEl(choices?"select":"input");
    const id="multicharge-"+title.toLowerCase().replace(/[^a-z0-9]+/g,"-");
    input.setAttribute("id",id);label.setAttribute("for",id);
    if(choices){
      for(const [key,caption] of choices){
        const opt=mcEl("option","",caption);opt.value=key;
        if(key===String(value===null||value===undefined?"":value))opt.selected=true;
        input.append(opt);
      }
    }else{
      input.setAttribute("type",type||"text");
    }
    input.value=value===undefined||value===null?"":String(value);
    wrapper.append(label,input);container.append(wrapper);
    return input;
  }
  feedback(container){
    if(!this._settingsFeedback)return;
    const result=this._settingsFeedback;
    const node=mcEl("p","message "+(result.status==="confirmed"?"confirmed":result.status==="rejected"?"error":"pending"),result.message);
    node.setAttribute("role",result.status==="rejected"?"alert":"status");
    container.append(node);
  }
  title(container,label){
    container.append(mcEl("h2","",label));
  }
  notice(container,message,bad){
    container.append(mcEl("div","notice"+(bad?" error":""),message));
  }
  configure(container){
    const link=mcEl("a","action","Open Home Assistant integration settings");
    link.href="/config/integrations/integration/robotix_multicharge";
    link.setAttribute("aria-label","Open MultiCharge native configuration and options");
    container.append(link);
  }
  render(){
    if(!this.shadowRoot)return;
    const root=this.shadowRoot;root.replaceChildren();
    const style=mcEl("style");style.textContent=MC_STYLE;root.append(style);
    const shell=mcEl("section","root");
    const head=mcEl("div","heading");const heading=mcEl("div");
    heading.append(mcEl("h2","","MultiCharge"),mcEl("p","muted small","Charging plan & observed sources"));
    head.append(heading,mcButton("Refresh",()=>{this._last=0;this.load();}));
    shell.append(head);
    const tabs=mcEl("nav","tabs");tabs.setAttribute("aria-label","MultiCharge views");
    for(const item of MC_TABS){
      const btn=mcButton(item,()=>{this._tab=item;this.render();});
      btn.setAttribute("aria-selected",String(this._tab===item));
      tabs.append(btn);
    }
    shell.append(tabs);
    if(this._loading&&!this._data)this.notice(shell,"Loading actual Home Assistant observations…",false);
    if(this._error){
      this.notice(shell,"Cannot load current charging data: "+this._error+". An administrator must have a configured MultiCharge integration.",true);
      this.configure(shell);
    }else if(!this._data&&!this._loading){
      this.notice(shell,"No charging controller is configured or currently available.",true);
      this.configure(shell);
    }else if(this._data){
      if(this._tab==="Overview")this.overview(shell);
      if(this._tab==="Charging Plan")this.plan(shell);
      if(this._tab==="Chargeable Assets")this.assets(shell);
      if(this._tab==="Chargers")this.chargers(shell);
      if(this._tab==="Settings")this.settings(shell);
      this.notice(shell,"Automatic slot execution and variable current require an exclusively owned, separately commissioned charger with qualified electrical limits and independent measured readback. Unqualified controls remain unavailable.",false);
    }
    root.append(shell);
  }
  overview(container){
    const d=this._data,c=d.configuration||{},assets=c.assets||[],chargers=c.chargers||[];
    this.title(container,"Charging overview");
    const observations=(d.observations||{}).chargers||{};
    const priced=((d.observations||{}).sources||{}).current_price||{};
    const priceLabel=priced.quality==="ok"&&typeof priced.value==="number"&&priced.currency
      ?new Intl.NumberFormat(undefined,{style:"currency",currency:priced.currency,maximumFractionDigits:4}).format(priced.value)+"/kWh"
      :"Unavailable";
    const powers=chargers.map(x=>(observations[x.id]||{}).power_kw);
    const complete=powers.length>0&&powers.every(x=>x&&x.quality==="ok"&&typeof x.value==="number");
    const active=powers.filter(x=>x&&x.quality==="ok"&&x.value>0).length;
    const metrics=mcEl("div","grid");
    for(const [key,value] of [
      ["Active chargers",complete?String(active):"Unknown"],
      ["Actual power",complete?(powers.reduce((sum,x)=>sum+x.value,0).toFixed(2)+" kW"):"Unknown"],
      ["Current price",priceLabel]
    ]){const el=mcEl("div","metric");el.append(mcEl("p","muted small",key),mcEl("div","value",value));metrics.append(el);}
    container.append(metrics);
    const mode=(c.controller||{}).mode||"Off";
    const chips=mcEl("div","chips");chips.append(mcEl("p","muted","Charging strategy: "+mode));
    for(const item of MC_MODES){
      const button=mcButton(item,()=>this.saveSettings("controller",(c.controller||{}).id,{mode:item}));
      button.disabled=this._settingsBusy||item===mode;
      button.title="Mode changes require administrator access and physical idle safety.";
      if(item===mode)button.className="active";
      chips.append(button);
    }
    container.append(chips);
    this.feedback(container);
    for(const a of assets){
      const card=mcEl("div","card");const observed=((d.observations||{}).assets||{})[a.id]||{};
      const charger=chargers.find(x=>x.asset===a.id);
      card.append(mcEl("h3","",a.name),mcEl("p","muted",mcValue(observed.soc,"%")+" battery · Target "+(a.target_soc===undefined?"not set":a.target_soc+"%")));
      card.append(mcEl("p","small","Ready by "+mcTime(a.ready_by,d.timezone)+" · "+(charger?charger.name:"No charger assigned")));
      container.append(card);
    }
    if(!assets.length)this.notice(container,"No assets configured. Add one through Settings.",false);
    const next=mcEl("div","card");next.append(mcEl("h3","","Next action"));
    next.append(mcEl("p","",d.status==="unavailable"?"Review missing inputs and source quality.":"Review the proposed plan before enabling any real equipment."));
    const reasons=Object.entries(d.reasons||{}).filter(([key,val])=>val!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",reasons.map(([key,val])=>key+": "+val).slice(0,4).join(" · ")));
    container.append(next);
  }
  settingsSelect(_container,name){this._tab="Settings";this._settingsOpen=name;this.render();}
  plan(container){
    const d=this._data;
    this.title(container,"Charging plan");
    const controls=mcEl("div","controls");
    for(const day of ["today","tomorrow"]) {
      const btn=mcButton(day==="today"?"Today":"Tomorrow",()=>{this._day=day;this._last=0;this.load();},this._day===day?"active":"");
      controls.append(btn);
    }
    const selector=mcEl("select");
    selector.setAttribute("aria-label","Filter by charger or chargeable asset");
    const options=[["","All chargers"]];
    for(const item of d.configuration.chargers||[])options.push(["charger:"+item.id,item.name]);
    for(const item of d.configuration.assets||[])options.push(["asset:"+item.id,item.name+" (asset)"]);
    for(const [value,title] of options){const option=mcEl("option","",title);option.value=value;option.selected=value===this._filter;selector.append(option);}
    selector.addEventListener("change",()=>{this._filter=selector.value;this._last=0;this.load();});
    controls.append(selector);
    container.append(controls);
    const chart=mcEl("div","chart");
    const svg=mcSVG("svg",{viewBox:"0 0 900 220",role:"img","aria-label":"15-minute proposed and measured power. Missing measured slots are unknown."});
    const raw=d.slots||[];
    const start=new Date(d.start).getTime(),end=new Date(d.end).getTime();
    const count=Math.max(1,Math.ceil((end-start)/900000));
    const max=Math.max(0.2,...raw.map(s=>s.proposed_power_kw||0),
      ...raw.map(s=>s.accepted_power_kw||0),
      ...(d.actual_slots||[]).map(s=>s.actual_power_kw||0));
    svg.append(mcSVG("line",{x1:37,y1:174,x2:892,y2:174,stroke:"currentColor","stroke-opacity":0.35}));
    for(const slot of raw){
      const index=Math.floor((new Date(slot.start).getTime()-start)/900000);
      if(index<0||index>=count)continue;
      const w=850/count;const x=40+index*w;
      if(typeof slot.proposed_power_kw==="number"){
        const h=Math.max(0,slot.proposed_power_kw/max*150);
        const rect=mcSVG("rect",{x,y:174-h,width:Math.max(1,w-1),height:h,fill:"#4284d3"});
        rect.append(mcSVG("title",{},"Proposed "+slot.proposed_power_kw+" kW · "+mcTime(slot.start,d.timezone)));
        svg.append(rect);
      }
      if(typeof slot.accepted_power_kw==="number"){
        const h=Math.max(0,slot.accepted_power_kw/max*150);
        const accepted=mcSVG("rect",{x:x+w*0.38,y:174-h,width:Math.max(1,w*0.28),height:h,fill:"#8d61b5"});
        accepted.append(mcSVG("title",{},"Physically accepted "+slot.accepted_power_kw+" kW · "+mcTime(slot.start,d.timezone)));
        svg.append(accepted);
      }
    }
    const priceSlots=(d.price_slots||[]).filter(s=>typeof s.price_per_kwh==="number");
    if(priceSlots.length){
      const vmin=Math.min(...priceSlots.map(s=>s.price_per_kwh));
      const vmax=Math.max(...priceSlots.map(s=>s.price_per_kwh));
      const range=vmax-vmin||1;
      let path="",started=false;
      for(let i=0;i<count;i++){
        const t=start+i*900000;
        const eligible=priceSlots.filter(s=>new Date(s.start).getTime()<=t&&new Date(s.end).getTime()>=t+900000);
        if(eligible.length!==1){started=false;continue;}
        const x=40+(i+0.5)*850/count;
        const y=170-(eligible[0].price_per_kwh-vmin)/range*145;
        path+=(started?" L":" M")+x.toFixed(2)+" "+y.toFixed(2);
        started=true;
      }
      if(path)svg.append(mcSVG("path",{d:path,fill:"none",stroke:"#d89a22","stroke-width":2}));
    }
    for(let i=0;i<=4;i++){
      const t=new Date(start+(end-start)*i/4);
      svg.append(mcSVG("text",{x:40+i*212,y:195},t.toLocaleTimeString(undefined,{timeZone:d.timezone||"UTC",hour:"2-digit",minute:"2-digit"})));
    }
    svg.append(mcSVG("text",{x:40,y:15}, "Power (kW) · proposed / physically accepted / measured"));
    chart.append(svg);container.append(chart);
    const legend=mcEl("div","legend");
    for(const [color,text] of [["#4284d3","Proposed"],["#8d61b5","Accepted (physical)"],["#2d9c70","Measured"],["#d89a22","Qualified price"]]){
      const item=mcEl("span");const dot=mcEl("span","dot");dot.style.background=color;item.append(dot,document.createTextNode(text));legend.append(item);
    }
    container.append(legend);
    const actual=(d.actual_slots||[]);
    const expected=this._filter ? 1 : (d.configuration.chargers||[]).length;
    const buckets=new Map();
    for(const sample of actual){
      const rows=buckets.get(sample.start)||[];
      rows.push(sample);
      buckets.set(sample.start,rows);
    }
    let qualifiedActual=0;
    for(const [timestamp,rows] of buckets){
      if(!expected||rows.length!==expected||
         !rows.every(item=>typeof item.actual_power_kw==="number"))continue;
      const index=Math.floor((new Date(timestamp).getTime()-start)/900000);
      if(index<0||index>=count)continue;
      const kw=rows.reduce((total,row)=>total+row.actual_power_kw,0);
      const h=Math.max(0,kw/max*150);
      const w=850/count;
      const rect=mcSVG("rect",{
        x:40+index*w+w*0.55,y:174-h,
        width:Math.max(1,w*0.35),height:h,fill:"#2d9c70"
      });
      rect.append(mcSVG("title",{},"Measured "+kw.toFixed(2)+" kW · "+mcTime(timestamp,d.timezone)));
      svg.append(rect);
      qualifiedActual++;
    }
    if(!qualifiedActual)this.notice(container,
      "Measured interval history unavailable: "+
      (d.actual_history_quality||"RECORDER_OR_SOURCE_UNQUALIFIED")+
      ". No actual charging or cost is inferred from proposals.",false);
    const next=mcEl("div","card");next.append(mcEl("h3","","Next planned session"));
    const first=raw.find(x=>x.proposed_power_kw>0);
    next.append(mcEl("p","",first?mcTime(first.start,d.timezone)+" · "+first.proposed_power_kw+" kW":"No qualified charging slot"));
    next.append(mcEl("p","muted small","Reason: "+Object.entries(d.reasons||{}).map(([k,v])=>k+" "+v).slice(0,4).join("; ")));
    container.append(next);
  }
  assets(container){
    const d=this._data,assets=d.configuration.assets||[],chargers=d.configuration.chargers||[];
    this.title(container,"Chargeable assets ("+assets.length+")");
    if(!assets.length)this.notice(container,"No chargeable assets configured.",false);
    for(const a of assets){
      const card=mcEl("div","card");const charger=chargers.find(x=>x.asset===a.id);
      const obs=((d.observations||{}).assets||{})[a.id]||{};
      const header=mcEl("div","row");header.append(mcEl("h3","",a.name),mcButton(this._open===a.id?"Hide details":"Details",()=>{this._open=this._open===a.id?"":a.id;this.render();}));
      card.append(header);
      mcPair(card,"Battery",mcValue(obs.soc,"%"));
      mcPair(card,"Target",a.target_soc===undefined?"Not set":a.target_soc+"%");
      mcPair(card,"Ready By",mcTime(a.ready_by,d.timezone));
      mcPair(card,"Charger",charger?charger.name:"Not assigned");
      if(this._open===a.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Charging priority",a.priority===undefined?"Not set":a.priority);
        mcPair(detail,"Battery data",obs.soc?(obs.soc.quality+" · "+(a.soc_entity||"manual")):"Unknown");
        mcPair(detail,"Requested energy",a.requested_kwh===undefined?"Not set":a.requested_kwh+" kWh");
        mcPair(detail,"Duration",a.requested_duration_minutes===undefined?"Not set":a.requested_duration_minutes+" min");
        this.configure(detail);card.append(detail);
      }
      container.append(card);
    }
    if(this._assetEditor==="new"){
      const form=mcEl("form","card");form.append(mcEl("h3","","Add a chargeable asset"));
      const name=this.field(form,"Asset name","","text");
      const kind=this.field(form,"Asset type","car",null,[["car","Car"],["bicycle","Bicycle"],["other","Other"]]);
      const energy=this.field(form,"Requested energy (kWh)","", "number");
      form.append(mcButton("Create asset",()=>{
        const id=name.value.trim().toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
        const changes={name:name.value.trim(),kind:kind.value};
        if(energy.value!=="")changes.requested_kwh=Number(energy.value);
        this.saveSettings("asset",id,changes,"create");
      }));
      container.append(form);
    }
    this.feedback(container);
    container.append(mcButton(this._assetEditor==="new"?"Cancel adding":"Add asset",()=>{
      this._assetEditor=this._assetEditor==="new"?"":"new";this.render();
    }));
  }
  chargers(container){
    const d=this._data,chargers=d.configuration.chargers||[],observations=(d.observations||{}).chargers||{};
    this.title(container,"Chargers ("+chargers.length+")");
    if(!chargers.length)this.notice(container,"No charging points configured.",false);
    for(const c of chargers){
      const obs=observations[c.id]||{};
      const card=mcEl("div","card");
      const head=mcEl("div","row");head.append(mcEl("h3","",c.name),mcButton(this._open===c.id?"Hide details":"Details",()=>{this._open=this._open===c.id?"":c.id;this.render();}));
      card.append(head);
      mcPair(card,"Connection",mcValue(obs.connected));
      mcPair(card,"Actual power",mcValue(obs.power_kw," kW"));
      mcPair(card,"Control type",c.kind==="on_off"?"On/off":"Verified variable current when commissioned");
      const session=(d.active_sessions||{})[c.id];
      if(session){
        mcPair(card,"Active session",mcTime(session.started_at,d.timezone));
        mcPair(card,"Measured session energy",
               session.actual_energy_kwh===null?"Unknown":session.actual_energy_kwh+" kWh");
      }
      mcPair(card,"Assigned asset",c.asset||"Not assigned");
      const history=(d.completed_sessions||[]).filter(x=>x.charger_id===c.id);
      const latest=history.length?history[history.length-1]:null;
      if(latest){
        mcPair(card,"Last confirmed session",mcTime(latest.ended_at,d.timezone));
        mcPair(card,"Measured energy",latest.actual_energy_kwh===null?"Unknown":latest.actual_energy_kwh+" kWh");
        mcPair(card,"Verified cost",latest.cost===null?"Unknown":latest.cost+" "+latest.currency);
      }
      if(this._open===c.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Rated power",c.rated_power_kw+" kW");
        mcPair(detail,"Phases",c.phase_count||"Unverified");
        mcPair(detail,"Current range",c.min_current_a&&c.max_current_a?c.min_current_a+"–"+c.max_current_a+" A":"Not supported/verified");
        mcPair(detail,"Source state",obs.power_kw?(obs.power_kw.quality+" · "+obs.power_kw.reason):"Unknown");
        const actual=(d.command_outcomes||{})[c.id]||{};
        mcPair(detail,"Command outcome",actual.status||"No command issued");
        if(actual.reason)mcPair(detail,"Reason",actual.reason);
        if(actual.readback_at)mcPair(detail,"Measured confirmation",mcTime(actual.readback_at,d.timezone));
        this.configure(detail);card.append(detail);
      }
      const capability=(d.command_capabilities||{})[c.id]||{};
      const outcome=this._commandFeedback[c.id]||(d.command_outcomes||{})[c.id];
      const controls=mcEl("div","controls");
      if(capability.start_allowed){
        const start=mcButton("Start charging",()=>this.command(c.id,"start"));
        start.disabled=this._commandBusy;
        controls.append(start);
      }
      if(capability.stop_allowed){
        const stop=mcButton("Stop charging",()=>this.command(c.id,"stop"));
        stop.disabled=this._commandBusy;
        controls.append(stop);
      }
      if(controls.children.length)card.append(controls);
      if(!capability.start_allowed && capability.reason)
        card.append(mcEl("p","muted small","Start unavailable: "+capability.reason));
      if(outcome){
        const bad=outcome.status==="rejected"||outcome.status==="execution_unknown";
        const status=mcEl("p","small"+(bad?" error":""),outcome.status+" — "+outcome.reason);
        status.setAttribute("role",bad?"alert":"status");
        card.append(status);
      }
      container.append(card);
    }
    container.append(mcButton("Add charger",()=>this.settingsSelect(container,"Sources & bindings")));
  }
  settings(container){
    const d=this._data,c=d.configuration||{},ctl=c.controller||{};
    this.title(container,"Settings");
    this.notice(container,"Changes are validated by Home Assistant and confirmed only after reloading. Stop active owned chargers before structural changes; commissioning and hardware capabilities remain in native advanced options.",false);
    this.feedback(container);
    for(const title of MC_SETTINGS){
      const group=mcEl("section","card"),open=title===this._settingsOpen;
      const row=mcEl("div","row");
      row.append(mcEl("h3","",title),mcButton(open?"Close":"Edit",()=>{
        this._settingsOpen=open?"":title;this.render();
      }));
      group.append(row);
      if(open){
        const detail=mcEl("div","details");
        if(title==="Charging site"){
          const name=this.field(detail,"Site name",ctl.name);
          const parallel=this.field(detail,"Parallel chargers",ctl.max_parallel,"number");
          const power=this.field(detail,"Group power ceiling kW",ctl.max_power_kw,"number");
          detail.append(mcButton("Save charging site",()=>this.saveSettings(
            "controller",ctl.id,{name:name.value,max_parallel:Number(parallel.value),
            max_power_kw:power.value===""?null:Number(power.value)}
          )));
        }else if(title==="Sources & bindings"){
          const price=this.field(detail,"Effective tariff source",ctl.price_entity);
          const solar=this.field(detail,"Solar capacity source",ctl.solar_entity);
          const binding=this.field(detail,"Binding power envelope",ctl.binding_entity);
          detail.append(mcButton("Save sources",()=>this.saveSettings(
            "controller",ctl.id,{price_entity:price.value||null,
            solar_entity:solar.value||null,binding_entity:binding.value||null}
          )));
          detail.append(mcEl("p","muted small","Source IDs must refer to existing qualified native Home Assistant sensors. Unknown capacity never becomes unlimited."));
        }else if(title==="Charging strategy"){
          detail.append(mcEl("p","", "Selected: "+(ctl.mode||"Off")));
          const chips=mcEl("div","chips");
          for(const mode of MC_MODES){
            const button=mcButton(mode,()=>this.saveSettings("controller",ctl.id,{mode}));
            button.disabled=this._settingsBusy||mode===ctl.mode;
            if(mode===ctl.mode)button.className="active";
            chips.append(button);
          }
          detail.append(chips);
        }else if(title==="Safety & limits"){
          const power=this.field(detail,"Maximum group kW",ctl.max_power_kw,"number");
          const phases=this.field(detail,"Verified phase ceilings (A)",
            Object.entries(ctl.phase_limits_a||{}).map(([key,val])=>key+":"+val).join(","));
          detail.append(mcButton("Save electrical limits",()=>{
            let limits=null;
            if(phases.value.trim()){
              limits={};
              for(const part of phases.value.split(",")){
                const pieces=part.trim().split(":");
                if(pieces.length!==2||!["L1","L2","L3"].includes(pieces[0].trim().toUpperCase())){
                  this._settingsFeedback={status:"rejected",message:"Use verified phase limits such as L1:16,L2:16,L3:16."};this.render();return;
                }
                limits[pieces[0].trim().toUpperCase()]=Number(pieces[1]);
              }
            }
            this.saveSettings("controller",ctl.id,{
              max_power_kw:power.value===""?null:Number(power.value),
              phase_limits_a:limits
            });
          }));
          detail.append(mcEl("p","muted small","Circuit wiring, physical ownership and commissioning are only changed through native expert configuration after electrical verification."));
        }else if(title==="Integrations"){
          detail.append(mcEl("p","","Home Assistant integrations own physical sources and charger devices. MultiCharge only references their qualified entities."));
          mcPair(detail,"Tariff",(d.observations||{}).sources?.tariff_quality||"Unknown");
          mcPair(detail,"Solar",(d.observations||{}).sources?.solar_quality||"Unknown");
          mcPair(detail,"Capacity",(d.observations||{}).sources?.binding_quality||"Unknown");
          this.configure(detail);
        }else{
          detail.append(mcEl("p","","Advanced wiring, assets, charger commissioning, import and YAML remain managed by native Home Assistant Options. Existing logical IDs are retained on edit."));
          this.configure(detail);
        }
        group.append(detail);
      }
      container.append(group);
    }
  }
}
if(!customElements.get("robotix-multicharge-card"))customElements.define("robotix-multicharge-card",RobotixMultiChargeCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="robotix-multicharge-card")){
  window.customCards.push({type:"robotix-multicharge-card",name:"Robotix MultiCharge",description:"Five-tab charging proposals, actual source status and native configuration"});
}