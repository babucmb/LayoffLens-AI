const $ = selector => document.querySelector(selector);
const escapeText = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const money = value => `$${Number(value).toFixed(2)}M`;

const api = async (path, options = {}) => {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.message || detail;
    } catch (_) {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
};

const showError = (selector, message) => {
  const element = $(selector);
  if (!element) return;
  element.textContent = `Unable to load this view: ${message}`;
  element.classList.remove('hidden');
};

const clearError = selector => $(selector)?.classList.add('hidden');

function renderKpis(data) {
  const items = [
    ['Revenue outlook', money(data.kpis.revenue_outlook), 'illustrative'],
    ['Demand trend', `${data.kpis.demand_trend}%`, 'seeded period comparison'],
    ['Capacity gap', `${data.kpis.capacity_gap} units`, 'aggregate only'],
    ['AI + infra spend', money(data.kpis.investment_spend), 'October run-rate'],
    ['Forecast confidence', `${Math.round(data.kpis.confidence * 100)}%`, 'defined baseline'],
    ['Data freshness', data.kpis.freshness.warning, 'freshness not measurable for seed data'],
  ];
  $('#kpis').innerHTML = items.map(([label, value, note]) =>
    `<div class="card kpi"><div class="label">${escapeText(label)}</div><div class="value">${escapeText(value)}</div><div class="delta">${escapeText(note)}</div></div>`
  ).join('');
}

function renderOverview(data) {
  renderKpis(data);
  $('#headline').textContent = data.headline;
  const quality = data.data_quality;
  $('#quality-banner').textContent = quality.valid
    ? `Source validation: valid synthetic seed · Freshness: ${quality.freshness} · ${quality.warning}`
    : `Source validation: blocked · ${quality.warning}`;
  $('#quality-banner').classList.toggle('quality-warning', !quality.valid);
  $('#finance-chart').innerHTML = data.finance.map(record =>
    `<div style="flex:1"><div class="bar-group"><div class="bar actual" style="height:${Number(record.revenue) / 13 * 100}%"></div><div class="bar budget" style="height:${Number(record.budget) / 13 * 100}%"></div></div><span class="bar-label">${escapeText(record.month)}</span></div>`
  ).join('');
  $('#risk-list').innerHTML = data.risks.map(risk =>
    `<div class="risk"><span class="severity ${escapeText(risk.severity)}">${escapeText(risk.severity)}</span><div class="risk-title">${escapeText(risk.title)}</div><div class="risk-meta">${escapeText(risk.unit)} · ${escapeText(risk.horizon)} · ${Math.round(Number(risk.confidence) * 100)}% confidence</div><div class="risk-evidence">${risk.evidence.map(escapeText).join(' · ')}</div></div>`
  ).join('');
}

function renderAnalytics({ finance, workforce, forecasts, signals }) {
  const revenue = finance.metrics.find(item => item.metric === 'revenue') || {};
  const margin = finance.metrics.find(item => item.metric === 'operating_margin') || {};
  const forecast = forecasts.forecasts.find(item => item.metric === 'revenue') || {};
  $('#analytics-status').textContent = `${signals.length} generated signals · local synthetic source`;
  $('#analytics-summary').innerHTML = `<div class="grid two"><div><p><b>Revenue trend:</b> ${escapeText(revenue.percentage_change ?? 'n/a')}% month over month</p><p><b>Operating margin:</b> ${escapeText(margin.latest ?? 'n/a')}</p><p><b>Aggregate shortage:</b> ${escapeText(workforce.aggregate_shortage)} capacity units</p></div><div><p><b>90-day revenue forecast:</b> ${escapeText(forecast.forecast_value ?? 'unavailable')} USD millions</p><p class="muted">Range: ${escapeText(forecast.lower_bound ?? 'n/a')}–${escapeText(forecast.upper_bound ?? 'n/a')}. ${escapeText(forecast.uncertainty || '')}</p><p><b>Signals:</b> ${escapeText(signals.map(item => item.event_type).join(' · ') || 'none at current threshold')}</p></div></div>`;
}

function renderScenarios(data) {
  const labels = { baseline: 'Baseline', downside: 'Downside', intervention: 'Intervention' };
  $('#scenario-results').innerHTML = Object.entries(labels).map(([key, label]) => {
    const scenario = data[key];
    return `<div class="scenario ${key}"><h3>${escapeText(label)}</h3><div class="big">${money(scenario.revenue_outlook)}</div><dl><dt>Capacity gap</dt><dd>${escapeText(scenario.capacity_gap)} units</dd><br><dt>Infra spend</dt><dd>${money(scenario.infrastructure_spend)}</dd><br><dt>Confidence</dt><dd>${Math.round(Number(scenario.confidence) * 100)}%</dd></dl></div>`;
  }).join('');
  $('#action-grid').innerHTML = data.actions.map(action =>
    `<div class="action"><h3>${escapeText(action.name)}</h3><p>${escapeText(action.benefit)}</p><small><b>Eligibility:</b> ${Object.prototype.hasOwnProperty.call(action, 'eligible') ? (action.eligible ? 'eligible' : 'not eligible') : 'not evaluated'}<br>${escapeText(action.cost)} ${escapeText(action.cost_unit)} · ${escapeText(action.time_to_effect)}<br>${escapeText(action.condition)}<br><b>Uncertainty:</b> ${escapeText(action.uncertainty)}<br><b>Approval:</b> ${escapeText(action.approval)}<br><b>Estimate:</b> illustrative, not validated savings</small></div>`
  ).join('');
  const evaluation = data.evaluation || {};
  const alternatives = (evaluation.scenarios || []).filter(item => item.scenario_type === 'alternative');
  $('#scenario-results').insertAdjacentHTML('beforeend', `<div class="scenario comparison"><h3>Decision comparison</h3><p>${escapeText(evaluation.ranking_explanation || 'No ranking evaluated')}</p><p><b>Ranked alternatives:</b> ${escapeText((evaluation.ranking || []).join(' · ') || 'none')}</p><small>${escapeText(evaluation.double_counting_warning || 'Savings are not additive.')}</small></div>`);
  $('#action-grid').insertAdjacentHTML('beforeend', alternatives.map(item =>
    `<div class="action"><h3>${escapeText(item.scenario_id)}</h3><p>${escapeText(item.explanation)}</p><small><b>Status:</b> ${escapeText(item.evaluation_status)} · <b>Feasibility:</b> ${escapeText(item.feasibility)}<br><b>Gross savings:</b> ${escapeText(item.gross_savings ?? 'unknown')} USD millions · <b>Cost:</b> ${escapeText(item.estimated_cost ?? 'unknown')} USD millions<br><b>Net impact:</b> ${escapeText(item.net_savings ?? 'unknown')} USD millions<br><b>Assumptions:</b> ${escapeText((item.assumptions || []).join(' · '))}<br><b>Limitations:</b> ${escapeText((item.limitations || []).join(' · ') || 'none')}</small></div>`
  ).join(''));
  const sensitivity = data.sensitivity || {};
  $('#scenario-results').insertAdjacentHTML('beforeend', `<div class="scenario comparison"><h3>Sensitivity</h3><p>Most sensitive declared assumption: <b>${escapeText(sensitivity.most_sensitive_parameter || 'unavailable')}</b></p><small>${escapeText(sensitivity.method || 'Endpoint analysis')}</small></div>`);
}

async function loadScenarios() {
  clearError('#scenario-error');
  const scenario = {
    delay_months: Number($('#delay').value),
    conversion: Number($('#conversion').value) / 100,
    infra_change: Number($('#infra').value) / 100,
    hiring_delay: Number($('#hiring-delay').value),
    mobility: Number($('#mobility').value),
  };
  $('#delay-out').textContent = `${scenario.delay_months.toFixed(1)} months`;
  $('#conversion-out').textContent = `${Math.round(scenario.conversion * 100)}%`;
  $('#infra-out').textContent = `${Math.round(scenario.infra_change * 100)}%`;
  $('#hiring-delay-out').textContent = `${scenario.hiring_delay.toFixed(1)} months`;
  $('#mobility-out').textContent = `${scenario.mobility} units`;
  try {
    renderScenarios(await api('/api/scenarios', { method: 'POST', body: JSON.stringify(scenario) }));
  } catch (error) {
    showError('#scenario-error', error.message);
  }
  try {
    const history = await api('/api/scenarios/history');
    $('#canonical-scenario-history').innerHTML = history.length
      ? history.slice(0, 8).map(item => `<div class="review"><strong>${escapeText(item.scenario_name || item.scenario_type)}</strong> · ${escapeText(item.forecast_horizon_days)} days · ${escapeText(item.created_at)}<br>Revenue: ${money(item.financial_results?.revenue_outlook)} · Capacity gap: ${escapeText(item.financial_results?.capacity_gap)} units · <small>${escapeText(item.scenario_id)}</small></div>`).join('')
      : '<p class="muted">No canonical simulations recorded yet.</p>';
  } catch (error) {
    $('#canonical-scenario-history').textContent = `Unable to load canonical history: ${error.message}`;
  }
}

function renderInvestigation(data) {
  const panel = $('#investigation-panel');
  panel.classList.remove('hidden');
  const source = data.source || {};
  const policy = data.policy || {};
  const trace = data.agent_trace || [];
  const traceMarkup = trace.length ? `<div class="evidence-meta"><p><b>Agent runtime trace:</b> ${trace.length} selected agents · deterministic simulation mode</p>${trace.map(item => `<p><b>${escapeText(item.agent)}</b> · ${escapeText(item.status)}<br><small>${escapeText(item.reason)} · tools: ${escapeText((item.selected_tools || []).join(', ') || 'none')} · evidence: ${escapeText((item.evidence || []).join(' · ') || 'none')}</small></p>`).join('')}</div>` : '';
  panel.innerHTML = `<div class="card-head"><div><p class="eyebrow">AGENT RUNTIME · ${escapeText(data.mode)}</p><h2>Investigation ${escapeText(data.run_id.slice(0, 8))}</h2><p class="muted">${escapeText(data.timestamp)} · Status: <b>${escapeText(data.investigation_status || 'unavailable')}</b></p></div><span class="badge">${escapeText(data.meta_call?.source || 'Demo fallback')}</span></div><div class="evidence-meta"><p><b>Source snapshot:</b> ${escapeText(source.snapshot_id || 'unavailable')} · version ${escapeText(source.version || 'unavailable')}</p><p><b>Ingested:</b> ${escapeText(source.ingested_at || 'unavailable')} · <b>Source event time:</b> ${escapeText(source.source_timestamp || 'unavailable in synthetic fixture')}</p><p><b>Policy:</b> ${escapeText(policy.name || 'unavailable')} · planner ${escapeText(policy.planner || 'unavailable')}</p><p><b>Evidence review:</b> ${data.review?.completed ? 'completed' : 'not completed'}${data.review?.mandatory_missing?.length ? ` · missing: ${escapeText(data.review.mandatory_missing.join(', '))}` : ''}</p></div>${traceMarkup}<div>${data.steps.map(step =>
    `<div class="agent ${step.status === 'failed' ? 'failed' : ''}"><i class="agent-dot"></i><b>${escapeText(step.agent)}</b><span>${escapeText(step.error || JSON.stringify(step.result))}<br><small>Status: ${escapeText(step.status)} · Inputs: ${escapeText((step.inputs || []).join(', ') || 'none')}<br>Evidence: ${escapeText((step.evidence || []).join(' · ') || 'none')} · Reason: ${escapeText(step.reason || 'unavailable')}</small></span><small>${escapeText(step.status)}</small></div>`
  ).join('')}</div><div class="card" style="margin-top:16px;background:#f5fbf7"><p class="eyebrow">EVIDENCE-GROUNDED EXECUTIVE BRIEF</p>${Object.entries(data.brief).map(([key, value]) =>
    `<p><b>${escapeText(key.replaceAll('_', ' '))}</b><br>${escapeText(Array.isArray(value) ? value.join(' · ') : value)}</p>`
  ).join('')}</div>`;
}

function renderHistory(runs) {
  $('#history').innerHTML = runs.length ? runs.map(run =>
    `<div class="history-item"><b>${escapeText(run.event?.type || 'event')}</b> · ${escapeText(run.investigation_status || 'unavailable')} · ${escapeText(run.created_at || 'unavailable')}<br><small>Run ${escapeText(run.id)} · Snapshot ${escapeText(run.source?.snapshot_id || 'unavailable')} · Policy ${escapeText(run.policy?.name || 'unavailable')}</small><br><button class="primary history-open" data-run-id="${escapeText(run.id)}">Inspect run</button></div>`
  ).join('') : '<p class="muted">No investigations recorded yet.</p>';
  document.querySelectorAll('.history-open').forEach(button => {
    button.onclick = () => {
      const run = runs.find(item => item.id === button.dataset.runId);
      if (!run) return;
      const detail = $('#history-detail');
      detail.classList.remove('hidden');
      detail.replaceChildren();
      const title = document.createElement('b');
      title.textContent = `Run ${run.id}`;
      detail.append(title);
      const summary = document.createElement('p');
      summary.textContent = `Status: ${run.investigation_status || 'unavailable'} · Event: ${run.event?.type || 'unavailable'} · Source: ${run.source?.snapshot_id || 'unavailable'}`;
      detail.append(summary);
      const evidence = document.createElement('p');
      evidence.textContent = `Evidence: ${(run.brief?.evidence || []).join(' · ') || 'none'} · ${(run.outcomes || []).length} explicitly recorded outcomes`;
      detail.append(evidence);
      $('#save-outcome').dataset.investigationId = run.id;
      $('#save-review').dataset.investigationId = run.id;
      $('#review-context').textContent = `Linked investigation: ${run.id} · ${run.investigation_status || 'unavailable'} · evidence snapshot will be captured`;
    };
  });
}

async function loadHistory() {
  try {
    const runs = await api('/api/history');
    window.investigationRuns = runs;
    renderHistory(runs);
    if ($('#investigation-history')) renderInvestigationHistory(runs);
  } catch (error) {
    $('#history').textContent = `Unable to load investigation history: ${error.message}`;
  }
}

function renderInvestigationHistory(runs) {
  const container = $('#investigation-history');
  if (!container) return;
  container.replaceChildren();
  if (!runs.length) { container.textContent = 'No investigations recorded yet.'; return; }
  runs.slice().reverse().forEach(run => {
    const item = document.createElement('article');
    item.className = 'history-item';
    const heading = document.createElement('strong');
    heading.textContent = `${run.event?.type || 'event'} · ${run.investigation_status || 'unknown'}`;
    const detail = document.createElement('p');
    detail.className = 'muted';
    detail.textContent = `${run.id} · ${run.timestamp || run.created_at || 'unknown time'} · ${run.steps?.length || 0} specialist steps · ${(run.brief?.evidence || []).length} evidence references`;
    const button = document.createElement('button');
    button.className = 'primary';
    button.textContent = 'Open trace';
    button.onclick = () => { renderInvestigation(run); $('#overview').scrollIntoView({ behavior: 'smooth' }); };
    item.append(heading, detail, button);
    container.append(item);
  });
}

async function loadIntelligence() {
  try {
    const [finance, demand, projects, workforce, operations, anomalies, signals] = await Promise.all([
      api('/api/analytics/finance'), api('/api/analytics/demand'), api('/api/analytics/projects'),
      api('/api/analytics/workforce'), api('/api/analytics/operations'),
      api('/api/analytics/anomalies?threshold=1'), api('/api/signals'),
    ]);
    $('#intelligence-finance').textContent = `Revenue: ${finance.metrics?.find(item => item.metric === 'revenue')?.latest ?? 'n/a'} · Pipeline trend: ${demand.metrics?.find(item => item.metric === 'weighted_pipeline')?.percentage_change ?? 'n/a'}% · Infrastructure: ${operations.cloud?.latest_total_cost ?? 'n/a'}`;
    $('#intelligence-workforce').textContent = `Aggregate shortage: ${workforce.aggregate_shortage ?? 'n/a'} capacity units · Project risks: ${projects.risk_count ?? projects.projects?.length ?? 'n/a'}`;
    $('#intelligence-signals').textContent = `${signals.length} business signals · ${anomalies.length || anomalies.anomalies?.length || 0} anomalies detected. Values are synthetic and aggregate-only.`;
  } catch (error) {
    $('#intelligence-signals').textContent = `Intelligence unavailable: ${error.message}`;
  }
}

async function loadSystemStatus() {
  try {
    const [providers, quality, freshness] = await Promise.all([api('/api/providers/status'), api('/api/data/quality'), api('/api/data/freshness')]);
    $('#provider-status').textContent = `Meta: ${providers.meta.readiness} · ${providers.meta.model} · Tavily: ${providers.tavily.readiness} · Network: ${providers.network_calls}`;
    $('#data-status').textContent = `Data validation: ${quality.valid ? 'valid' : 'blocked'} · Freshness: ${freshness.warning || freshness.status || 'reported by source adapter'}`;
  } catch (error) {
    $('#provider-status').textContent = `System status unavailable: ${error.message}`;
  }
}

async function investigate() {
  const button = $('#investigate');
  button.disabled = true;
  button.textContent = 'Running bounded workflow…';
  clearError('#page-error');
  try {
    renderInvestigation(await api('/api/investigate', { method: 'POST', body: JSON.stringify({ event_type: $('#event-type').value }) }));
  } catch (error) {
    showError('#page-error', error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Run investigation <span>→</span>';
  }
}

async function loadEvaluation() {
  try {
    const data = await api('/api/evaluation');
    $('#evaluation-card').innerHTML = `<p class="eyebrow">OUTCOME EVALUATION</p><h2>Forecast humility is a feature.</h2><p class="muted">Version ${escapeText(data.model_version)} · ${escapeText(data.status)}</p><div class="kpis" style="margin-top:20px"><div class="kpi"><div class="label">MAE</div><div class="value">${escapeText(data.mae)}</div></div><div class="kpi"><div class="label">WAPE</div><div class="value">${escapeText((data.wape * 100).toFixed(1))}%</div></div></div><p><b>What the system got wrong:</b> ${escapeText(data.what_went_wrong)}</p><p><b>Controlled learning:</b> ${escapeText(data.controlled_learning)}</p>`;
  } catch (error) {
    $('#evaluation-card').textContent = `Unable to load evaluation: ${error.message}`;
  }
}

async function loadReviews() {
  try {
    const reviews = await api('/api/reviews');
    const container = $('#reviews');
    container.replaceChildren();
    if (!reviews.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = 'No decisions recorded yet.';
      container.append(empty);
    }
    reviews.forEach(review => {
      const item = document.createElement('div');
      item.className = 'review';
      const title = document.createElement('strong');
      title.textContent = `${review.recommendation.replace('_', ' ')} · ${review.lifecycle_status}`;
      const meta = document.createElement('div');
      meta.className = 'muted';
      meta.textContent = `${review.actor || review.reviewer || 'demo identity'} · ${review.timestamp || review.created_at} · Investigation: ${review.investigation_id || 'unlinked'}`;
      const rationale = document.createElement('p');
      rationale.textContent = review.rationale || 'No rationale recorded.';
      const button = document.createElement('button');
      button.className = 'primary';
      button.textContent = 'Inspect review';
      button.onclick = () => renderReviewDetail(review);
      item.append(title, meta, rationale, button);
      container.append(item);
    });
    await loadAuditEvents();
  } catch (error) {
    $('#reviews').textContent = `Unable to load review history: ${error.message}`;
  }
}

function renderReviewDetail(review) {
  const detail = $('#review-detail');
  detail.classList.remove('hidden');
  detail.replaceChildren();
  const heading = document.createElement('b');
  heading.textContent = `Review ${review.id} · ${review.lifecycle_status}`;
  const evidence = document.createElement('p');
  evidence.textContent = `Evidence snapshot: ${(review.evidence_snapshot?.evidence || []).map(item => item.evidence_id || item).join(' · ') || 'none'}`;
  const timeline = document.createElement('div');
  (review.activity || []).forEach(activity => {
    const row = document.createElement('p');
    row.className = 'muted';
    row.textContent = `${activity.activity_type} · ${activity.actor} · ${activity.created_at} · ${activity.detail?.comment || activity.detail?.rationale || ''}`;
    timeline.append(row);
  });
  const comment = document.createElement('textarea');
  comment.placeholder = 'Add a review comment';
  const commentButton = document.createElement('button');
  commentButton.className = 'primary';
  commentButton.textContent = 'Add comment';
  commentButton.onclick = async () => {
    if (!comment.value.trim()) return;
    await api(`/api/reviews/${encodeURIComponent(review.id)}/comments`, { method: 'POST', body: JSON.stringify({ comment: comment.value.trim() }) });
    comment.value = '';
    await loadReviews();
  };
  detail.append(heading, evidence, timeline, comment, commentButton);
}

async function loadAuditEvents() {
  try {
    const events = await api('/api/audit');
    const container = $('#audit-events');
    container.replaceChildren();
    events.slice(-20).reverse().forEach(event => {
      const row = document.createElement('div');
      row.className = 'review';
      row.textContent = `${event.created_at} · ${event.action} · ${event.actor} (${event.role}) · ${event.tenant_id} · ${JSON.stringify(event.detail)}`;
      container.append(row);
    });
  } catch (error) {
    $('#audit-events').textContent = `Audit access unavailable: ${error.message}`;
  }
}

document.querySelectorAll('.tab').forEach(tab => tab.onclick = () => {
  document.querySelectorAll('.tab,.view').forEach(element => element.classList.remove('active'));
  tab.classList.add('active');
  $(`#${tab.dataset.view}`).classList.add('active');
  if (tab.dataset.view === 'scenarios') loadScenarios();
  if (tab.dataset.view === 'intelligence') loadIntelligence();
  if (tab.dataset.view === 'investigations') loadHistory();
  if (tab.dataset.view === 'evaluation') loadEvaluation();
  if (tab.dataset.view === 'audit') loadReviews();
  if (tab.dataset.view === 'audit') loadHistory();
  if (tab.dataset.view === 'system') loadSystemStatus();
});

$('#investigate').onclick = investigate;
$('#recalculate').onclick = loadScenarios;
$('#save-review').onclick = async () => {
  const rationale = $('#rationale').value.trim();
  if (rationale.length < 3) {
    $('#review-message').textContent = 'Add a short rationale before saving.';
    return;
  }
  const button = $('#save-review');
  button.disabled = true;
  try {
    const reviewPayload = { recommendation: $('#decision').value, rationale };
    if (button.dataset.investigationId) reviewPayload.investigation_id = button.dataset.investigationId;
    await api('/api/reviews', { method: 'POST', body: JSON.stringify(reviewPayload) });
    $('#rationale').value = '';
    await loadReviews();
  } catch (error) {
    $('#review-message').textContent = `Unable to save review: ${error.message}`;
  } finally {
    button.disabled = false;
  }
};

$('#save-outcome').onclick = async () => {
  const button = $('#save-outcome');
  const investigationId = button.dataset.investigationId;
  const source = $('#outcome-source').value.trim();
  const observedOn = $('#outcome-date').value;
  if (!investigationId || !source || !observedOn) {
    $('#outcome-message').textContent = 'Inspect a run and provide an observation date and evidence source.';
    return;
  }
  button.disabled = true;
  try {
    await api('/api/outcomes', { method: 'POST', body: JSON.stringify({
      investigation_id: investigationId,
      category: $('#outcome-category').value,
      value: $('#outcome-value').value === '' ? null : Number($('#outcome-value').value),
      unit: $('#outcome-unit').value.trim() || null,
      observed_on: observedOn,
      evidence_source: source,
      provenance: 'explicitly_supplied',
    }) });
    $('#outcome-message').textContent = 'Observed outcome saved; it is not attributed automatically to the recommendation.';
    await loadHistory();
  } catch (error) {
    $('#outcome-message').textContent = `Unable to save outcome: ${error.message}`;
  } finally {
    button.disabled = false;
  }
};

(async () => {
  try {
    const [overview, meta, providers, finance, workforce, forecasts, signals] = await Promise.all([
      api('/api/overview'), api('/api/meta/status'), api('/api/providers/status'), api('/api/analytics/finance'),
      api('/api/analytics/workforce'), api('/api/analytics/forecasts?horizon_days=90'),
      api('/api/signals'),
    ]);
    renderOverview(overview);
    renderAnalytics({ finance, workforce, forecasts, signals });
    await loadHistory();
    $('#meta-badge').textContent = meta.mode === 'live' ? `LIVE META · ${meta.model}` : `DEMO FALLBACK · ${meta.model}`;
    $('#research-badge').textContent = providers.tavily.configured ? 'TAVILY · CONFIGURED / NOT TESTED' : 'TAVILY · NOT CONFIGURED';
  } catch (error) {
    showError('#page-error', error.message);
  }
})();
