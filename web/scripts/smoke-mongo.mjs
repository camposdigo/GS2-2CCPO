import { spawn } from 'node:child_process';
import { mkdir, writeFile, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { createServer } from 'node:net';
import mongoose from 'mongoose';
import assert from 'node:assert/strict';

const root = fileURLToPath(new URL('../', import.meta.url));
const executable = process.env.MONGOD_EXECUTABLE || join(root, '.tools/mongodb/mongod.exe');
await access(executable).catch(() => { throw new Error('Baixe o MongoDB portátil: python scripts/fetch-mongodb-qa.py, ou configure MONGOD_EXECUTABLE.'); });
const evidence = join(root, 'evidence');
const dataPath = join(root, 'data/mongo-qa');
await Promise.all([mkdir(evidence, { recursive: true }), mkdir(dataPath, { recursive: true })]);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const freePort = () => new Promise(resolve => { const server = createServer(); server.listen(0, '127.0.0.1', () => { const port = server.address().port; server.close(() => resolve(port)); }); });
const mongoPort = await freePort();
const webPort = await freePort();
const database = `territorio_vivo_qa_${Date.now()}`;
const uri = `mongodb://127.0.0.1:${mongoPort}/${database}`;
const baseUrl = `http://127.0.0.1:${webPort}`;
let mongo;
let web;

async function startMongo() {
  mongo = spawn(executable, ['--bind_ip', '127.0.0.1', '--port', String(mongoPort), '--dbpath', dataPath, '--logpath', join(evidence, 'mongo-smoke.log'), '--logappend'], { windowsHide: true, stdio: 'ignore' });
  for (let attempt = 0; attempt < 60; attempt++) {
    const connection = mongoose.createConnection(uri, { serverSelectionTimeoutMS: 400, bufferCommands: false });
    connection.on('error', () => {});
    try { await connection.asPromise(); await connection.close(); return; }
    catch { await connection.close(); if (mongo.exitCode !== null) throw new Error(`mongod exited ${mongo.exitCode}. See evidence/mongo-smoke.log`); await delay(200); }
  }
  throw new Error('MongoDB did not become ready.');
}
async function stopMongo() {
  if (!mongo || mongo.exitCode !== null) return;
  const connection = await mongoose.createConnection(uri, { serverSelectionTimeoutMS: 2000 }).asPromise();
  try { await connection.db.admin().command({ shutdown: 1, force: true, timeoutSecs: 2 }); } catch {}
  await connection.close().catch(() => {});
  for (let attempt = 0; attempt < 40 && mongo.exitCode === null; attempt++) await delay(200);
  if (mongo.exitCode === null) mongo.kill();
}
async function startWeb() {
  web = spawn(process.execPath, ['src/server.js'], { cwd: root, env: { ...process.env, DEMO_MODE: 'false', MONGO_URI: uri, PORT: String(webPort) }, windowsHide: true, stdio: 'ignore' });
  for (let attempt = 0; attempt < 60; attempt++) {
    try { const result = await fetch(`${baseUrl}/api/health`); const health = await result.json(); if (result.ok && health.storage.mode === 'mongodb') return; } catch {}
    if (web.exitCode !== null) throw new Error(`Web exited ${web.exitCode}`);
    await delay(200);
  }
  throw new Error('Web did not become ready.');
}
async function stopWeb() {
  if (!web || web.exitCode !== null) return;
  web.kill();
  for (let attempt = 0; attempt < 40 && web.exitCode === null; attempt++) await delay(100);
}
try {
  await startMongo();
  await startWeb();
  const response = await fetch(`${baseUrl}/api/occurrences`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: 'acessibilidade', region: 'Zona Norte', description: 'Teste sintético de integração: barreira na circulação de pedestres.' }) });
  assert.equal(response.status, 201);
  const created = await response.json();
  assert.equal(created.dataMode, 'mongodb');
  const firstList = await (await fetch(`${baseUrl}/api/occurrences`)).json();
  assert.equal(firstList.total, 1);
  assert.equal(firstList.items[0].id, created.item.id);
  // Stop the API and database, then read the same document from both restarted processes.
  await stopWeb();
  await stopMongo();
  await startMongo();
  await startWeb();
  const restarted = await (await fetch(`${baseUrl}/api/occurrences?category=acessibilidade&region=Zona%20Norte`)).json();
  assert.equal(restarted.dataMode, 'mongodb');
  assert.equal(restarted.total, 1);
  assert.equal(restarted.items[0].id, created.item.id);
  const connection = await mongoose.createConnection(uri).asPromise();
  const actualCount = await connection.collection('occurrences').countDocuments({ id: created.item.id });
  assert.equal(actualCount, 1);
  await connection.dropDatabase();
  await connection.close();
  const report = { generatedAt: new Date().toISOString(), mongoVersion: '8.2.12', mode: 'mongodb', createdStatus: 201, protocol: created.item.protocol, sameIdAfterApiAndDatabaseRestart: true, directDatabaseDocumentCount: actualCount, testDatabaseRemovedAfterCheck: true, globalServiceInstalled: false, bindAddress: '127.0.0.1' };
  await writeFile(join(evidence, 'mongo-smoke.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { await stopWeb(); await stopMongo(); }
