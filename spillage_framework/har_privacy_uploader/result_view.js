(() => {
  const CATEGORY_LABELS = {
    direct_content: 'Explicit content',
    indirect_content: 'Implicit content',
    direct_behavioral: 'Explicit behavior',
    indirect_behavioral: 'Implicit behavior'
  };

  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[char]);

  window.renderDetailedResult = result => {
    const verdict = result.final_verdict || {};
    const violations = Array.isArray(verdict.violations) ? verdict.violations : [];
    const reviews = Array.isArray(result.reviews) ? result.reviews : [];
    const meta = result.analysis_metadata || {};
    const violationHtml = violations.length ? violations.map(item => `
      <article class="violation-card">
        <div class="violation-title">
          <span>${safe(CATEGORY_LABELS[item.category] || item.category || 'Violation')}</span>
          ${item.attribute ? `<code>${safe(item.attribute)}</code>` : ''}
        </div>
        ${item.evidence ? `<blockquote>“ ${safe(item.evidence)}”</blockquote>` : ''}
        <p>${safe(item.explanation || '')}</p>
      </article>`).join('') : `
      <p class="no-violation">${safe(verdict.no_violation_reason || 'No violation supported by the trajectory.')}</p>`;

    const reviewHtml = reviews.map(review => `
      <div class="review-row">
        <span>${safe(review.reviewer_model || 'Reviewer')}</span>
        <strong>Choice ${safe(review.choice || '—')}</strong>
        <p>${safe(review.reason || '')}</p>
      </div>`).join('');

    const models = [
      ...(meta.candidate_models || []),
      ...(meta.reviewer_models || []),
      meta.chairman_model
    ].filter(Boolean);

    document.getElementById('result').innerHTML = `
      <div class="result-head">
        <span class="verdict ${result.oversharing ? 'bad' : 'good'}">
          ${result.oversharing ? 'Oversharing detected' : 'No oversharing detected'}
        </span>
        <span class="duration">${safe(meta.elapsed_seconds || 0)} s</span>
      </div>
      <h2>${safe(verdict.decision_summary || 'Analysis complete')}</h2>
      <section class="violation-list">${violationHtml}</section>
      <details class="council-details" ${result.oversharing ? 'open' : ''}>
        <summary>Council decision</summary>
        <p>${safe(verdict.reviewer_signal || 'No detailed signal provided by the chairman.')}</p>
        <p>Selected candidate: <strong>${safe(verdict.selected_candidate || '—')}</strong></p>
        ${reviewHtml}
      </details>
      <details class="audit-details">
        <summary>Analysis details</summary>
        <div class="audit-grid">
          <span><strong>${safe(meta.steps_sent || 0)}</strong> steps sent</span>
          <span><strong>${safe(meta.trajectory_characters_sent || 0)}</strong> characters</span>
          <span><strong>${safe(meta.ollama_calls || 0)}</strong> Ollama calls</span>
          <span><strong>${safe(models.join(' · '))}</strong> models</span>
        </div>
      </details>`;
  };

  const style = document.createElement('style');
  style.textContent = `
    .result-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .verdict{display:inline-block;padding:8px 12px;border-radius:999px;font-weight:750}
    .verdict.good{background:#153f32;color:#83e8bb}.verdict.bad{background:#4a2222;color:#ffaaa0}
    .duration{color:#8e9da9;font-size:13px}.result-panel h2{font-size:20px;line-height:1.4;margin:18px 0}
    .no-violation{color:#b8c4ce}.violation-card{border:1px solid #463535;border-left:3px solid #ff8f83;border-radius:8px;padding:14px;margin:12px 0}
    .violation-title{display:flex;justify-content:space-between;gap:10px;font-weight:700}.violation-title code{color:#ffc0b9}
    blockquote{margin:12px 0;padding:10px 12px;background:#0d141a;border-radius:6px;color:#d8e0e7}
    details{border-top:1px solid #2b3741;margin-top:18px;padding-top:14px}summary{cursor:pointer;font-weight:700;color:#cbd5dd}
    .review-row{margin:12px 0;padding:10px;background:#10171d;border-radius:7px}.review-row span{color:#91a1ad;margin-right:12px}.review-row p{margin-bottom:0}
    .audit-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.audit-grid span{background:#10171d;padding:10px;border-radius:7px}
  `;
  document.head.appendChild(style);
})();
