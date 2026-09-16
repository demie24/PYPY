// Read-only layout regression against the deployed dashboard at 100% zoom.
// Navigates pages but never executes attack, recovery, settings or report actions.
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({headless:true});
const page = await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
const errors=[],commands=[],results=[];
page.on('pageerror',error=>errors.push(error.message));
page.on('websocket',socket=>socket.on('framesent',({payload})=>{
  try { const message=JSON.parse(payload); if(['grid/attack','grid/control','grid/control/proposed'].includes(message.topic)) commands.push(message); } catch {}
}));
const routes=[['overview','Overview'],['grid','Live Grid'],['detection','Cyber Detection'],['decision','AI Decision'],['recovery','Self-Healing'],['simulation','Attack Simulation'],['forensics','Logs & Forensics'],['health','System Health'],['reports','Reports'],['settings','Settings']];
try {
  await page.goto(`${process.env.EXHIBITION_URL || 'http://localhost:3001'}/#/overview`,{waitUntil:'domcontentloaded'});
  await page.waitForSelector('.pypy-footer');
  for(const [width,height] of [[1920,1080],[1440,900],[1366,768],[390,844]]) {
    await page.setViewportSize({width,height});
    for(const [route,label] of routes) {
      if(width<=760) await page.getByRole('button',{name:'Open navigation',exact:true}).click();
      await page.locator('.pypy-sidebar nav button').filter({hasText:label}).click();
      await page.waitForSelector(`[data-control-page="${route}"]`);
      if(width<=760) {
        await page.locator('.pypy-sidebar').waitFor({state:'hidden'});
        await page.locator('.pypy-sidebar').evaluate(e=>Promise.all(e.getAnimations().map(animation=>animation.finished.catch(()=>{}))));
      }
      const workspace=page.locator('.pypy-workspace');
      await workspace.evaluate(e=>{e.scrollTop=0;});
      const before=await page.evaluate(()=>{
        const workspace=document.querySelector('.pypy-workspace');
        return {height:workspace.clientHeight,scrollHeight:workspace.scrollHeight,left:workspace.getBoundingClientRect().left,headerTop:document.querySelector('.pypy-topbar').getBoundingClientRect().top};
      });
      console.log('Checking',width,height,route,before);
      // The content gutter avoids intentionally scrollable tables/consoles.
      await page.mouse.move(before.left+5,height/2);
      await page.mouse.wheel(0,before.scrollHeight+height);
      await page.waitForFunction(()=>{
        const workspace=document.querySelector('.pypy-workspace');
        return workspace.scrollTop+workspace.clientHeight>=workspace.scrollHeight-2;
      },null,{timeout:5000}).catch(async error=>{
        console.error('Scroll failure',await workspace.evaluate(e=>({top:e.scrollTop,height:e.clientHeight,scrollHeight:e.scrollHeight,overflow:getComputedStyle(e).overflowY,hit:document.elementFromPoint(e.getBoundingClientRect().left+5,innerHeight/2)?.outerHTML.slice(0,300)})));
        throw error;
      });
      const after=await page.evaluate(()=>{
        const workspace=document.querySelector('.pypy-workspace'),footer=document.querySelector('.pypy-footer');
        const scrollers=[];
        for(let element=footer.parentElement;element;element=element.parentElement) {
          if(/auto|scroll/.test(getComputedStyle(element).overflowY)) scrollers.push(element.className || element.tagName);
        }
        return {scrollTop:workspace.scrollTop,scrollHeight:workspace.scrollHeight,clientHeight:workspace.clientHeight,footerTop:footer.getBoundingClientRect().top,footerBottom:footer.getBoundingClientRect().bottom,headerTop:document.querySelector('.pypy-topbar').getBoundingClientRect().top,headerBottom:document.querySelector('.pypy-topbar').getBoundingClientRect().bottom,documentHeight:document.documentElement.scrollHeight,documentWidth:document.documentElement.scrollWidth,workspaceWidth:workspace.clientWidth,workspaceScrollWidth:workspace.scrollWidth,windowScroll:scrollY,zoom:visualViewport.scale,sidebarPosition:getComputedStyle(document.querySelector('.pypy-sidebar')).position,scrollers};
      });
      assert.equal(after.zoom,1,'No zoom workaround');
      assert.equal(before.height,height,'Workspace is viewport constrained');
      assert.ok(after.footerBottom<=height+1 && after.footerTop>=after.headerBottom,`${route}: entire footer reachable`);
      assert.ok(Math.abs(after.headerTop-before.headerTop)<1 && Math.abs(after.headerTop)<1,'Header stays sticky');
      assert.equal(after.sidebarPosition,'fixed');
      assert.equal(after.windowScroll,0,'No second document scroll');
      assert.ok(after.documentHeight<=height+1 && after.documentWidth<=width,'No body overflow');
      assert.ok(after.workspaceScrollWidth<=after.workspaceWidth,'No workspace horizontal scrollbar');
      assert.deepEqual(after.scrollers,['pypy-workspace'],'One content scroll container');
      if(route==='overview') assert.ok(after.scrollTop>0,'Overview really scrolls by mouse wheel');
      results.push({width,height,route,scrollTop:after.scrollTop,contentHeight:after.scrollHeight,footerBottom:after.footerBottom});
      if(route==='overview') await page.screenshot({path:`/tmp/pypy-overview-scroll-${width}x${height}.png`});
    }
  }
  assert.deepEqual(errors,[]);
  assert.deepEqual(commands,[],'Read-only verification sent no control commands');
  console.log(JSON.stringify({result:'PASS',checks:results.length,results,pageErrors:errors,controlCommands:commands},null,2));
} finally { await browser.close(); }
