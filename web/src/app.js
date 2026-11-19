import express from 'express';
import helmet from 'helmet';
import { rateLimit } from 'express-rate-limit';
import multer from 'multer';
import { z } from 'zod';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { occurrenceInput, occurrenceQuery, ServiceUnavailable } from './domain.js';

const publicPath = fileURLToPath(new URL('../public', import.meta.url));
const defaultWaterPath = fileURLToPath(new URL('../../modules/water/artifacts/dashboard.json', import.meta.url));
const finite = z.number().finite();
const waterSchema = z.object({
  schemaVersion: z.literal(1),
  dataMode: z.enum(['real', 'unavailable']),
  source: z.object({ name: z.string(), url: z.url() }).passthrough(),
  generatedAt: z.string(),
  observedAt: z.iso.date().nullable(),
  metrics: z.object({ volumePct: finite.min(0).max(100).optional() }).passthrough(),
  series: z.array(z.object({ date: z.iso.date(), observed: finite.nullable(), forecast: finite.nullable(), lower: finite.nullable(), upper: finite.nullable() })),
  alerts: z.array(z.object({ level: z.enum(['info', 'warning', 'critical']), title: z.string(), justification: z.string(), limitations: z.array(z.string()), requiresHumanReview: z.literal(true) }).passthrough()),
  freshness: z.object({ maxAgeDays: finite.min(0).optional() }).passthrough().optional()
}).passthrough().refine(value => value.dataMode !== 'real' || (value.observedAt && Number.isFinite(value.metrics.volumePct)));
const probability = z.object({ className: z.string(), label: z.string(), score: finite.min(0).max(1) });
const classificationSchema = z.object({
  dataMode: z.literal('trained_model'),
  prediction: probability,
  probabilities: z.array(probability),
  requiresHumanReview: z.literal(true)
}).passthrough();

export async function readWaterArtifact(path) {
  try {
    const artifact = waterSchema.parse(JSON.parse(await readFile(path, 'utf8')));
    if (artifact.dataMode === 'real') {
      const asOfDate = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
      const ageDays = Math.floor((Date.parse(`${asOfDate}T00:00:00Z`) - Date.parse(`${artifact.observedAt}T00:00:00Z`)) / 86_400_000);
      if (ageDays < 0) throw new Error('future observation');
      artifact.freshness = { ...artifact.freshness, asOfDate, ageDays, status: ageDays <= (artifact.freshness?.maxAgeDays ?? 2) ? 'current' : 'stale' };
      if (artifact.forecast && typeof artifact.forecast === 'object') {
        artifact.forecast.expired = artifact.freshness.status !== 'current' || (typeof artifact.forecast.usableUntil === 'string' && artifact.forecast.usableUntil < asOfDate);
      }
    }
    return artifact;
  } catch {
    return { dataMode: 'unavailable', source: 'modules/water/artifacts/dashboard.json', message: 'Execute o módulo hídrico para gerar os indicadores. Nenhum valor foi estimado pelo painel.', metrics: null, alerts: [] };
  }
}

function isSupportedImage(buffer, mime) {
  if (mime === 'image/jpeg') return buffer.length > 3 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff;
  if (mime === 'image/png') return buffer.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
  return false;
}

export function createApp({ store, waterPath = defaultWaterPath, classifierUrl = 'http://127.0.0.1:8001', fetchImpl = fetch, rateLimiting = true, corsOrigins = '' } = {}) {
  if (!store) throw new Error('A storage adapter is required.');
  const allowedOrigins = new Set(corsOrigins.split(',').map(value => value.trim()).filter(Boolean));
  for (const origin of allowedOrigins) {
    const parsed = new URL(origin);
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== origin) throw new Error('CORS_ORIGINS deve conter origens HTTP(S) exatas, sem caminho, credenciais ou wildcard.');
  }
  const app = express();
  app.disable('x-powered-by');
  app.set('query parser', 'simple');
  app.use(helmet({ contentSecurityPolicy: { directives: { imgSrc: ["'self'", 'data:', 'blob:'], upgradeInsecureRequests: null } } }));
  app.use('/api', (req, res, next) => {
    const origin = req.get('Origin');
    if (!origin) return next();
    res.vary('Origin');
    const sameOrigin = `${req.protocol}://${req.get('host')}`;
    if (origin !== sameOrigin && !allowedOrigins.has(origin)) return res.status(403).json({ error: { code: 'ORIGIN_NOT_ALLOWED', message: 'Origem não autorizada para esta API.' } });
    res.set('Access-Control-Allow-Origin', origin);
    if (req.method !== 'OPTIONS') return next();
    const method = req.get('Access-Control-Request-Method');
    const headers = (req.get('Access-Control-Request-Headers') || '').toLowerCase().split(',').map(value => value.trim()).filter(Boolean);
    if (!['GET', 'POST'].includes(method) || headers.some(header => header !== 'content-type')) return res.status(403).json({ error: { code: 'PREFLIGHT_NOT_ALLOWED', message: 'Método ou cabeçalho não autorizado.' } });
    res.set('Access-Control-Allow-Methods', 'GET, POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.set('Access-Control-Max-Age', '600');
    return res.status(204).end();
  });
  app.use(express.json({ limit: '12kb', strict: true }));
  if (rateLimiting) app.use('/api', rateLimit({ windowMs: 60_000, limit: 100, standardHeaders: 'draft-8', legacyHeaders: false, message: { error: { code: 'RATE_LIMITED', message: 'Muitas solicitações. Aguarde um minuto.' } } }));
  app.use('/api', (_req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });

  app.get('/api/health', (_req, res) => res.status(store.available() ? 200 : 503).json({
    status: store.available() ? 'ok' : 'unavailable',
    storage: { mode: store.mode, available: store.available() },
    classifier: { urlConfigured: Boolean(classifierUrl) }
  }));

  app.get('/api/dashboard', async (_req, res) => {
    const [occurrences, water] = await Promise.all([store.summary(), readWaterArtifact(waterPath)]);
    res.json({ occurrences, water, dataMode: store.mode });
  });
  app.get('/api/occurrences', async (req, res) => {
    const result = occurrenceQuery.safeParse(req.query);
    if (!result.success) return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Filtros inválidos.', fields: result.error.issues.map(issue => ({ field: issue.path.join('.'), message: issue.message })) } });
    const { page, limit } = result.data;
    res.json({ ...await store.list(result.data), page, limit, dataMode: store.mode });
  });
  if (rateLimiting) app.post('/api/occurrences', rateLimit({ windowMs: 600_000, limit: 10, standardHeaders: 'draft-8', legacyHeaders: false, message: { error: { code: 'RATE_LIMITED', message: 'Limite de registros atingido. Tente novamente mais tarde.' } } }));
  app.post('/api/occurrences', async (req, res) => {
    if (!req.is('application/json')) return res.status(415).json({ error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: 'Envie JSON.' } });
    const result = occurrenceInput.safeParse(req.body);
    if (!result.success) return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'Confira os campos informados.', fields: result.error.issues.map(issue => ({ field: issue.path.join('.'), message: issue.message })) } });
    res.status(201).json({ item: await store.create(result.data), dataMode: store.mode });
  });

  const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024, files: 1, fields: 0, parts: 1 }, fileFilter: (_req, file, cb) => {
    if (!['image/png', 'image/jpeg'].includes(file.mimetype)) { const error = new Error('Use PNG ou JPEG.'); error.status = 415; return cb(error); }
    cb(null, true);
  } });
  app.post('/api/classify', upload.single('file'), async (req, res) => {
    if (!req.file) return res.status(400).json({ error: { code: 'IMAGE_REQUIRED', message: 'Selecione uma imagem no campo file.' } });
    if (!isSupportedImage(req.file.buffer, req.file.mimetype)) return res.status(415).json({ error: { code: 'INVALID_IMAGE', message: 'O conteúdo não corresponde a uma imagem PNG ou JPEG.' } });
    try {
      const body = new FormData();
      body.append('file', new Blob([req.file.buffer], { type: req.file.mimetype }), 'image');
      const upstream = await fetchImpl(`${classifierUrl.replace(/\/$/, '')}/api/classify`, { method: 'POST', body, signal: AbortSignal.timeout(15_000) });
      const result = await upstream.json();
      if (!upstream.ok) return res.status(upstream.status >= 500 ? 503 : 422).json({ error: { code: 'CLASSIFIER_UNAVAILABLE', message: 'Classificador indisponível ou modelo ainda não treinado. Execute o módulo de visão computacional.' } });
      const valid = classificationSchema.safeParse(result);
      if (!valid.success) return res.status(503).json({ error: { code: 'CLASSIFIER_INVALID_RESPONSE', message: 'O modelo não forneceu um resultado válido. Nenhuma classificação foi produzida.' } });
      res.json(valid.data);
    } catch {
      res.status(503).json({ error: { code: 'CLASSIFIER_UNAVAILABLE', message: 'Classificador indisponível ou treinamento pendente. Nenhuma classificação foi produzida.' } });
    }
  });

  app.use('/api', (_req, res) => res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Rota não encontrada.' } }));
  app.use(express.static(publicPath, { dotfiles: 'deny', index: 'index.html' }));
  app.use((error, _req, res, _next) => {
    if (error instanceof ServiceUnavailable) return res.status(503).json({ error: { code: 'STORAGE_UNAVAILABLE', message: error.message } });
    if (error instanceof multer.MulterError) return res.status(error.code === 'LIMIT_FILE_SIZE' ? 413 : 400).json({ error: { code: error.code, message: error.code === 'LIMIT_FILE_SIZE' ? 'A imagem deve ter até 5 MB.' : 'Envie somente uma imagem, no campo file.' } });
    if (error.type === 'entity.too.large') return res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'Requisição acima do tamanho permitido.' } });
    if (error.type === 'entity.parse.failed') return res.status(400).json({ error: { code: 'INVALID_JSON', message: 'JSON inválido.' } });
    if (error.status === 415) return res.status(415).json({ error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: 'Use uma imagem PNG ou JPEG.' } });
    res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Não foi possível concluir a operação.' } });
  });
  return app;
}
