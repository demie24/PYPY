// Isolated Overview data-flow regression; no fixture reaches the real gateway.
import assert from 'node:assert/strict';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}});
const errors=[],commands=[];
page.on('pageerror',error=>errors.push(error.message));
try {
  const response=await page.request.get('http://localhost:8000/api/telemetry/topology?grid_name=ieee39');
  assert.equal(response.ok(),true);
  const topology=await response.json();
  await page.route('**/api/telemetry/topology?*',route=>route.fulfill({json:topology}));
  let socket;
  await page.routeWebSocket('**/ws',ws=>{
    socket=ws;ws.onMessage(message=>commands.push(message));
    ws.send(JSON.stringify({type:'BOOTSTRAP',telemetry:null,events:[],alerts:[]}));
  });
  await page.goto(`${process.env.EXHIBITION_URL || 'http://localhost:3001'}/#/overview`,{waitUntil:'domcontentloaded'});
  const card=label=>page.locator('.pypy-metric').filter({has:page.locator('p',{hasText:label})});
  const value=label=>card(label).locator('.pypy-metric-copy > strong');
  await page.waitForSelector('.pypy-metric');
  assert.equal(await value('Active power load').innerText(),'Unavailable');
  assert.equal(await value('AI live readiness').innerText(),'Unavailable');
  const buses=Object.fromEntries(Object.keys(topology.buses).map(id=>[id,{voltage_pu:1,is_load:false,is_gen:false,P_mw:0,active_power:10000,load_mw:20000,p_load_mw:30000}]));
  Object.assign(buses.Bus_1,{is_load:true,P_mw:10.5});
  Object.assign(buses.Bus_2,{is_load:true,P_mw:20});
  Object.assign(buses.Bus_3,{is_gen:true,P_mw:999});
  Object.assign(buses.Bus_4,{is_load:'true',P_mw:888});
  const frame=()=>({timestamp:Date.now(),grid_name:'ieee39',solver_status:{converged:true},attack_status:{active_attack:null},state:{buses,lines:Object.fromEntries(topology.lines.map(line=>[line.id,{}])),breakers:Object.fromEntries(topology.lines.map(line=>[line.id,'CLOSED']))}});
  const send=(topic,payload)=>socket.send(JSON.stringify({topic,payload}));
  send('pypy/grid/telemetry',frame());
  await page.waitForFunction(()=>[...document.querySelectorAll('.pypy-metric')].some(e=>e.textContent.includes('Active power load')&&e.textContent.includes('30.5 MW')));
  for(const id of ['lstm','gnn','stgnn','pinn']) send(`grid/ai/status/${id}`,{ready:true});
  send('grid/ai/status/ppo',{ready:false});send('grid/ai/status/dqn',{ready:'true'});send('grid/ai/status/unrelated_service',{ready:true});
  await page.waitForFunction(()=>[...document.querySelectorAll('.pypy-metric')].some(e=>e.textContent.includes('AI live readiness')&&e.textContent.includes('4/6')));
  assert.equal(await value('Active power load').innerText(),'30.5 MW');
  assert.equal(await card('AI live readiness').locator('small').innerText(),'Models confirmed ready by live signals');
  Object.assign(buses.Bus_1,{P_mw:0});Object.assign(buses.Bus_2,{P_mw:0});
  send('pypy/grid/telemetry',frame());send('grid/ai/status/pinn',{ready:false});
  await page.waitForFunction(()=>[...document.querySelectorAll('.pypy-metric')].some(e=>e.textContent.includes('Active power load')&&e.textContent.includes('0.0 MW')));
  assert.equal(await value('AI live readiness').innerText(),'3/6');
  assert.deepEqual(errors,[]);assert.deepEqual(commands,[]);
  console.log('PASS: authoritative is_load === true P_mw only; excludes generators, truthy non-boolean flags and generic power fields; missing data unavailable; zero load valid; readiness follows live boolean signals (4/6 then 3/6), not service count.');
} finally {await browser.close();}
