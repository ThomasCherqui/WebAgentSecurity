(() => {
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[char]);
  const labels = {
    direct_content:'Explicit content', indirect_content:'Implicit content',
    direct_behavioral:'Explicit behavior', indirect_behavioral:'Implicit behavior'
  };

  function violationsHtml(violations) {
    if (!violations?.length) return '<p class="quiet">No violation retained.</p>';
    return violations.map(item => `
      <article class="violation-card">
        <div><strong>${safe(labels[item.category] || item.category)}</strong>${item.attribute ? `<code>${safe(item.attribute)}</code>` : ''}</div>
        ${item.evidence ? `<blockquote>“ ${safe(item.evidence)}”</blockquote>` : ''}
        <p>${safe(item.explanation || '')}</p>
      </article>`).join('');
  }

  function candidatesHtml(step) {
    return Object.entries(step.candidate_verdicts || {}).map(([label,candidate]) => {
      const model=(step.candidate_label_map || {})[label] || label;
      const count=(candidate.violations || []).length;
      return `<div class="opinion"><div><strong>${safe(label)} · ${safe(model)}</strong><span class="mini ${count?'bad':'good'}">${count ? `${count} violation(s)` : 'Clear'}</span></div>${violationsHtml(candidate.violations || [])}${candidate.no_violation_reason ? `<p class="quiet">${safe(candidate.no_violation_reason)}</p>` : ''}</div>`;
    }).join('');
  }

  function reviewsHtml(reviews) {
    return (reviews || []).map(review => `<div class="review-row"><div><strong>${safe(review.reviewer_model)}</strong><span>selects ${safe(review.choice || '—')}</span></div><p>${safe(review.reason || '')}</p></div>`).join('');
  }

  function stepHtml(step) {
    const final=step.final_verdict || {};
    const over=(final.violations || []).length > 0;
    return `<details class="step-card ${over?'has-violation':''}" ${over?'open':''}>
      <summary><span>Step ${safe(step.step)}</span><span class="mini ${over?'bad':'good'}">${over?'Oversharing':'Clear'}</span><span class="step-time">${safe(step.elapsed_seconds)} s</span></summary>
      <div class="step-body">
        <h4>Chairman decision</h4>
        <p class="decision">${safe(final.decision_summary || final.no_violation_reason || '')}</p>
        ${violationsHtml(final.violations || [])}
        <p class="quiet">${safe(final.reviewer_signal || '')} ${final.selected_candidate ? `· Selected candidate: ${safe(final.selected_candidate)}` : ''}</p>
        <details><summary>The 3 candidate opinions</summary><div class="opinion-grid">${candidatesHtml(step)}</div></details>
        <details><summary>The 3 reviews</summary>${reviewsHtml(step.reviews)}</details>
        <details><summary>Reconstructed Claude action</summary><pre>${safe(step.trajectory || '')}</pre></details>
      </div>
    </details>`;
  }

  window.renderDetailedResult = result => {
    const summary=result.summary || {}, meta=result.analysis_metadata || {};
    document.getElementById('result').innerHTML=`
      <div class="result-head"><span class="verdict ${result.oversharing?'bad':'good'}">${result.oversharing?'Oversharing detected':'No oversharing detected'}</span><span class="duration">${safe(meta.elapsed_seconds || 0)} s</span></div>
      <div class="global-summary"><strong>${safe(summary.steps_analyzed || 0)}</strong> steps analyzed · <strong>${safe(summary.violation_count || 0)}</strong> violations · <strong>${safe(meta.ollama_calls || 0)}</strong> Ollama calls</div>
      <div class="step-list">${(result.step_results || []).map(stepHtml).join('')}</div>
      <details class="audit-details"><summary>Council configuration</summary>
        <p>Jurors: ${safe((meta.council_models || []).join(' · '))}</p><p>Chairman: ${safe(meta.chairman_model || '')}</p><p>${safe(meta.calls_per_step || 0)} calls per step</p>
      </details>`;
  };

  const style=document.createElement('style');
  style.textContent=`
    .global-summary{margin:18px 0;color:#aab7c1}.step-list{display:grid;gap:10px}.step-card{border:1px solid #2b3741;border-radius:9px;padding:0;margin:0}.step-card.has-violation{border-color:#70423e}
    .step-card>summary{display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:12px;padding:13px 14px;cursor:pointer;font-weight:700}.step-body{padding:0 14px 14px;border-top:1px solid #2b3741}.step-time{font-size:12px;color:#8d9ba7}
    .mini{font-size:11px;padding:4px 7px;border-radius:99px}.mini.good{background:#153f32;color:#83e8bb}.mini.bad{background:#4a2222;color:#ffaaa0}.decision{font-size:16px;line-height:1.5}.quiet{color:#98a6b3}
    .opinion-grid{display:grid;gap:10px;margin-top:12px}.opinion{background:#10171d;padding:12px;border-radius:8px}.opinion>div:first-child{display:flex;justify-content:space-between;gap:10px}.review-row{background:#10171d;padding:10px 12px;border-radius:7px;margin:8px 0}.review-row>div{display:flex;justify-content:space-between}.review-row p{margin-bottom:0}
    code{margin-left:10px;color:#ffc0b9}pre{max-height:320px}.step-body details{margin-top:14px}.step-body h4{margin-bottom:6px}
  `;
  document.head.appendChild(style);
})();
