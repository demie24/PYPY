// Opt-in live rehearsal. Unlike dashboard/tests, this uses the real gateway.
// Modes: baseline (read-only), breaker, fdia. START is always followed by STOP.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import { mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const mode = process.argv[2] || 'baseline';
if (!['baseline','breaker','fdia','resume'].includes(mode)) throw new Error('Unsupported rehearsal mode');
const out = path.resolve('docs/audit_evidence/2026-09-13-exhibition');
mkdirSync(out,{recursive:true});
const run = `${mode}-${Date.now()}`;
const stream = path.join(out,`${run}.jsonl`);
const browser = await chromium.launch({headless:true});
const page = await browser.newPage({viewport:{width:1920,height:1080}});
let latest=null, issued=false, closed=0;
const packets=[],errors=[],requests=[],commands=[];
const start=Date.now();
const record=(kind,data)=>appendFileSync(stream,JSON.stringify({received_at:Date.now(),kind,...data})+'\n');
page.on('pageerror',e=>errors.push(e.message));
page.on('requestfailed',r=>requests.push({url:r.url(),error:r.failure()?.errorText}));
page.on('websocket',ws=>{
  record('socket',{url:ws.url()});
  ws.on('close',()=>{closed++;record('socket_closed',{});});
  ws.on('framesent',({payload})=>{try{const d=JSON.parse(payload);if(d.topic==='grid/attack'){commands.push(d);record('browser_command',d);}}catch{}});
  ws.on('framereceived',({payload})=>{try{
    const d=JSON.parse(payload);
    if(d.type==='BOOTSTRAP'){if(Object.keys(d.telemetry?.state?.buses||{}).length===39)latest=d.telemetry;record('bootstrap',{telemetry:d.telemetry,threat:d.threat,trust_scores:d.trust_scores,events:d.events,alerts:d.alerts});}
    const topic=d.topic,p=d.payload;
    if(!topic)return;
    if(topic==='pypy/grid/telemetry'||topic==='grid/telemetry'){
      if(topic==='pypy/grid/telemetry' && Object.keys(p.state?.buses||{}).length===39)latest=p;
      record('telemetry',{topic,payload:{timestamp:p.timestamp,telemetry_id:p.telemetry_id,experiment_id:p.experiment_id,solver_status:p.solver_status,attack_status:p.attack_status,buses:p.state?.buses,breakers:p.state?.breakers}});
    }else if(['grid/events','grid/alerts','grid/trust_scores','grid/physics_validation','grid/ai/fusion','grid/threat','grid/control/proposed','grid/ai/recovery_policy','grid/orchestrator/events','grid/control'].includes(topic)){
      packets.push({topic,payload:p,received_at:Date.now()});record('evidence',{topic,payload:p});
    }
  }catch{}});
});
const snapshot=async(name)=>{await page.screenshot({path:path.join(out,`${run}-${name}.png`),fullPage:true});const text=await page.locator('main').innerText();record('screen',{name,text});return text;};
const waitUntil=async(fn,ms)=>{const until=Date.now()+ms;while(Date.now()<until){if(fn())return true;await page.waitForTimeout(500);}return false;};
let outcome={mode,started_at:start};
try{
  await page.goto('http://localhost:3001/#/exhibition');
  await page.waitForSelector('[data-testid="exhibition"]');
  if(!await waitUntil(()=>latest?.timestamp && Date.now()-latest.timestamp<10000,30000))throw new Error('Fresh telemetry unavailable');
  await page.waitForSelector('.ex-bus');
  await page.evaluate(()=>document.fonts.ready);
  const first=latest.timestamp;await page.waitForTimeout(5000);
  outcome.baseline={first_timestamp:first,last_timestamp:latest.timestamp,buses:Object.keys(latest.state.buses).length,branches:Object.keys(latest.state.lines).length,solver:latest.solver_status,attack:latest.attack_status,open:Object.entries(latest.state.breakers).filter(([,v])=>v!=='CLOSED'),voltage_min:Math.min(...Object.values(latest.state.buses).map(b=>b.voltage_pu)),voltage_max:Math.max(...Object.values(latest.state.buses).map(b=>b.voltage_pu)),headline:await page.locator('h1').innerText()};
  if(outcome.baseline.attack?.active_attack)throw new Error('An attack is already active; refusing to overlap');
  await snapshot('baseline');
  if(mode==='resume'){
    outcome.closed_after_runtime_restart=await waitUntil(()=>latest.state.breakers.L_line_0==='CLOSED',90000);
    await page.waitForTimeout(4000);
    outcome.final={timestamp:latest.timestamp,attack:latest.attack_status,breaker:latest.state.breakers.L_line_0,solver:latest.solver_status,headline:await page.locator('h1').innerText()};
    await snapshot('after-runtime-restart');
  }else if(mode!=='baseline'){
    if(outcome.baseline.open.length)throw new Error('Baseline contains open breakers; refusing to add another incident');
    await page.getByRole('button',{name:'LAUNCH CYBER ATTACK',exact:true}).click();
    if(mode==='breaker')await page.getByRole('button',{name:/Breaker manipulation/}).click();
    issued=true;
    await page.getByRole('button',{name:'Launch selected attack',exact:true}).click();
    const type=mode==='breaker'?'BREAKER_MANIPULATION':'FDIA';
    outcome.attack_confirmed=await waitUntil(()=>latest?.attack_status?.active_attack===type,15000);
    if(!outcome.attack_confirmed)throw new Error('Attack command was not confirmed');
    await page.waitForTimeout(mode==='fdia'?22000:1000);
    outcome.attack_state={timestamp:latest.timestamp,attack:latest.attack_status,breaker:latest.state.breakers.L_line_0,bus5:latest.state.buses.Bus_5,headline:await page.locator('h1').innerText()};
    await snapshot('attack');
    await page.getByRole('button',{name:'STOP ATTACK',exact:true}).click();
    outcome.stop_confirmed=await waitUntil(()=>!latest?.attack_status?.active_attack,15000);
    if(!outcome.stop_confirmed)throw new Error('STOP not confirmed');
    if(mode==='breaker')outcome.closed_after_stop=await waitUntil(()=>latest.state.breakers.L_line_0==='CLOSED',90000);
    else await page.waitForTimeout(15000);
    await page.waitForTimeout(4000);
    outcome.final={timestamp:latest.timestamp,attack:latest.attack_status,breaker:latest.state.breakers.L_line_0,solver:latest.solver_status,bus5:latest.state.buses.Bus_5,headline:await page.locator('h1').innerText()};
    await snapshot('after-stop');
  }
  outcome.topics=Object.fromEntries([...new Set(packets.map(p=>p.topic))].map(t=>[t,packets.filter(p=>p.topic===t).length]));
  outcome.alerts=packets.filter(p=>p.topic==='grid/alerts');
  outcome.decisions=packets.filter(p=>p.topic==='grid/orchestrator/events');
  outcome.controls=packets.filter(p=>p.topic==='grid/control');
  outcome.proposals=packets.filter(p=>p.topic==='grid/control/proposed');
  outcome.commands=commands;outcome.page_errors=errors;outcome.request_failures=requests;outcome.websocket_closes=closed;
}catch(e){outcome.error=e.message;console.error(e.message);process.exitCode=1;}
finally{
  if(issued && latest?.attack_status?.active_attack){execFileSync('docker',['exec','smart_grid_mqtt','mosquitto_pub','-t','grid/attack','-m','{"action":"STOP"}']);record('cleanup',{action:'STOP',path:'existing MQTT command'});}
  outcome.completed_at=Date.now();writeFileSync(path.join(out,`${run}-summary.json`),JSON.stringify(outcome,null,2));
  console.log(JSON.stringify({file:`${run}-summary.json`,...outcome},null,2));
  await browser.close();
}
