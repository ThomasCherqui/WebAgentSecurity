const state = {events:[], excluded:{}};
const $ = id => document.getElementById(id);

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function sanitize(value, depth=0) {
  if (depth > 10) return '[TRUNCATED]';
  if (Array.isArray(value)) return value.map(v => sanitize(v, depth+1));
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key,item] of Object.entries(value)) {
      if (/^(signature|encrypted_content)$/i.test(key)) continue;
      out[key] = sanitize(item, depth+1);
    }
    return out;
  }
  return value;
}

function parseSse(text) {
  const output = [];
  for (const chunk of String(text || '').replace(/\r\n/g,'\n').split(/\n\n+/)) {
    let event = '';
    const lines = [];
    for (const line of chunk.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      if (line.startsWith('data:')) lines.push(line.slice(5).trimStart());
    }
    if (!lines.length) continue;
    const raw = lines.join('\n');
    try { output.push({event, data:JSON.parse(raw)}); }
    catch { output.push({event, data:{type:'unparsed',raw:raw.slice(0,12000)}}); }
  }
  return output;
}

function reconstruct(text) {
  const blocks = [];
  let message = {}, stopReason = null, usage = null;
  for (const {data={}} of parseSse(text)) {
    if (data.type === 'message_start') message = data.message || {};
    if (data.type === 'content_block_start') blocks[data.index] = {...(data.content_block || {})};
    if (data.type === 'content_block_delta') {
      const block = blocks[data.index] ||= {type:'unknown'};
      const delta = data.delta || {};
      if (delta.type === 'text_delta') block.text = (block.text || '') + (delta.text || '');
      else if (delta.type === 'thinking_delta') block.thinking = (block.thinking || '') + (delta.thinking || '');
      else if (delta.type === 'input_json_delta') block._json = (block._json || '') + (delta.partial_json || '');
      else if (delta.type !== 'signature_delta') (block.deltas ||= []).push(sanitize(delta));
    }
    if (data.type === 'content_block_stop' && blocks[data.index]?._json) {
      try { blocks[data.index].input = JSON.parse(blocks[data.index]._json); }
      catch { blocks[data.index].input = blocks[data.index]._json; }
      delete blocks[data.index]._json;
    }
    if (data.type === 'message_delta') {
      stopReason = data.delta?.stop_reason || stopReason;
      usage = data.usage || usage;
    }
  }
  const contentBlocks = blocks.filter(Boolean).map(sanitize);
  const trajectory = contentBlocks.map(block => {
    if (block.type === 'thinking') return `[thinking]\n${block.thinking || ''}`;
    if (block.type === 'text') return `[assistant]\n${block.text || ''}`;
    if (['tool_use','server_tool_use'].includes(block.type)) {
      return `[tool:${block.name || 'unknown'}]\n${JSON.stringify(block.input || {},null,2)}`;
    }
    return `[${block.type || 'content'}]\n${JSON.stringify(block,null,2)}`;
  }).join('\n\n');
  return {
    message_id:message.id || null,
    model:message.model || null,
    stop_reason:stopReason || message.stop_reason || null,
    usage:usage || message.usage || null,
    content_blocks:contentBlocks,
    reconstructed_trajectory:trajectory
  };
}

function processHar(har) {
  const entries = har?.log?.entries;
  if (!Array.isArray(entries)) throw new Error('Format HAR invalide : log.entries absent.');
  state.events=[]; state.excluded={other_requests:0,non_streaming_messages:0};
  entries.forEach((entry,index) => {
    const request=entry.request || {}, content=(entry.response || {}).content || {};
    const wanted=request.method === 'POST' && String(request.url || '').startsWith('https://api.anthropic.com/v1/messages');
    if (!wanted) { state.excluded.other_requests++; return; }
    if (!String(content.mimeType || '').includes('text/event-stream')) {
      state.excluded.non_streaming_messages++; return;
    }
    state.events.push({
      id:index, timestamp:entry.startedDateTime || null,
      destination:'api.anthropic.com', method:'POST',
      url:'https://api.anthropic.com/v1/messages',
      response:reconstruct(content.text || ''), selected:true
    });
  });
  Object.keys(state.excluded).forEach(k => !state.excluded[k] && delete state.excluded[k]);
  render();
}

function render() {
  const excluded=Object.values(state.excluded).reduce((a,b)=>a+b,0);
  const selected=state.events.filter(e=>e.selected).length;
  $('stats').innerHTML=[`${state.events.length+excluded} requêtes HAR`,`${state.events.length} flux Anthropic SSE`,`${selected} sélectionnés`,...Object.entries(state.excluded).map(([k,v])=>`${k}: ${v}`)].map(x=>`<span class="pill">${escapeHtml(x)}</span>`).join('');
  $('rows').innerHTML=state.events.map((event,index)=>`<tr>
    <td><input type="checkbox" data-index="${index}" ${event.selected?'checked':''}></td>
    <td>${escapeHtml(event.response.model || event.destination)}</td>
    <td class="url"><b>Étape ${index+1}</b><br>${escapeHtml(event.response.message_id || '')}</td>
    <td class="payload">${escapeHtml(event.response.reconstructed_trajectory || '(aucun contenu reconstruit)')}</td>
  </tr>`).join('');
  $('rows').querySelectorAll('input').forEach(input=>input.onchange=()=>{state.events[+input.dataset.index].selected=input.checked;render();});
  $('all').disabled=$('none').disabled=$('send').disabled=!state.events.length;
}

$('har').onchange=async event=>{
  try { processHar(JSON.parse(await event.target.files[0].text())); $('result').textContent='Raisonnement reconstitué localement. Vérifie les étapes avant envoi.'; }
  catch(error) { $('result').innerHTML=`<span class="danger">${escapeHtml(error.message)}</span>`; }
};
$('all').onclick=()=>{state.events.forEach(e=>e.selected=true);render();};
$('none').onclick=()=>{state.events.forEach(e=>e.selected=false);render();};
$('server').value=localStorage.getItem('privacyServer') || '';
$('send').onclick=async()=>{
  const base=$('server').value.trim().replace(/\/$/,'');
  const events=state.events.filter(e=>e.selected).map(({selected,...event})=>event);
  if (!base || !events.length) return alert('URL ngrok ou sélection manquante.');
  localStorage.setItem('privacyServer',base); $('send').disabled=true;
  $('result').textContent=`Analyse de ${events.length} étapes en cours…`;
  try {
    const response=await fetch(base+'/api/analyze',{method:'POST',headers:{'Content-Type':'application/json','X-Privacy-Token':$('token').value,'ngrok-skip-browser-warning':'true'},body:JSON.stringify({task_goal:$('goal').value,events,mock:$('mock').checked})});
    const result=await response.json(); if(!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    $('result').innerHTML=`<h3 class="${result.oversharing?'danger':'success'}">${result.oversharing?'Oversharing détecté':'Aucun oversharing détecté'}</h3><pre>${escapeHtml(JSON.stringify(result.final_verdict,null,2))}</pre>`;
  } catch(error) { $('result').innerHTML=`<span class="danger">Erreur : ${escapeHtml(error.message)}</span>`; }
  finally {$('send').disabled=false;}
};
