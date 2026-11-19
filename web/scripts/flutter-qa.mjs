// Requires the already-built Flutter web app at localhost:5000 and API at :3000.
// Run only after both services are ready. Pass --inspect for a read-only capture.
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { openQaBrowser, delay } from './cdp.mjs';

const evidence = fileURLToPath(new URL('../../mobile/evidence/', import.meta.url));
await mkdir(evidence, { recursive: true });
const readOnly = process.argv.includes('--inspect');
const reportFile = join(evidence, readOnly ? 'flutter-web-capture.json' : 'flutter-web-qa.json');
const browser = await openQaBrowser({ url: 'http://localhost:5000' });
const report = { generatedAt: new Date().toISOString(), client: 'Flutter web in existing local Chrome', api: 'http://localhost:3000', readOnly, steps: [] };
try {
  for (let attempt = 0; attempt < 80; attempt++) {
    if (browser.events.some(event => event.method === 'Network.responseReceived' && event.params.response.url.endsWith('/api/dashboard') && event.params.response.status === 200)) break;
    await delay(250);
  }
  await delay(1000);
  await browser.evaluate(`document.querySelector('flt-semantics-placeholder')?.click()`);
  await delay(800);
  report.initialLabels = await browser.labels();
  const dashboardEvent = browser.events.find(event => event.method === 'Network.responseReceived' && event.params.response.url.endsWith('/api/dashboard') && event.params.response.status === 200);
  assert(dashboardEvent, 'Dashboard não foi carregado da API.');
  const dashboard = JSON.parse((await browser.send('Network.getResponseBody', { requestId: dashboardEvent.params.requestId })).body);
  assert.equal(dashboard.water.dataMode, 'real');
  const volume = dashboard.water.metrics.volumePct.toFixed(2);
  assert(report.initialLabels.some(item => item.name.includes(volume) || item.name.includes(volume.replace('.', ','))), 'Volume real não encontrado na semântica Flutter.');
  report.steps.push({ action: 'dashboard', realVolumeVisible: true, volumePct: dashboard.water.metrics.volumePct, observedAt: dashboard.water.observedAt });
  await browser.screenshot(join(evidence, 'flutter-web.png'));
  if (!readOnly) {
    await browser.tap('Alertas');
    const alertLabels = await browser.labels();
    assert(alertLabels.some(item => item.name.includes('Alertas com contexto')));
    report.steps.push({ action: 'alerts', visible: true, labels: alertLabels });
    await browser.screenshot(join(evidence, 'flutter-alerts.png'));
    await browser.tap('Ocorrências');
    await delay(800);
    const occurrenceLabels = await browser.labels();
    assert(occurrenceLabels.some(item => item.name.includes('TV-')));
    report.steps.push({ action: 'occurrences', apiRowsVisible: true });
    await browser.tap('Preferências');
    await browser.tap('Região favorita');
    await browser.tap('Zona Norte');
    await browser.tap('Salvar preferência');
    const preferences = await browser.evaluate(`Object.fromEntries(Object.entries(localStorage).filter(([key])=>key.includes('favoriteRegion')))`);
    assert(JSON.stringify(preferences).includes('Zona Norte'));
    await browser.send('Page.reload');
    await delay(2500);
    await browser.evaluate(`document.querySelector('flt-semantics-placeholder')?.click()`);
    await delay(500);
    assert((await browser.labels()).some(item => item.name.includes('Sua região: Zona Norte')));
    report.steps.push({ action: 'favorite-region-reload', value: 'Zona Norte', persisted: true, storageKeys: Object.keys(preferences) });
    await browser.tap('Ocorrências');
    await delay(600);
    await browser.tap('Registrar ocorrência');
    await browser.tap('O que está acontecendo?');
    await browser.send('Input.insertText', { text: 'Exemplo sintético de QA Flutter: irregularidade no pavimento dificulta a passagem.' });
    await browser.tap('Enviar ocorrência');
    await delay(1500);
    const createdEvent = browser.events.find(event => event.method === 'Network.responseReceived' && event.params.response.url.endsWith('/api/occurrences') && event.params.response.status === 201);
    assert(createdEvent, 'O formulário Flutter não produziu HTTP201.');
    const createdBody = JSON.parse((await browser.send('Network.getResponseBody', { requestId: createdEvent.params.requestId })).body);
    assert.equal(createdBody.dataMode, 'demo');
    assert.equal(createdBody.item.region, 'Zona Norte');
    assert((await browser.labels()).some(item => item.name.includes(createdBody.item.protocol)));
    report.steps.push({ action: 'create-occurrence-through-flutter-form', status: 201, dataMode: 'demo', protocol: createdBody.item.protocol, region: createdBody.item.region, listedAfterCreate: true });
    await browser.screenshot(join(evidence, 'flutter-occurrences.png'));
    await browser.tap('Painel');
    await delay(500);
    await browser.screenshot(join(evidence, 'flutter-web.png'));
  }
  report.apiRequests = browser.events.filter(event => event.method === 'Network.requestWillBeSent' && event.params.request.url.includes(':3000/api/')).map(event => ({ method: event.params.request.method, url: event.params.request.url, postData: event.params.request.postData }));
  report.apiResponses = browser.events.filter(event => event.method === 'Network.responseReceived' && event.params.response.url.includes(':3000/api/')).map(event => ({ url: event.params.response.url, status: event.params.response.status }));
  report.exceptions = browser.events.filter(event => event.method === 'Runtime.exceptionThrown').map(event => event.params.exceptionDetails.text);
  report.failedRequests = browser.events.filter(event => event.method === 'Network.loadingFailed').map(event => ({ error: event.params.errorText, cors: event.params.corsErrorStatus }));
  assert.equal(report.exceptions.length, 0);
  await writeFile(reportFile, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  report.error = error.message;
  report.finalLabels = await browser.labels().catch(() => []);
  await browser.screenshot(join(evidence, 'flutter-failure.png')).catch(() => {});
  await writeFile(reportFile, JSON.stringify(report, null, 2));
  throw error;
} finally { await browser.close(); }
