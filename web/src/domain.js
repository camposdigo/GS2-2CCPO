import { z } from 'zod';

export const categories = ['buraco', 'iluminacao', 'residuos', 'acessibilidade'];
export const statuses = ['recebida', 'em_analise', 'resolvida'];
export const regions = ['Centro', 'Zona Norte', 'Zona Sul', 'Zona Leste', 'Zona Oeste'];
const cleanText = z.string().trim().refine(value => !/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value), 'Remova caracteres de controle.');
export const occurrenceInput = z.object({
  category: z.enum(categories),
  region: z.enum(regions),
  description: cleanText.pipe(z.string().min(12, 'Descreva a situação com pelo menos 12 caracteres.').max(600))
    .refine(value => !/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(value), 'Não informe e-mail ou dados pessoais.')
    .refine(value => !/(?:\+?55\s*)?\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}/.test(value), 'Não informe telefone ou dados pessoais.')
}).strict();
export const occurrenceQuery = z.object({
  category: z.enum(categories).optional(),
  status: z.enum(statuses).optional(),
  region: z.enum(regions).optional(),
  page: z.coerce.number().int().min(1).max(10000).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20)
}).strict();

export function summarize(items) {
  const byCategory = Object.fromEntries(categories.map(category => [category, 0]));
  let resolved = 0;
  for (const item of items) {
    byCategory[item.category] = (byCategory[item.category] ?? 0) + 1;
    if (item.status === 'resolvida') resolved++;
  }
  return { total: items.length, open: items.length - resolved, resolved, byCategory };
}

export class ServiceUnavailable extends Error {
  constructor() { super('Persistência indisponível. Configure e inicie o MongoDB ou ative DEMO_MODE=true para demonstração.'); }
}
