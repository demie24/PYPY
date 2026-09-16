import assert from 'node:assert/strict';
import test from 'node:test';
import { exhibitionState, fresh } from '../src/exhibitionState.ts';
import { emptyRecoveryEvidence, reduceRecoveryEvidence } from '../src/recoveryEvidence.ts';

const now = 1800000000000;
const telemetry = (): any => ({ timestamp: now, telemetry_id: 'test:final', experiment_id: 'test', solver_status: {converged:true}, attack_status:{active_attack:null}, state:{
  buses:Object.fromEntries(Array.from({length:39},(_,i)=>['Bus_'+(i+1),{voltage_pu:i===35?1.0636:i===24?1.056:1}])),
  lines:Object.fromEntries(Array.from({length:46},(_,i)=>['L_line_'+i,{}])),
  breakers:Object.fromEntries(Array.from({length:46},(_,i)=>['L_line_'+i,'CLOSED']))
}});
const props = (): any => ({connected:true,telemetry:telemetry(),alerts:[],threat:null,trustScores:null,aiFusion:null,recoveryEvidence:emptyRecoveryEvidence()});
const sandbox = {overall_safe:true,solver_converged:true,voltage_safe:true,thermal_safe:true,topology_valid:true,cascade_safe:true,finite_state:true};
function recovery(options: {command?:string; receiptOnly?:boolean; replayReceipt?:boolean; omitOpen?:boolean} = {}) {
  const proposal:any = {timestamp:now-2000,correlation_id:'test',source_telemetry_id:'test:proposal-input',experiment_id:'test',target:'L_line_0',command:options.command||'CLOSE',source:'AI_RL_PPO_DQN_CONSENSUS',sandbox:{...sandbox,timestamp:now-2000},initial_state:'OPEN'};
  if(options.receiptOnly) delete proposal.timestamp;
  const opened=telemetry();opened.timestamp=now-3000;opened.state.breakers.L_line_0='OPEN';
  const control:any={...proposal,timestamp:now-1000,source:'ORCHESTRATOR_APPROVED'};
  if(options.receiptOnly || options.replayReceipt) delete control.timestamp;
  if(options.replayReceipt) control._evidence_timestamp=now-1000;
  const items:any[]=[...(!options.omitOpen?[['pypy/grid/telemetry',opened]]:[]),
    ['grid/ai/recovery_policy',{...proposal,timestamp:now-2500,source_telemetry_id:'test:earlier-policy-input'}],
    ['grid/control/proposed',proposal],
    ['grid/orchestrator/events',{...proposal,timestamp:now-1500,event:'APPROVAL'}],
    ['grid/control',control],['pypy/grid/telemetry',telemetry()]];
  return items.reduce((s,[topic,payload])=>reduceRecoveryEvidence(s,topic,payload),emptyRecoveryEvidence());
}
test('IEEE39 safety envelope permits healthy >1.05 buses and an evidenced restoration',()=>{
  const p=props();assert.equal(exhibitionState(p,now).stable,true);
  p.recoveryEvidence=recovery();assert.equal(exhibitionState(p,now).verified,true);
  assert.equal(exhibitionState(p,now).headline,'GRID SECURED');
});
test('timestamp-less dispatch freezes receipt time without changing the control payload',t=>{
  t.mock.method(Date,'now',()=>now-1000);
  const p=props();p.recoveryEvidence=recovery({receiptOnly:true});
  assert.equal(p.recoveryEvidence.attempts[0].dispatched.timestamp,undefined);
  assert.equal(p.recoveryEvidence.attempts[0].sourceTelemetryId,'test:proposal-input');
  t.mock.method(Date,'now',()=>now+1000);
  assert.equal(exhibitionState(p,now).verified,true);
  p.recoveryEvidence=recovery({replayReceipt:true});assert.equal(exhibitionState(p,now).verified,true);
});
test('stale, disconnected, active attacker, OPEN and unconverged states cannot succeed',()=>{
  for(const mutate of [
    (p:any)=>{p.telemetry.timestamp=now-31000;},
    (p:any)=>{p.connected=false;},
    (p:any)=>{p.telemetry.attack_status.active_attack='BREAKER_MANIPULATION';},
    (p:any)=>{p.telemetry.state.breakers.L_line_0='OPEN';},
    (p:any)=>{p.telemetry.solver_status.converged=false;},
    (p:any)=>{p.telemetry.state.breakers.L_line_1='OPEN';},
    (p:any)=>{delete p.telemetry.state.breakers.L_line_1;},
    (p:any)=>{delete p.telemetry.attack_status;},
    (p:any)=>{p.telemetry.state.buses.Bus_1.voltage_pu=.8;},
    (p:any)=>{p.telemetry.experiment_id='other';},
  ]) {const p=props();p.recoveryEvidence=recovery();mutate(p);assert.equal(exhibitionState(p,now).verified,false);}
  const p=props();p.telemetry.timestamp=now-31000;assert.equal(exhibitionState(p,now).headline,'TELEMETRY UNAVAILABLE');
  p.connected=false;assert.equal(exhibitionState(p,now).headline,'CONNECTION LOST');
  assert.ok(exhibitionState(p,now).stages.every(s=>s.state==='idle'));
  assert.equal(fresh({timestamp:now+100000},now),false);
});
test('STOP/FDIA detection and rejected isolation are not autonomous restoration',()=>{
  const p=props();p.telemetry.attack_status.active_attack='FDIA';
  p.alerts=[{timestamp:now,type:'GRID_DEVIATION'}];
  assert.equal(exhibitionState(p,now).stages[1].state,'warning');
  p.telemetry.attack_status.active_attack=null;assert.equal(exhibitionState(p,now).verified,false);
  p.recoveryEvidence=recovery({command:'OPEN'});assert.equal(exhibitionState(p,now).verified,false);
});
test('approval, safe PPO/DQN proposal, observed OPEN, correlation and recent dispatch are mandatory',()=>{
  for(const mutate of [
    (a:any)=>{a.evidence=a.evidence.filter((e:any)=>e.stage!=='APPROVED');},
    (a:any)=>{a.proposal={...a.proposal,sandbox:{...sandbox,overall_safe:false}};},
    (a:any)=>{a.proposal={...a.proposal,source:'OPERATOR'};},
    (a:any)=>{a.observedOpen=undefined;},
    (a:any)=>{a.evidence.find((e:any)=>e.stage==='CONTROL DISPATCHED').timestamp=now-61000;},
    (a:any)=>{a.evidence.find((e:any)=>e.stage==='CONTROL DISPATCHED').payload={...a.dispatched,correlation_id:'other'};},
    (a:any)=>{a.evidence.find((e:any)=>e.stage==='CONTROL DISPATCHED').payload={...a.dispatched,source_telemetry_id:'test:unrelated-input'};},
  ]) {const p=props();p.recoveryEvidence=recovery();mutate(p.recoveryEvidence.attempts[0]);assert.equal(exhibitionState(p,now).verified,false);}
});
test('CLOSE followed by OPEN stays unverified; legacy or missing canonical frames cannot certify recovery',()=>{
  const p=props();p.recoveryEvidence=recovery();
  const open=telemetry();open.timestamp=now+1;open.state.breakers.L_line_0='OPEN';
  p.recoveryEvidence=reduceRecoveryEvidence(p.recoveryEvidence,'pypy/grid/telemetry',open);p.telemetry=open;
  assert.equal(exhibitionState(p,now+1).headline,'VERIFYING GRID RESPONSE');
  const legacy=telemetry();legacy.timestamp=now+2;
  p.recoveryEvidence=reduceRecoveryEvidence(p.recoveryEvidence,'grid/telemetry',legacy);p.telemetry=legacy;
  assert.equal(exhibitionState(p,now+2).verified,false);
  p.telemetry=telemetry();p.recoveryEvidence=recovery();
  p.recoveryEvidence.attempts[0].evidence=p.recoveryEvidence.attempts[0].evidence.filter((e:any)=>e.stage!=='TELEMETRY VERIFIED');
  assert.equal(exhibitionState(p,now).verified,false);
});
test('refresh without original OPEN evidence fails closed despite declared initial_state OPEN',()=>{
  const p=props();p.recoveryEvidence=recovery({omitOpen:true,replayReceipt:true});
  assert.equal(exhibitionState(p,now).verified,false);
});
