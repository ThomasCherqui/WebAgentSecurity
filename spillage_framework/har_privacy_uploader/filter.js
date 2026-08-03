const state = { har: null, events: [], excluded: {} };
const $ = id => document.getElementById(id);

const telemetryHosts = [
  'google-analytics.com','googletagmanager.com','doubleclick.net','sentry.io',
  'segment.io','segment.com','amplitude.com','mixpanel.com','posthog.com',
  'newrelic.com','datadoghq.com','browser-intake-us5-datadoghq.com',
  'honeycomb.io','hcaptcha.com'
];
const claudeHosts = ['claude.ai','anthropic.com'];
const secretKey = /(^|_)(authorization|cookie|token|access.?token|refresh.?token|api.?key|password|passwd|secret|session|signature|code.?verifier|code.?challenge|state)($|_)/i;
const staticExt = /\.(?:css|js|mjs|png|jpe?g|gif|svg|ico|woff2?|ttf|map)(?:$|\?)/i;

function hostMatches(host, list) {
  return list.some(domain => host === domain || host.endsWith('.' + domain));
}

function redactScalar(value) {
  if (typeof value !== 'string') return value;
  return value
    .replace(/Bearer\s+[A-Za-z0-9._~+\/-]+=*/gi, 'Bearer [REDACTED]')
    .replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, '[JWT_REDACTED]')
    .slice(0, 12000);
}

function sanitizeObject(value, depth=0) {
  if (depth > 8) return '[TRUNCATED_DEPTH]';
  if (Array.isArray(value)) return value.slice(0, 100).map(v => sanitizeObject(v, depth + 1));
  if (value && typeof value === 'object') {
    const output = {};
    for (const [key, item] of Object.entries(value)) {
      output[key] = secretKey.test(key) ? '[REDACTED]' : sanitizeObject(item, depth + 1);
    }
    return output;
  }
  return redactScalar(value);
}

function sanitizeUrl(raw) {
  try {
    const url = new URL(raw);
    const query = {};
    for (const [key, value] of url.searchParams.entries()) {
      query[key] = secretKey.test(key) ? '[REDACTED]' : redactScalar(value);
    }
    return {
      url: `${url.protocol}//${url.host}${url.pathname}`,
      destination: url.hostname,
      query
    };
  } catch { return {url: String(raw || ''), destination: '', query: {}}; }
}

function sanitizePostData(postData) {
  if (!postData) return null;
  const mime_type = postData.mimeType || '';
  if (Array.isArray(postData.params) && postData.params.length) {
    const params = {};
    for (const item of postData.params) {
      const key = item.name || 'unnamed';
      params[key] = secretKey.test(key) ? '[REDACTED]' : redactScalar(item.value || item.fileName || '');
    }
    return {mime_type, value: params};
  }
  const text = postData.text || '';
  if (!text) return null;
  try { return {mime_type, value: sanitizeObject(JSON.parse(text))}; }
  catch {
    if (mime_type.includes('application/x-www-form-urlencoded')) {
      const params = {};
      for (const [key, value] of new URLSearchParams(text)) {
        params[key] = secretKey.test(key) ? '[REDACTED]' : redactScalar(value);
      }
      return {mime_type, value: params};
    }
    return {mime_type, value: redactScalar(text)};
  }
}

function classify(entry) {
  const request = entry.request || {};
  const method = String(request.method || 'GET').toUpperCase();
  const parsed = sanitizeUrl(request.url);
  const mime = String((entry.response || {}).content?.mimeType || '');
  const post_data = sanitizePostData(request.postData);
  const hasQuery = Object.keys(parsed.query).length > 0;
  if (hostMatches(parsed.destination, claudeHosts) && !$('includeClaude').checked) return 'claude_control_plane';
  if (hostMatches(parsed.destination, telemetryHosts) && !$('includeTelemetry').checked) return 'telemetry';
  if (method === 'GET' && !hasQuery && (staticExt.test(parsed.url) || /^(image|font|text\/css|javascript)/i.test(mime))) return 'static';
  if (!post_data && !hasQuery && !['POST','PUT','PATCH','DELETE'].includes(method)) return 'no_user_data';
  return null;
}

function convert(entry, index) {
  const request = entry.request || {};
  const parsed = sanitizeUrl(request.url);
  return {
    id: index,
    timestamp: entry.startedDateTime || null,
    destination: parsed.destination,
    method: String(request.method || 'GET').toUpperCase(),
    url: parsed.url,
    query: parsed.query,
    post_data: sanitizePostData(request.postData),
    response: {
      status: (entry.response || {}).status ?? null,
      mime_type: (entry.response || {}).content?.mimeType || null
    },
    initiator_type: entry._initiator?.type || null
  };
}

function processHar() {
  const entries = state.har?.log?.entries;
  if (!Array.isArray(entries)) throw new Error('Format HAR invalide : log.entries est absent.');
  state.events = []; state.excluded = {};
  entries.forEach((entry, index) => {
    const reason = classify(entry);
    if (reason) state.excluded[reason] = (state.excluded[reason] || 0) + 1;
    else state.events.push({...convert(entry, index), selected: true});
  });
  render();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function render() {
  const excluded = Object.values(state.excluded).reduce((a,b) => a+b, 0);
  const selected = state.events.filter(e => e.selected).length;
  $('stats').innerHTML = [
    `${state.events.length + excluded} requêtes HAR`, `${state.events.length} retenues`,
    `${selected} sélectionnées`, `${excluded} exclues`,
    ...Object.entries(state.excluded).map(([key,value]) => `${key}: ${value}`)
  ].map(text => `<span class="pill">${escapeHtml(text)}</span>`).join('');
  $('rows').innerHTML = state.events.map((event, index) => {
    const payload = {query:event.query, post_data:event.post_data};
    return `<tr><td><input type="checkbox" data-index="${index}" ${event.selected?'checked':''}></td>`+
      `<td>${escapeHtml(event.destination)}</td><td class="url"><b>${event.method}</b> ${escapeHtml(event.url)}</td>`+
      `<td class="payload">${escapeHtml(JSON.stringify(payload,null,2))}</td></tr>`;
  }).join('');
  $('rows').querySelectorAll('input').forEach(input => input.onchange = () => {
    state.events[Number(input.dataset.index)].selected = input.checked; render();
  });
  $('all').disabled = $('none').disabled = $('send').disabled = !state.events.length;
}

$('har').onchange = async event => {
  try {
    state.har = JSON.parse(await event.target.files[0].text());
    processHar(); $('result').textContent = 'HAR filtré localement. Vérifie la sélection avant envoi.';
  } catch (error) { $('result').innerHTML = `<span class="danger">${escapeHtml(error.message)}</span>`; }
};
$('includeClaude').onchange = $('includeTelemetry').onchange = () => state.har && processHar();
$('all').onclick = () => { state.events.forEach(e => e.selected=true); render(); };
$('none').onclick = () => { state.events.forEach(e => e.selected=false); render(); };
$('server').value = localStorage.getItem('privacyServer') || '';

$('send').onclick = async () => {
  const base = $('server').value.trim().replace(/\/$/, '');
  const events = state.events.filter(e => e.selected).map(({selected, ...event}) => event);
  if (!base) return alert('Renseigne l’URL ngrok.');
  if (!events.length) return alert('Sélection vide.');
  localStorage.setItem('privacyServer', base);
  $('send').disabled = true; $('result').textContent = `Analyse de ${events.length} événements en cours…`;
  try {
    const response = await fetch(base + '/api/analyze', {
      method:'POST', headers:{'Content-Type':'application/json',
        'X-Privacy-Token':$('token').value
      },
      body:JSON.stringify({task_goal:$('goal').value, events, mock:$('mock').checked})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    $('result').innerHTML = `<h3 class="${result.oversharing?'danger':'success'}">${result.oversharing?'Oversharing détecté':'Aucun oversharing détecté'}</h3>`+
      `<pre>${escapeHtml(JSON.stringify(result.final_verdict,null,2))}</pre>`;
  } catch (error) {
    $('result').innerHTML = `<span class="danger">Erreur : ${escapeHtml(error.message)}</span>`;
  } finally { $('send').disabled = false; }
};
