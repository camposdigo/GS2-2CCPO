import { fileURLToPath } from 'node:url';
import { createApp } from './app.js';
import { createDemoStore, createMongoStore } from './storage.js';

const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT inválida.');
const demo = process.env.DEMO_MODE === 'true';
const store = demo
  ? await createDemoStore(fileURLToPath(new URL('../data/demo.json', import.meta.url)))
  : await createMongoStore(process.env.MONGO_URI);
if (demo) console.log('DEMONSTRAÇÃO EXPLÍCITA: dados sintéticos e persistência JSON. Não utiliza MongoDB.');
else if (!store.available()) console.error('MongoDB indisponível: configure MONGO_URI e reinicie. APIs de dados retornarão 503.');
const app = createApp({ store, classifierUrl: process.env.CLASSIFIER_URL || 'http://127.0.0.1:8001', corsOrigins: process.env.CORS_ORIGINS || '' });
const server = app.listen(port, '0.0.0.0', () => console.log(`Território Vivo: http://localhost:${port} | persistência: ${store.mode}`));
async function shutdown() { server.close(async () => { await store.close(); process.exit(0); }); }
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
