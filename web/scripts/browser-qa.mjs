import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const evidence = join(root, 'evidence');
await mkdir(evidence, { recursive: true });
const chrome = process.env.CHROME_EXECUTABLE || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const browser = spawn(chrome, ['--headless', '--disable-gpu', '--no-first-run', '--remote-debugging-port=9334', `--user-data-dir=${join(root, 'data/browser-cdp-qa')}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
let socket;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  let pages;
  for (let attempt = 0; attempt < 60; attempt++) {
    try { pages = await (await fetch('http://127.0.0.1:9334/json/list')).json(); if (pages.some(page => page.type === 'page')) break; } catch {}
    await delay(250);
  }
  const page = pages?.find(item => item.type === 'page');
  if (!page) throw new Error('Chrome debugging endpoint not ready.');
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  let next = 0;
  const requests = new Map();
  const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id && requests.has(message.id)) {
      const pending = requests.get(message.id); requests.delete(message.id);
      if (message.error) pending.reject(new Error(message.error.message)); else pending.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++next; requests.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
  const evaluate = async expression => (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result.value;
  await send('Runtime.enable');
  await send('Page.enable');
  const checks = [];
  for (const [name, width, height] of [['desktop', 1440, 1550], ['mobile', 390, 1350]]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: name === 'mobile' });
    await send('Page.navigate', { url: process.env.QA_BASE_URL || 'http://localhost:3000' });
    await delay(2000);
    const result = await evaluate(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,total:document.querySelector('#metric-total').textContent,water:document.querySelector('#water-volume').textContent,hasChart:!!document.querySelector('#water-chart svg'),overflow:Array.from(document.querySelectorAll('body *')).filter(n=>{const r=n.getBoundingClientRect();return r.right>innerWidth+1&&r.width>0}).slice(0,8).map(n=>({tag:n.tagName,class:n.className,width:n.getBoundingClientRect().width}))})`);
    checks.push({ viewport: name, ...result });
    if (result.scrollWidth > result.width) throw new Error(`${name}: horizontal overflow ${JSON.stringify(result)}`);
    const screenshot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    await writeFile(join(evidence, `painel-${name}.png`), Buffer.from(screenshot.data, 'base64'));
  }
  await evaluate(`document.querySelector('[data-action="new-occurrence"]').click()`);
  const modal = await evaluate(`({open:document.querySelector('#occurrence-dialog').open,hasRegion:!!document.querySelector('#region'),descriptionMax:document.querySelector('#description').maxLength})`);
  if (!modal.open || modal.descriptionMax !== 600) throw new Error('Occurrence modal failed.');
  await evaluate(`document.querySelector('#close-dialog').click();location.hash='ocorrencias'`);
  await delay(800);
  const navigation = await evaluate(`({visible:!document.querySelector('#view-ocorrencias').hidden,count:document.querySelectorAll('#occurrences-list .occurrence-row').length})`);
  if (!navigation.visible) throw new Error('Navigation failed.');
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  const report = { generatedAt: new Date().toISOString(), browser: 'Existing local Google Chrome headless via CDP', checks, modal, navigation, errors };
  await writeFile(join(evidence, 'browser-qa.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (socket) socket.close();
  browser.kill();
}
