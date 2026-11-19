// Read-only UI verification for the top-navigation redesign. No occurrence is saved.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { openQaBrowser, delay } from './cdp.mjs';

const evidence = fileURLToPath(new URL('../evidence/', import.meta.url));
await mkdir(evidence, { recursive: true });
const baseUrl = process.env.QA_BASE_URL || 'http://localhost:3000';
const browser = await openQaBrowser({ url: `${baseUrl}/#painel`, width: 1440, height: 1200, port: 9344, profile: 'browser-redesign-qa' });
const report = { generatedAt: new Date().toISOString(), baseUrl, readOnly: true, viewports: [] };

async function waitUntil(expression, label) {
  for (let attempt = 0; attempt < 60; attempt++) {
    if (await browser.evaluate(expression)) return;
    await delay(100);
  }
  throw new Error(`Timeout: ${label}`);
}
async function click(selector) {
  const point = await browser.evaluate(`(()=>{const node=document.querySelector(${JSON.stringify(selector)});if(!node)throw new Error('Control missing');node.scrollIntoView({block:'nearest',inline:'nearest'});const r=node.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  await browser.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 });
  await browser.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 });
}
async function navigate(view) {
  await click(`.nav-item[data-view="${view}"]`);
  await waitUntil(`!document.querySelector('#view-${view}').hidden&&document.querySelector('.nav-item[data-view="${view}"]').getAttribute('aria-current')==='page'`, `navigation ${view}`);
  assert.equal(await browser.evaluate(`document.querySelectorAll('.nav-item[aria-current="page"]').length`), 1);
}
async function checkOverflow(label) {
  const value = await browser.evaluate(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,mainLeft:document.querySelector('#main').getBoundingClientRect().left,mainRight:document.querySelector('#main').getBoundingClientRect().right})`);
  assert(value.scrollWidth <= value.width, `${label}: horizontal page overflow ${JSON.stringify(value)}`);
  return value;
}

try {
  for (const [name, width, height] of [['desktop', 1440, 1200], ['mobile', 390, 1250], ['mobile-320', 320, 1250]]) {
    await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: name !== 'desktop' });
    await browser.send('Page.navigate', { url: `${baseUrl}/#painel` });
    await waitUntil(`document.readyState==='complete'&&!!document.querySelector('#metric-total')&&document.querySelector('#metric-total').textContent!=='—'`, 'dashboard ready');
    await delay(250);
    const layout = await browser.evaluate(`({sidebarCount:document.querySelectorAll('.sidebar').length,navCount:document.querySelectorAll('.nav-item[data-view]').length,navRects:Array.from(document.querySelectorAll('.nav-item[data-view]')).map(n=>{const r=n.getBoundingClientRect();return{view:n.dataset.view,x:r.x,y:r.y,width:r.width,height:r.height}}),title:document.querySelector('h1').textContent,water:document.querySelector('#water-volume').textContent,total:document.querySelector('#metric-total').textContent,hasChart:!!document.querySelector('#water-chart svg')})`);
    assert.equal(layout.sidebarCount, 0, 'The sidebar must be removed from the DOM.');
    assert.equal(layout.navCount, 4);
    assert(layout.navRects.every(rect => rect.y >= 0 && rect.y < 250), 'Navigation must be placed in the header.');
    const overflow = await checkOverflow(`${name}/dashboard`);
    await browser.screenshot(join(evidence, `redesenho-${name}.png`));

    await click('[data-action="new-occurrence"]');
    await waitUntil(`document.querySelector('#occurrence-dialog').open`, 'occurrence dialog open');
    const modal = await browser.evaluate(`({open:document.querySelector('#occurrence-dialog').open,invalid:!document.querySelector('#occurrence-form').checkValidity(),maxLength:document.querySelector('#description').maxLength,dialogWidth:document.querySelector('#occurrence-dialog').getBoundingClientRect().width})`);
    assert(modal.invalid);
    assert.equal(modal.maxLength, 600);
    assert(modal.dialogWidth <= width);
    await click('#submit-occurrence');
    assert(await browser.evaluate(`document.querySelector('#occurrence-dialog').open`));
    await browser.evaluate(`document.querySelector('#category').value='buraco';document.querySelector('#region').value='Centro';document.querySelector('#description').value='Exemplo sintético de verificação visual, sem envio.'`);
    assert(await browser.evaluate(`document.querySelector('#occurrence-form').checkValidity()`));
    await click('#close-dialog');
    await browser.evaluate(`document.querySelector('#occurrence-form').reset()`);

    await navigate('ocorrencias');
    await waitUntil(`document.querySelector('#list-count').textContent!=='Carregando…'`, 'occurrences loaded');
    const eventStart = browser.events.length;
    await browser.evaluate(`document.querySelector('#filter-category').value='iluminacao';document.querySelector('#filter-region').value='Zona Norte';document.querySelector('#filter-status').value='';document.querySelector('#filters').requestSubmit()`);
    let filterResponse;
    for (let attempt = 0; attempt < 60; attempt++) {
      filterResponse = browser.events.slice(eventStart).find(event => event.method === 'Network.responseReceived' && event.params.response.url.includes('/api/occurrences?') && event.params.response.url.includes('category=iluminacao') && event.params.response.url.includes('region=Zona'));
      if (filterResponse) break;
      await delay(100);
    }
    assert(filterResponse, 'Filter request was not sent.');
    assert.equal(filterResponse.params.response.status, 200);
    await delay(150);
    const filterData = JSON.parse((await browser.send('Network.getResponseBody', { requestId: filterResponse.params.requestId })).body);
    assert(filterData.items.every(item => item.category === 'iluminacao' && item.region === 'Zona Norte'));
    await checkOverflow(`${name}/occurrences`);
    await navigate('classificador');
    assert(await browser.evaluate(`!!document.querySelector('#image-file')&&!document.querySelector('#view-classificador').hidden`));
    await checkOverflow(`${name}/classifier`);
    await navigate('projeto');
    assert(await browser.evaluate(`!document.querySelector('#view-projeto').hidden`));
    await checkOverflow(`${name}/project`);
    await navigate('painel');
    report.viewports.push({ name, width, height, layout, overflow, modal: { ...modal, requiredValidationPassed: true, validInputAcceptedWithoutSaving: true }, navigation: ['painel', 'ocorrencias', 'classificador', 'projeto'], filters: { category: 'iluminacao', region: 'Zona Norte', status: 200, total: filterData.total, allRowsMatch: true } });
  }
  report.exceptions = browser.events.filter(event => event.method === 'Runtime.exceptionThrown').map(event => event.params.exceptionDetails.text);
  report.failedRequests = browser.events.filter(event => event.method === 'Network.loadingFailed').map(event => event.params.errorText);
  report.mutatingRequests = browser.events.filter(event => event.method === 'Network.requestWillBeSent' && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(event.params.request.method)).map(event => ({ method: event.params.request.method, url: event.params.request.url }));
  assert.equal(report.exceptions.length, 0);
  assert.equal(report.failedRequests.length, 0);
  assert.equal(report.mutatingRequests.length, 0);
  await writeFile(join(evidence, 'redesenho-qa.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  report.error = error.message;
  await browser.screenshot(join(evidence, 'redesenho-failure.png')).catch(() => {});
  await writeFile(join(evidence, 'redesenho-qa.json'), JSON.stringify(report, null, 2));
  throw error;
} finally { await browser.close(); }
