import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { openQaBrowser, delay } from './cdp.mjs';

const browser = await openQaBrowser({ url: 'http://localhost:3000/#painel', width: 1120, height: 900, port: 9345, profile: 'browser-redesign-header-qa' });
const results = [];
try {
  for (const width of [1120, 960]) {
    await browser.send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await browser.send('Page.navigate', { url: 'http://localhost:3000/#painel' });
    await delay(700);
    const result = await browser.evaluate(`(()=>{const h=document.querySelector('.site-header').getBoundingClientRect();const nav=document.querySelector('.top-nav').getBoundingClientRect();return{width:innerWidth,scrollWidth:document.documentElement.scrollWidth,headerHeight:h.height,navLeft:nav.left,navRight:nav.right,links:Array.from(document.querySelectorAll('.nav-item')).map(n=>({label:n.textContent.trim().replace(/\\s+/g,' '),clientWidth:n.clientWidth,scrollWidth:n.scrollWidth}))}})()`);
    assert(result.scrollWidth <= width);
    assert(result.navLeft >= 0 && result.navRight <= width);
    assert(result.links.every(link => link.scrollWidth <= link.clientWidth));
    await browser.evaluate('window.scrollTo(0,500)');
    await delay(200);
    result.scrolled = await browser.evaluate(`({scrollY,headerTop:document.querySelector('.site-header').getBoundingClientRect().top,headerPosition:getComputedStyle(document.querySelector('.site-header')).position})`);
    assert(result.scrolled.scrollY > 0);
    assert.equal(result.scrolled.headerPosition, 'sticky');
    assert.equal(result.scrolled.headerTop, 0);
    results.push(result);
  }
  await writeFile(fileURLToPath(new URL('../evidence/redesenho-header-qa.json', import.meta.url)), JSON.stringify({ generatedAt: new Date().toISOString(), results }, null, 2));
  console.log(JSON.stringify(results, null, 2));
} finally { await browser.close(); }
