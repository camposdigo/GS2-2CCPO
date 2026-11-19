import { mkdir, readFile, writeFile, rename } from 'node:fs/promises';
import { dirname } from 'node:path';
import { randomUUID } from 'node:crypto';
import mongoose from 'mongoose';
import { categories, statuses, regions, ServiceUnavailable, summarize } from './domain.js';

function makeItem(input) {
  const id = randomUUID();
  return { id, protocol: `TV-${id.slice(0, 8).toUpperCase()}`, ...input, status: 'recebida', createdAt: new Date().toISOString() };
}

export async function createDemoStore(filePath, { seed = true } = {}) {
  await mkdir(dirname(filePath), { recursive: true });
  let rows;
  try { rows = JSON.parse(await readFile(filePath, 'utf8')); }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    rows = seed ? [
      { ...makeItem({ category: 'iluminacao', region: 'Zona Norte', description: 'Exemplo sintético: iluminação pública intermitente em área de circulação.' }), status: 'em_analise' },
      makeItem({ category: 'residuos', region: 'Centro', description: 'Exemplo sintético: acúmulo de resíduos em área de uso coletivo.' }),
      { ...makeItem({ category: 'acessibilidade', region: 'Zona Sul', description: 'Exemplo sintético: barreira de acesso em passagem de pedestres.' }), status: 'resolvida' },
      makeItem({ category: 'buraco', region: 'Zona Leste', description: 'Exemplo sintético: irregularidade no pavimento dificulta a circulação.' })
    ] : [];
    await writeFile(filePath, JSON.stringify(rows, null, 2));
  }
  if (!Array.isArray(rows)) throw new Error('Arquivo de demonstração inválido.');
  // Serialize writes so simultaneous submissions cannot overwrite each other.
  let transaction = Promise.resolve();
  return {
    mode: 'demo', available: () => true,
    async create(input) {
      const item = makeItem(input);
      const pending = transaction.then(async () => {
        const next = [...rows, item];
        await writeFile(`${filePath}.tmp`, JSON.stringify(next, null, 2));
        await rename(`${filePath}.tmp`, filePath);
        rows = next;
        return item;
      });
      transaction = pending.catch(() => {});
      return pending;
    },
    async list(query) {
      const filtered = rows.filter(item => ['category', 'status', 'region'].every(key => !query[key] || query[key] === item[key]))
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      return { items: filtered.slice((query.page - 1) * query.limit, query.page * query.limit), total: filtered.length };
    },
    async summary() { return summarize(rows); },
    async close() {}
  };
}

export async function createMongoStore(uri, { serverSelectionTimeoutMS = 2500 } = {}) {
  if (!uri) return {
    mode: 'mongodb', available: () => false,
    async create() { throw new ServiceUnavailable(); },
    async list() { throw new ServiceUnavailable(); },
    async summary() { throw new ServiceUnavailable(); },
    async close() {}
  };
  const connection = mongoose.createConnection(uri, { serverSelectionTimeoutMS, bufferCommands: false });
  connection.on('error', () => {});
  try { await connection.asPromise(); } catch { /* APIs expose 503; never fall back to demo. */ }
  const schema = new mongoose.Schema({
    id: { type: String, required: true, unique: true },
    protocol: { type: String, required: true },
    category: { type: String, enum: categories, required: true },
    region: { type: String, enum: regions, required: true },
    description: { type: String, minlength: 12, maxlength: 600, required: true },
    status: { type: String, enum: statuses, default: 'recebida', required: true },
    createdAt: { type: Date, required: true }
  }, { versionKey: false, bufferCommands: false });
  schema.index({ category: 1, region: 1, createdAt: -1 });
  const Occurrence = connection.model('Occurrence', schema);
  const check = () => { if (connection.readyState !== 1) throw new ServiceUnavailable(); };
  const serialize = row => ({ id: row.id, protocol: row.protocol, category: row.category, region: row.region, description: row.description, status: row.status, createdAt: new Date(row.createdAt).toISOString() });
  return {
    mode: 'mongodb', available: () => connection.readyState === 1,
    async create(input) {
      check();
      try { return serialize((await Occurrence.create(makeItem(input))).toObject()); }
      catch { throw new ServiceUnavailable(); }
    },
    async list(query) {
      check();
      const filter = Object.fromEntries(['category', 'status', 'region'].filter(key => query[key]).map(key => [key, query[key]]));
      try {
        const [items, total] = await Promise.all([
          Occurrence.find(filter).select('-_id').sort({ createdAt: -1, id: 1 }).skip((query.page - 1) * query.limit).limit(query.limit).lean(),
          Occurrence.countDocuments(filter)
        ]);
        return { items: items.map(serialize), total };
      } catch { throw new ServiceUnavailable(); }
    },
    async summary() {
      check();
      try {
        const groups = await Occurrence.aggregate([{ $group: { _id: { category: '$category', status: '$status' }, count: { $sum: 1 } } }]);
        const summary = { total: 0, open: 0, resolved: 0, byCategory: Object.fromEntries(categories.map(category => [category, 0])) };
        for (const group of groups) {
          summary.total += group.count;
          summary.byCategory[group._id.category] += group.count;
          summary[group._id.status === 'resolvida' ? 'resolved' : 'open'] += group.count;
        }
        return summary;
      } catch { throw new ServiceUnavailable(); }
    },
    async close() { await connection.close(); }
  };
}
