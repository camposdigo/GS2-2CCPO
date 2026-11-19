// Local QA with the user's already installed Chrome. No browser installation.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
export async function openQaBrowser({ url, width = 430, height = 1300, port = 9336, profile = 'browser-flutter-qa' }) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const chrome = process.env.CHROME_EXECUTABLE || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  const processHandle = spawn(chrome, ['--headless', '--disable-gpu', '--no-first-run', '--force-renderer-accessibility', `--remote-debugging-port=${port}`, `--user-data-dir=${join(root, 'data', profile)}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  let socket;
  try {
    let page;
    for (let attempt = 0; attempt < 80; attempt++) {
      try { page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(item => item.type === 'page'); if (page) break; } catch {}
      await delay(250);
    }
    if (!page) throw new Error('Chrome debugging endpoint not ready.');
    socket = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
    const pending = new Map();
    const events = [];
    let sequence = 0;
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const request = pending.get(message.id);
        if (!request) return;
        pending.delete(message.id);
        clearTimeout(request.timer);
        if (message.error) request.reject(new Error(message.error.message)); else request.resolve(message.result);
      } else events.push(message);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 20_000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send('Runtime.enable');
    await send('Network.enable');
    await send('Accessibility.enable');
    await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: true });
    await send('Page.navigate', { url });
    const tree = async () => (await send('Accessibility.getFullAXTree')).nodes;
    const labels = async () => (await tree()).map(node => ({ role: node.role?.value, name: node.name?.value })).filter(node => node.name);
    const tap = async (label, role) => {
      const nodes = (await tree()).filter(node => node.name?.value && node.backendDOMNodeId && (!role || node.role?.value === role));
      const node = nodes.find(item => item.name.value === label) || nodes.find(item => item.name.value.startsWith(label)) || nodes.find(item => item.name.value.includes(label));
      if (!node) throw new Error(`Accessible control not found: ${label} (${role || 'any role'})`);
      await send('DOM.scrollIntoViewIfNeeded', { backendNodeId: node.backendDOMNodeId }).catch(() => {});
      const { model } = await send('DOM.getBoxModel', { backendNodeId: node.backendDOMNodeId });
      const x = (model.content[0] + model.content[2] + model.content[4] + model.content[6]) / 4;
      const y = (model.content[1] + model.content[3] + model.content[5] + model.content[7]) / 4;
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
      await delay(400);
      return { label, role: node.role?.value, x, y };
    };
    const screenshot = async path => {
      await mkdir(dirname(path), { recursive: true });
      const result = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      await writeFile(path, Buffer.from(result.data, 'base64'));
    };
    const close = async () => {
      await send('Browser.close').catch(() => {});
      socket.close();
      for (let attempt = 0; attempt < 30 && processHandle.exitCode === null; attempt++) await delay(100);
      if (processHandle.exitCode === null) processHandle.kill();
    };
    return { send, evaluate, tree, labels, tap, screenshot, events, close };
  } catch (error) { if (socket) socket.close(); processHandle.kill(); throw error; }
}
