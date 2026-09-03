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
  if (!Array.isArray(entries)) throw new Error('Invalid HAR format: log.entries is missing.');
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
  $('stats').innerHTML=[`${state.events.length+excluded} HAR requests`,`${state.events.length} Anthropic SSE streams`,`${selected} selected`,...Object.entries(state.excluded).map(([k,v])=>`${k}: ${v}`)].map(x=>`<span class="pill">${escapeHtml(x)}</span>`).join('');
  $('rows').innerHTML=state.events.map((event,index)=>`<tr>
    <td><input type="checkbox" data-index="${index}" ${event.selected?'checked':''}></td>
    <td>${escapeHtml(event.response.model || event.destination)}</td>
    <td class="url"><b>Step ${index+1}</b><br>${escapeHtml(event.response.message_id || '')}</td>
    <td class="payload">${escapeHtml(event.response.reconstructed_trajectory || '(no reconstructed content)')}</td>
  </tr>`).join('');
  $('rows').querySelectorAll('input').forEach(input=>input.onchange=()=>{state.events[+input.dataset.index].selected=input.checked;render();});
  $('all').disabled=$('none').disabled=$('send').disabled=!state.events.length;
}

function renderResult(result) {
  const verdict=result.final_verdict || {};
  const violations=Array.isArray(verdict.violations) ? verdict.violations : [];
  const meta=result.analysis_metadata || {};
  let details="";
  for (const item of violations) details += "<div><strong>"+escapeHtml(item.category || "Violation")+"</strong><p>"+escapeHtml(item.reason || item.evidence || "")+"</p></div>";
  document.getElementById("result").innerHTML='<div class="verdict '+(result.oversharing ? 'bad' : 'good')+'">'+(result.oversharing ? 'Oversharing detected' : 'No oversharing detected')+'</div><p class="summary">'+escapeHtml(verdict.decision_summary || verdict.no_violation_reason || '')+'</p><div class="violations">'+details+'</div><p class="meta">'+(meta.steps_sent || 0)+' steps · '+(meta.trajectory_characters_sent || 0)+' characters · '+(meta.ollama_calls || 0)+' Ollama calls · '+(meta.elapsed_seconds || 0)+'s · '+escapeHtml(meta.chairman_model || '')+'</p>';
}

$('har').onchange=async event=>{
  try { processHar(JSON.parse(await event.target.files[0].text())); $('result').textContent='Reasoning reconstructed locally. Review the steps before analysis.'; }
  catch(error) { $('result').innerHTML=`<span class="danger">${escapeHtml(error.message)}</span>`; }
};
$('all').onclick=()=>{state.events.forEach(e=>e.selected=true);render();};
$('none').onclick=()=>{state.events.forEach(e=>e.selected=false);render();};
$('send').onclick=async()=>{
  const events=state.events.filter(e=>e.selected).map(({selected,...event})=>event);
  if (!events.length) return alert("No steps selected.");
  document.getElementById("send").disabled=true;
  $('result').textContent=`Analyzing ${events.length} steps…`;
  try {
    const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task_goal:document.getElementById("goal").value,task_context:document.getElementById("context").value,events,mock:false})});
    const result=await response.json(); if(!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    window.renderDetailedResult(result);
  } catch(error) { $('result').innerHTML=`<span class="danger">Error: ${escapeHtml(error.message)}</span>`; }
  finally {$('send').disabled=false;}
};
