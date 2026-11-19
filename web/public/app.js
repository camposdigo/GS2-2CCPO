const $ = selector => document.querySelector(selector);
const labels = { buraco: 'Buraco e pavimento', iluminacao: 'Iluminação pública', residuos: 'Resíduos', acessibilidade: 'Acessibilidade' };
const symbols = { buraco: '⌁', iluminacao: '☼', residuos: '♧', acessibilidade: '↗' };
const statusLabels = { recebida: 'Recebida', em_analise: 'Em análise', resolvida: 'Resolvida' };
const viewLabels = { painel: 'Visão geral', ocorrencias: 'Ocorrências', classificador: 'Análise de imagem', projeto: 'Sobre o projeto' };
let currentPage = 1;
let latestListRequest = 0;
let previewUrl;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function formatNumber(value, digits = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('pt-BR', { maximumFractionDigits: digits, minimumFractionDigits: digits }) : '—';
}
function formatDate(value, options = { day: '2-digit', month: 'short' }) {
  const date = new Date(value.length === 10 ? `${value}T12:00:00-03:00` : value);
  return Number.isNaN(date.getTime()) ? 'Data indisponível' : date.toLocaleDateString('pt-BR', { ...options, timeZone: 'America/Sao_Paulo' });
}
async function api(path, options) {
  const response = await fetch(path, options);
  let result;
  try { result = await response.json(); } catch { throw new Error('O servidor não retornou uma resposta válida.'); }
  if (!response.ok) {
    const fields = result.error?.fields?.map(field => field.message).join(' ');
    throw new Error(fields || result.error?.message || 'Não foi possível concluir a solicitação.');
  }
  return result;
}
function showView(view, focus = false) {
  if (!viewLabels[view]) view = 'painel';
  document.querySelectorAll('.view').forEach(section => { section.hidden = section.id !== `view-${view}`; });
  document.querySelectorAll('.nav-item').forEach(link => {
    const active = link.dataset.view === view;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  $('#breadcrumb-view').textContent = viewLabels[view];
  document.title = `${viewLabels[view]} · Território Vivo`;
  if (view === 'ocorrencias') loadOccurrences();
  if (focus) $('#main').focus({ preventScroll: true });
}
document.querySelectorAll('[data-view]').forEach(link => link.addEventListener('click', event => {
  event.preventDefault();
  const view = link.dataset.view;
  if (location.hash === `#${view}`) showView(view, true); else location.hash = view;
}));
window.addEventListener('hashchange', () => showView(location.hash.slice(1), true));
showView(location.hash.slice(1));
$('#today').textContent = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'America/Sao_Paulo' });

async function loadHealth() {
  const banner = $('#mode-banner');
  try {
    const response = await fetch('/api/health');
    const health = await response.json();
    banner.className = 'mode-banner';
    if (!health.storage.available) throw new Error('MongoDB indisponível. Configure MONGO_URI e inicie o banco para registrar e consultar ocorrências.');
    if (health.storage.mode === 'demo') {
      banner.classList.add('demo');
      banner.textContent = 'Modo demonstração · As ocorrências são exemplos sintéticos. A origem e a data dos indicadores de água aparecem no painel.';
    } else banner.textContent = 'Registros públicos por região. Participe sem informar dados pessoais e confira as fontes dos indicadores no painel.';
  } catch (error) {
    banner.className = 'mode-banner error';
    banner.textContent = error.message || 'Servidor indisponível. Inicie a API para carregar os dados.';
  }
}

function occurrenceRow(item, full = false) {
  const article = element('article', 'occurrence-row');
  const icon = element('span', 'occurrence-symbol', symbols[item.category] || '⌖');
  icon.setAttribute('aria-hidden', 'true');
  const main = element('div', 'occurrence-main');
  main.append(element('h3', '', labels[item.category] || 'Ocorrência'), element('p', '', `${item.region} · ${item.protocol} · ${formatDate(item.createdAt)}`));
  article.append(icon, main, element('span', `status ${item.status}`, statusLabels[item.status] || item.status));
  if (full) article.append(element('p', 'occurrence-description', item.description));
  return article;
}
async function loadRecent() {
  try {
    const result = await api('/api/occurrences?limit=4');
    $('#recent-list').replaceChildren(...(result.items.length ? result.items.map(item => occurrenceRow(item)) : [element('p', 'empty-state', 'O primeiro olhar pode ser o seu. Registre uma ocorrência para começar.')]));
  } catch (error) { $('#recent-list').replaceChildren(element('p', 'empty-state', error.message)); }
}
async function loadOccurrences() {
  const requestNumber = ++latestListRequest;
  const params = new URLSearchParams({ page: currentPage, limit: 12 });
  for (const [key, value] of new FormData($('#filters'))) if (value) params.set(key, value);
  $('#list-count').textContent = 'Carregando…';
  try {
    const result = await api(`/api/occurrences?${params}`);
    if (requestNumber !== latestListRequest) return;
    $('#occurrences-list').replaceChildren(...(result.items.length ? result.items.map(item => occurrenceRow(item, true)) : [element('p', 'empty-state', 'Nenhuma ocorrência para estes filtros. Experimente outra região ou categoria.')]));
    $('#list-count').textContent = `${formatNumber(result.total)} registro${result.total === 1 ? '' : 's'}`;
    $('#page-label').textContent = `Página ${currentPage} de ${Math.max(1, Math.ceil(result.total / result.limit))}`;
    $('#previous-page').disabled = currentPage === 1;
    $('#next-page').disabled = currentPage * result.limit >= result.total;
  } catch (error) {
    if (requestNumber !== latestListRequest) return;
    $('#list-count').textContent = 'Consulta indisponível';
    $('#occurrences-list').replaceChildren(element('p', 'empty-state', error.message));
    $('#previous-page').disabled = $('#next-page').disabled = true;
  }
}
$('#filters').addEventListener('submit', event => { event.preventDefault(); currentPage = 1; loadOccurrences(); });
$('#previous-page').addEventListener('click', () => { currentPage--; loadOccurrences(); });
$('#next-page').addEventListener('click', () => { currentPage++; loadOccurrences(); });

function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function drawWaterChart(rawSeries) {
  const series = rawSeries.filter(row => /^\d{4}-\d{2}-\d{2}$/.test(row.date)).slice(-97);
  if (!series.length) return $('#water-chart').replaceChildren(element('p', 'empty-state', 'Histórico não disponível no artefato hídrico.'));
  const width = 620, height = 220, left = 39, right = 15, top = 14, bottom = 35;
  const x = index => left + index * (width - left - right) / Math.max(1, series.length - 1);
  const y = value => top + (100 - Math.min(100, Math.max(0, value))) * (height - top - bottom) / 100;
  const svg = svgElement('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-labelledby': 'chart-title chart-desc' });
  svg.append(svgElement('title', { id: 'chart-title' }, 'Volume armazenado do Sistema Cantareira em porcentagem'), svgElement('desc', { id: 'chart-desc' }, 'Linha verde representa observações oficiais. Linha dourada tracejada representa estimativa do modelo; área clara indica o intervalo de previsão. Eixo vertical de zero a cem por cento.'));
  for (const value of [0, 25, 50, 75, 100]) {
    svg.append(svgElement('line', { x1: left, x2: width - right, y1: y(value), y2: y(value), stroke: '#e9eddf', 'stroke-dasharray': '3 5' }), svgElement('text', { x: left - 9, y: y(value) + 3, 'text-anchor': 'end', 'font-size': 9, fill: '#929c88' }, `${value}%`));
  }
  const bands = series.map((row, index) => ({ ...row, index })).filter(row => Number.isFinite(row.lower) && Number.isFinite(row.upper));
  if (bands.length > 1) svg.append(svgElement('polygon', { points: [...bands.map(row => `${x(row.index)},${y(row.upper)}`), ...bands.toReversed().map(row => `${x(row.index)},${y(row.lower)}`)].join(' '), fill: '#eae4c7', opacity: .65 }));
  if (bands.length === 1) {
    const band = bands[0];
    svg.append(svgElement('line', { x1: x(band.index), x2: x(band.index), y1: y(band.lower), y2: y(band.upper), stroke: '#bcaa6d', 'stroke-width': 9, opacity: .45 }));
  }
  for (const [key, color, dash] of [['observed', '#557f5d', ''], ['forecast', '#b29b58', '5 5']]) {
    const values = series.map((row, index) => ({ value: row[key], index })).filter(row => Number.isFinite(row.value));
    if (key === 'forecast' && values.length) {
      const anchor = series.map((row, index) => ({ value: row.observed, index })).filter(row => Number.isFinite(row.value) && row.index < values[0].index).at(-1);
      if (anchor) values.unshift(anchor);
      const last = values.at(-1);
      svg.append(svgElement('circle', { cx: x(last.index), cy: y(last.value), r: 3.5, fill: '#b29b58', stroke: '#fff', 'stroke-width': 1.5 }));
    }
    const points = values.map(row => `${x(row.index)},${y(row.value)}`).join(' ');
    if (points) svg.append(svgElement('polyline', { points, fill: 'none', stroke: color, 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-dasharray': dash }));
  }
  for (const index of [...new Set([0, Math.round((series.length - 1) / 3), Math.round(2 * (series.length - 1) / 3), series.length - 1])]) svg.append(svgElement('text', { x: x(index), y: height - 9, 'text-anchor': index === 0 ? 'start' : index === series.length - 1 ? 'end' : 'middle', 'font-size': 9, fill: '#929c88' }, formatDate(series[index].date)));
  $('#water-chart').replaceChildren(svg);
}
function renderWater(water) {
  if (water.dataMode !== 'real' || !Number.isFinite(water.metrics?.volumePct)) {
    $('#water-volume').textContent = '—';
    $('#water-caption').textContent = 'Estudo hídrico indisponível';
    $('#water-tag').textContent = 'Sem dados';
    $('#water-chart').replaceChildren(element('p', 'empty-state', water.message || 'Gere o artefato do estudo hídrico para consultar valores e previsões.'));
    $('#water-source').textContent = 'Não há indicadores hídricos válidos. Nenhum valor foi estimado pelo painel.';
    return;
  }
  $('#water-volume').textContent = `${formatNumber(water.metrics.volumePct, 1)}%`;
  $('#water-caption').textContent = `Cantareira · observado em ${formatDate(water.observedAt)}`;
  $('#water-tag').textContent = water.freshness?.status === 'current' ? 'Dados oficiais' : 'Histórico · verificar data';
  const delta = water.metrics.change7dPp;
  $('#water-subtitle').textContent = `Sistema Cantareira · volume útil (%)${Number.isFinite(delta) ? ` · variação em 7 dias: ${delta > 0 ? '+' : ''}${formatNumber(delta, 2)} p.p.` : ''}`;
  const forecastUsable = water.freshness?.status === 'current' && water.forecast?.expired !== true;
  const chartSeries = Array.isArray(water.series) ? water.series : [];
  drawWaterChart(forecastUsable ? chartSeries : chartSeries.map(row => ({ ...row, forecast: null, lower: null, upper: null })));
  const source = $('#water-source');
  const sourceName = typeof water.source === 'object' ? water.source.name : water.source;
  source.replaceChildren(document.createTextNode(`Fonte: ${sourceName || 'Não identificada'} · observação ${formatDate(water.observedAt, { day: '2-digit', month: '2-digit', year: 'numeric' })}. `));
  try {
    const url = new URL(water.source.url);
    if (url.protocol === 'https:') { const link = element('a', 'text-link', 'Consultar origem ↗'); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; source.append(link); }
  } catch { /* No unsafe link is rendered. */ }
  const detail = element('p', '', `${water.freshness?.offline ? 'Snapshot oficial em cache. ' : ''}${forecastUsable ? `Previsão é uma estimativa${water.forecast?.intervalLevel ? `; intervalo nominal de ${formatNumber(water.forecast.intervalLevel * 100)}%` : ''}. ` : 'Previsão arquivada: prazo de uso encerrado. Atualize o estudo antes de usar suas estimativas. '}${water.source?.license?.note || ''}`);
  source.append(detail);
  const alerts = Array.isArray(water.alerts) ? water.alerts : [];
  $('#water-alerts').replaceChildren(...(alerts.length ? alerts.map(alert => {
    const item = element('article', 'alert-item');
    const heading = element('div', 'alert-top');
    const dot = element('span', `alert-dot ${['warning', 'critical'].includes(alert.level) ? 'warning' : ''}`);
    dot.setAttribute('aria-hidden', 'true');
    heading.append(dot, element('h3', '', `${water.freshness?.status === 'stale' ? 'Histórico · ' : ''}${alert.title}`));
    item.append(heading, element('p', '', alert.justification));
    if (Array.isArray(alert.limitations) && alert.limitations.length) {
      const details = element('details');
      details.append(element('summary', '', 'Limitações da análise'), element('p', '', alert.limitations.join(' ')));
      item.append(details);
    }
    return item;
  }) : [element('p', 'empty-state', 'O estudo não gerou alertas para esta observação.')]));
}
async function loadDashboard() {
  try {
    const data = await api('/api/dashboard');
    $('#metric-total').textContent = formatNumber(data.occurrences.total);
    $('#metric-open').textContent = formatNumber(data.occurrences.open);
    $('#metric-resolved').textContent = formatNumber(data.occurrences.resolved);
    $('#nav-count').textContent = formatNumber(data.occurrences.total);
    renderWater(data.water);
  } catch (error) {
    $('#water-chart').replaceChildren(element('p', 'empty-state', error.message));
    $('#water-caption').textContent = 'Consulta indisponível';
    $('#water-tag').textContent = 'Indisponível';
  }
}

const dialog = $('#occurrence-dialog');
document.querySelectorAll('[data-action="new-occurrence"]').forEach(button => button.addEventListener('click', () => {
  $('#occurrence-message').textContent = '';
  dialog.showModal();
}));
$('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } });
let toastTimeout;
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimeout); toastTimeout = setTimeout(() => { $('#toast').hidden = true; }, 7000); }
$('#occurrence-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('#submit-occurrence');
  button.disabled = true;
  $('#occurrence-message').textContent = 'Salvando o registro…';
  try {
    const data = Object.fromEntries(new FormData(event.target));
    const result = await api('/api/occurrences', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    dialog.close();
    event.target.reset();
    toast(`Ocorrência ${result.item.protocol} registrada. ${result.dataMode === 'demo' ? 'Registro de demonstração salvo em JSON.' : 'Registro salvo no MongoDB.'}`);
    currentPage = 1;
    await Promise.allSettled([loadDashboard(), loadRecent(), loadOccurrences()]);
  } catch (error) { $('#occurrence-message').textContent = error.message; }
  finally { button.disabled = false; }
});

$('#image-file').addEventListener('change', event => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  const file = event.target.files[0];
  $('#image-preview').hidden = true;
  $('#classifier-message').textContent = '';
  if (!file) return;
  if (file.size > 5 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(file.type)) {
    $('#classifier-message').textContent = 'Selecione uma imagem PNG ou JPEG de até 5 MB.';
    event.target.value = '';
    return;
  }
  previewUrl = URL.createObjectURL(file);
  $('#preview-image').src = previewUrl;
  $('#image-preview').hidden = false;
});
function renderPrediction(result) {
  const card = element('div', 'prediction-card');
  card.append(element('p', 'eyebrow', 'CLASSE SUGERIDA PELO MODELO'), element('p', 'prediction-label', result.prediction.label), element('p', 'prediction-score', `${formatNumber(result.prediction.score * 100, 1)}% · saída softmax, sem calibração`));
  for (const probability of result.probabilities || []) {
    const row = element('div', 'probability-row');
    const label = element('div', 'probability-label');
    label.append(element('span', '', probability.label), element('span', '', `${formatNumber(probability.score * 100, 1)}%`));
    const bar = svgElement('svg', { viewBox: '0 0 100 2', role: 'presentation', width: '100%', height: '7', preserveAspectRatio: 'none' });
    bar.append(svgElement('rect', { width: 100, height: 2, fill: '#edf1e5', rx: 1 }), svgElement('rect', { width: Math.min(100, Math.max(0, probability.score * 100)), height: 2, fill: '#91ad6a', rx: 1 }));
    row.append(label, bar); card.append(row);
  }
  const testAccuracy = result.model?.testAccuracy;
  card.append(element('p', 'prediction-limitations', `${result.model?.name || 'CNN'} · versão ${result.model?.version || 'não informada'}. ${Number.isFinite(testAccuracy) ? `Acurácia no conjunto de teste: ${formatNumber(testAccuracy * 100, 1)}%. ` : ''}${(result.limitations || []).join(' ')} ${result.disclaimer || ''}`));
  $('#classifier-result').replaceChildren(card);
}
$('#classifier-form').addEventListener('submit', async event => {
  event.preventDefault();
  const file = $('#image-file').files[0];
  if (!file) return;
  $('#classify-button').disabled = true;
  $('#classifier-message').textContent = 'Consultando o serviço do modelo…';
  $('#classifier-result').replaceChildren(element('p', 'empty-state', 'Análise em andamento…'));
  try {
    const form = new FormData(); form.append('file', file);
    const result = await api('/api/classify', { method: 'POST', body: form });
    renderPrediction(result);
    $('#classifier-message').textContent = 'Análise concluída. Revise a classe sugerida e as limitações.';
  } catch (error) {
    $('#classifier-message').textContent = error.message;
    $('#classifier-result').replaceChildren(element('p', 'empty-state', 'Nenhuma classificação foi produzida. O serviço pode estar indisponível ou o modelo ainda pode precisar de treinamento.'));
  } finally { $('#classify-button').disabled = false; }
});

Promise.allSettled([loadHealth(), loadDashboard(), loadRecent()]);
