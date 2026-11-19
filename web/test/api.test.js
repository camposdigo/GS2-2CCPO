import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { createDemoStore, createMongoStore } from '../src/storage.js';

const valid = { category: 'buraco', region: 'Centro', description: 'Irregularidade no pavimento dificulta a passagem de pedestres.' };
async function fixture(t, options = {}) {
  const dir = await mkdtemp(join(tmpdir(), 'territorio-vivo-web-'));
  const path = join(dir, 'demo.json');
  const store = await createDemoStore(path, { seed: false });
  t.after(async () => { await store.close(); await rm(dir, { recursive: true, force: true }); });
  return { app: createApp({ store, waterPath: join(dir, 'water.json'), rateLimiting: false, ...options }), dir, path, store };
}

test('registra, filtra, pagina e mantém a ocorrência ao reabrir a persistência demo', async t => {
  const { app, path } = await fixture(t);
  const created = await request(app).post('/api/occurrences').send(valid).expect(201);
  assert.equal(created.body.dataMode, 'demo');
  assert.equal(created.body.item.status, 'recebida');
  assert.match(created.body.item.protocol, /^TV-/);
  const reopened = await createDemoStore(path, { seed: false });
  const records = await reopened.list({ page: 1, limit: 10 });
  assert.equal(records.total, 1);
  assert.equal(records.items[0].description, valid.description);
  const filtered = await request(app).get('/api/occurrences?category=buraco&region=Centro&limit=1&page=1').expect(200);
  assert.equal(filtered.body.total, 1);
  const absent = await request(app).get('/api/occurrences?category=residuos').expect(200);
  assert.equal(absent.body.total, 0);
  const dashboard = await request(app).get('/api/dashboard').expect(200);
  assert.equal(dashboard.body.occurrences.total, 1);
  assert.equal(dashboard.body.occurrences.byCategory.buraco, 1);
  assert.equal(dashboard.body.water.dataMode, 'unavailable');
});

test('escritas concorrentes não perdem registros', async t => {
  const { store, path } = await fixture(t);
  await Promise.all(Array.from({ length: 12 }, () => store.create(valid)));
  const records = JSON.parse(await readFile(path, 'utf8'));
  assert.equal(records.length, 12);
  assert.equal(new Set(records.map(row => row.id)).size, 12);
});

test('valida campos, rejeita alteração de status e dados de contato', async t => {
  const { app } = await fixture(t);
  for (const payload of [
    { ...valid, category: 'other' }, { ...valid, region: 'Rua exata, 123' },
    { ...valid, status: 'resolvida' }, { ...valid, email: 'pessoa@example.org' },
    { ...valid, description: 'Descrição com contato pessoa@example.org' },
    { ...valid, description: 'Entre em contato pelo (11) 99999-1234' },
    { ...valid, description: 'curta' }, { ...valid, description: 'a'.repeat(601) },
    { ...valid, category: { $ne: null } }
  ]) await request(app).post('/api/occurrences').send(payload).expect(400);
  await request(app).patch('/api/occurrences/anything').send({ status: 'resolvida' }).expect(404);
  await request(app).post('/api/occurrences').set('Content-Type', 'text/plain').send('test').expect(415);
  await request(app).post('/api/occurrences').set('Content-Type', 'application/json').send('{broken').expect(400);
  await request(app).post('/api/occurrences').send({ ...valid, description: 'a'.repeat(20_000) }).expect(413);
});

test('filtros inválidos e operadores de consulta não chegam ao banco', async t => {
  const { app } = await fixture(t);
  for (const query of ['limit=1001', 'page=0', 'limit=not-a-number', 'category[$ne]=x', 'category=buraco&category=residuos', 'unknown=x', 'status=invalid', 'region=invalid'])
    await request(app).get(`/api/occurrences?${query}`).expect(400);
});

test('texto potencialmente malicioso é JSON literal e página usa CSP', async t => {
  const { app } = await fixture(t);
  const description = '<img src=x onerror=alert(1)> problema de pavimentação.';
  const result = await request(app).post('/api/occurrences').send({ ...valid, description }).expect(201);
  assert.equal(result.body.item.description, description);
  assert.match(result.headers['content-type'], /application\/json/);
  const page = await request(app).get('/').expect(200);
  assert.match(page.headers['content-security-policy'], /script-src 'self'/);
  assert.doesNotMatch(page.text, /onerror=/);
  const script = await request(app).get('/app.js').expect(200);
  assert.doesNotMatch(script.text, /innerHTML|insertAdjacentHTML|document\.write/);
});

test('Mongo não configurado retorna 503, nunca usa demo e não expõe segredos', async () => {
  const store = await createMongoStore(undefined);
  const app = createApp({ store, rateLimiting: false });
  const health = await request(app).get('/api/health').expect(503);
  assert.equal(health.body.storage.mode, 'mongodb');
  assert.equal(health.body.storage.available, false);
  for (const endpoint of ['/api/occurrences', '/api/dashboard']) {
    const result = await request(app).get(endpoint).expect(503);
    assert.equal(result.body.error.code, 'STORAGE_UNAVAILABLE');
    assert.equal(result.body.stack, undefined);
  }
  await request(app).post('/api/occurrences').send(valid).expect(503);
});

test('falha real de conexão Mongo não resulta em fallback', async t => {
  const store = await createMongoStore('mongodb://127.0.0.1:1/test', { serverSelectionTimeoutMS: 100 });
  t.after(() => store.close());
  const app = createApp({ store, rateLimiting: false });
  const result = await request(app).get('/api/occurrences').expect(503);
  assert.equal(result.body.error.code, 'STORAGE_UNAVAILABLE');
  assert.equal(store.mode, 'mongodb');
});

test('artefato hídrico válido preserva fonte e recalcula obsolescência', async t => {
  const { app, dir } = await fixture(t);
  await writeFile(join(dir, 'water.json'), JSON.stringify({
    schemaVersion: 1, dataMode: 'real', generatedAt: '2020-01-02T00:00:00Z', observedAt: '2020-01-01',
    source: { name: 'Fonte oficial de teste', url: 'https://example.org/' }, freshness: { status: 'current', maxAgeDays: 2 },
    metrics: { volumePct: 50 }, series: [{ date: '2020-01-01', observed: 50, forecast: null, lower: null, upper: null }], alerts: [],
    forecast: { expired: false, usableUntil: '2020-01-03', valuePct: 51 }
  }));
  const result = await request(app).get('/api/dashboard').expect(200);
  assert.equal(result.body.water.metrics.volumePct, 50);
  assert.equal(result.body.water.freshness.status, 'stale');
  assert.equal(result.body.water.forecast.expired, true);
  assert.equal(result.body.water.source.name, 'Fonte oficial de teste');
  await writeFile(join(dir, 'water.json'), JSON.stringify({ dataMode: 'real', source: 'fake', metrics: { volumePct: 'inventado' } }));
  const invalid = await request(app).get('/api/dashboard').expect(200);
  assert.equal(invalid.body.water.dataMode, 'unavailable');
});

const png = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 1]);
test('upload exige arquivo real com assinatura aceita e limita tamanho', async t => {
  const { app } = await fixture(t);
  await request(app).post('/api/classify').expect(400);
  await request(app).post('/api/classify').attach('file', Buffer.from('not an image'), { filename: 'x.png', contentType: 'image/png' }).expect(415);
  await request(app).post('/api/classify').attach('file', Buffer.from('text'), { filename: 'x.txt', contentType: 'text/plain' }).expect(415);
  await request(app).post('/api/classify').attach('file', Buffer.from('RIFF0000WEBP'), { filename: 'x.webp', contentType: 'image/webp' }).expect(415);
  await request(app).post('/api/classify').attach('file', Buffer.concat([png, Buffer.alloc(5 * 1024 * 1024)]), { filename: 'large.png', contentType: 'image/png' }).expect(413);
});

test('modelo indisponível não gera classificação fictícia', async t => {
  const { app } = await fixture(t, { fetchImpl: async () => { throw new Error('offline'); } });
  const result = await request(app).post('/api/classify').attach('file', png, { filename: 'x.png', contentType: 'image/png' }).expect(503);
  assert.equal(result.body.error.code, 'CLASSIFIER_UNAVAILABLE');
  assert.equal(result.body.prediction, undefined);
});

test('proxy aceita somente contrato de resultado treinado e valida resposta', async t => {
  let validResponse = true;
  const prediction = { className: 'buraco', label: 'Buraco e pavimento', score: .75 };
  const { app } = await fixture(t, { fetchImpl: async (_url, options) => {
    assert.equal(options.body.get('file').type, 'image/png');
    return { ok: true, json: async () => validResponse ? { dataMode: 'trained_model', prediction, probabilities: [prediction], requiresHumanReview: true } : { prediction: { label: 'inventado' } } };
  } });
  const result = await request(app).post('/api/classify').attach('file', png, { filename: 'x.png', contentType: 'image/png' }).expect(200);
  assert.equal(result.body.prediction.score, .75);
  validResponse = false;
  await request(app).post('/api/classify').attach('file', png, { filename: 'x.png', contentType: 'image/png' }).expect(503);
});

test('CORS permite apenas origens exatas configuradas, sem wildcard nem credenciais', async t => {
  const { app } = await fixture(t, { corsOrigins: 'http://localhost:5000,http://127.0.0.1:5000' });
  const allowed = await request(app).get('/api/health').set('Origin', 'http://localhost:5000').expect(200);
  assert.equal(allowed.headers['access-control-allow-origin'], 'http://localhost:5000');
  assert.equal(allowed.headers['access-control-allow-credentials'], undefined);
  assert.match(allowed.headers.vary, /Origin/);
  for (const origin of ['http://localhost:5001', 'http://localhost:5000.evil.example', 'null', 'https://evil.example']) {
    const denied = await request(app).get('/api/health').set('Origin', origin).expect(403);
    assert.equal(denied.headers['access-control-allow-origin'], undefined);
  }
  const preflight = await request(app).options('/api/occurrences').set('Origin', 'http://127.0.0.1:5000').set('Access-Control-Request-Method', 'POST').set('Access-Control-Request-Headers', 'content-type').expect(204);
  assert.equal(preflight.headers['access-control-allow-methods'], 'GET, POST');
  assert.equal(preflight.headers['access-control-allow-headers'], 'Content-Type');
  assert.equal(preflight.headers['access-control-allow-credentials'], undefined);
  await request(app).options('/api/occurrences').set('Origin', 'http://localhost:5000').set('Access-Control-Request-Method', 'PATCH').expect(403);
  await request(app).options('/api/occurrences').set('Origin', 'http://localhost:5000').set('Access-Control-Request-Method', 'POST').set('Access-Control-Request-Headers', 'authorization').expect(403);
});

test('CORS vazio mantém acesso sem Origin e mesma origem, rejeitando origem cruzada', async t => {
  const { app } = await fixture(t);
  await request(app).get('/api/health').expect(200);
  await request(app).get('/api/health').set('Host', 'localhost:3000').set('Origin', 'http://localhost:3000').expect(200);
  await request(app).get('/api/health').set('Origin', 'http://localhost:5000').expect(403);
});
