// Explicit runtime fault rehearsal. Restores gateway/twin in finally.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import { execFileSync } from 'node:child_process';
import { mkdirSync,writeFileSync,appendFileSync } from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const out=path.resolve('docs/audit_evidence/2026-09-13-exhibition');mkdirSync(out,{recursive:true});
const run=`failures-${Date.now()}`;const evidence=path.join(out,`${run}.jsonl`);
const record=(kind,data)=>appendFileSync(evidence,JSON.stringify({timestamp:Date.now(),kind,...data})+'\n');
const docker=(...args)=>{const result=execFileSync('docker',args,{encoding:'utf8',timeout:45000});record('runtime_command',{args,result});return result;};
const stopAttack=()=>docker('exec','smart_grid_mqtt','mosquitto_pub','-t','grid/attack','-m','{"action":"STOP"}');
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1920,height:1080}});
let latest=null,paused=false,gatewayStopped=false,attackQueued=false;
const results={},errors=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('websocket',ws=>{record('socket_open',{url:ws.url()});ws.on('close',()=>record('socket_closed',{}));ws.on('framesent',({payload})=>{try{const d=JSON.parse(payload);if(d.topic==='grid/attack')record('browser_command',d);}catch{}});ws.on('framereceived',({payload})=>{try{const d=JSON.parse(payload);if(d.type==='BOOTSTRAP'&&Object.keys(d.telemetry?.state?.buses||{}).length===39)latest=d.telemetry;if(d.topic==='pypy/grid/telemetry'){latest=d.payload;record('canonical_telemetry',{timestamp:latest.timestamp,attack:latest.attack_status,breakers:latest.state?.breakers,solver:latest.solver_status});}}catch{}});});
const screen=async(name)=>{record('screen',{name,text:await page.locator('main').innerText()});await page.screenshot({path:path.join(out,`${run}-${name}.png`),fullPage:true});};
const fresh=async()=>page.waitForFunction(()=>{const b=document.querySelector('.ex-launch');return b&&!b.disabled;},{},{timeout:45000});
try{
  await page.goto('http://localhost:3001/#/exhibition');await fresh();
  assert.ok(latest&&!latest.attack_status?.active_attack);assert.ok(Object.values(latest.state.breakers).every(v=>v==='CLOSED'));
  gatewayStopped=true;docker('compose','stop','gateway');
  await page.waitForFunction(()=>document.querySelector('h1')?.textContent==='CONNECTION LOST');
  results.gateway_stop='CONNECTION LOST; launch disabled';assert.ok(await page.getByRole('button',{name:'LAUNCH CYBER ATTACK',exact:true}).isDisabled());await screen('gateway-stopped');
  docker('compose','start','gateway');gatewayStopped=false;await fresh();results.gateway_restart='WebSocket reconnected; fresh telemetry; launch enabled';await screen('gateway-reconnected');
  paused=true;docker('pause','smart_grid_digital_twin');const frozenTimestamp=latest.timestamp;
  await page.getByRole('button',{name:'LAUNCH CYBER ATTACK',exact:true}).click();
  attackQueued=true;await page.getByRole('button',{name:'Launch selected attack',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.ex-notice')?.textContent.includes('Command not confirmed'),{},{timeout:22000});
  results.unconfirmed_attack='Real command forwarded while twin paused; 15-second unconfirmed-outcome notice';await screen('attack-unconfirmed');
  await page.waitForFunction(()=>document.querySelector('h1')?.textContent==='TELEMETRY UNAVAILABLE',{},{timeout:25000});
  assert.ok(await page.getByRole('button',{name:'LAUNCH CYBER ATTACK',exact:true}).isDisabled());assert.equal(latest.timestamp,frozenTimestamp);
  assert.notEqual(await page.locator('h1').innerText(),'GRID SECURED');results.frozen_telemetry='TELEMETRY UNAVAILABLE after source freshness expiry; no false success';await screen('telemetry-frozen');
  // Queue STOP before resuming the frozen consumer. This terminates any queued
  // START through the existing documented broker command, never manual CLOSE.
  stopAttack();docker('unpause','smart_grid_digital_twin');paused=false;
  await page.waitForTimeout(2500);stopAttack();attackQueued=false;
  await fresh();results.twin_resumed='Canonical telemetry resumed; no active attack';await screen('telemetry-restored');
  await page.getByRole('button',{name:'Enter fullscreen',exact:true}).click();await page.waitForFunction(()=>!!document.fullscreenElement);
  await page.getByRole('button',{name:'Exit fullscreen',exact:true}).click();results.fullscreen='passed';
  await page.reload();await fresh();results.refresh='passed';
  assert.ok(!latest.attack_status?.active_attack);assert.ok(Object.values(latest.state.breakers).every(v=>v==='CLOSED'));
  results.final={timestamp:latest.timestamp,solver:latest.solver_status,active_attack:latest.attack_status?.active_attack,all_breakers_closed:true};
}catch(e){results.error=e.message;process.exitCode=1;}
finally{
  if(attackQueued)try{stopAttack();}catch{}
  if(paused)try{docker('unpause','smart_grid_digital_twin');}catch{}
  if(gatewayStopped)try{docker('compose','start','gateway');}catch{}
  results.page_errors=errors;writeFileSync(path.join(out,`${run}-summary.json`),JSON.stringify(results,null,2));console.log(JSON.stringify({file:`${run}-summary.json`,...results},null,2));await browser.close();
}
