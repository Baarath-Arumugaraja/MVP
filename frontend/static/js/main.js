let currentData = null;
let phasesChart = null, statusChart = null, radarChart = null;
const HISTORY_KEY = 'repurpose_history';

// ── NAVIGATION ───────────────────────────────────────────────────────────────
function showSection(id) {
  ['hero','loading-section','results-section','compare-section','batch-section']
    .forEach(s => document.getElementById(s).classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
  window.scrollTo(0,0);
}
function goBack() { showSection('hero'); destroyCharts(); }
function setMolecule(n) { document.getElementById('molecule-input').value = n; }
function showError(m) {
  const t = document.getElementById('error-toast');
  t.textContent = m; t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 5000);
}

// ── HISTORY ──────────────────────────────────────────────────────────────────
function getHistory() { try { return JSON.parse(localStorage.getItem(HISTORY_KEY)||'[]'); } catch { return []; } }
function addHistory(m) {
  let h = getHistory().filter(x => x.toLowerCase() !== m.toLowerCase());
  h.unshift(m); h = h.slice(0,6);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h)); } catch {}
  renderHistory();
}
function renderHistory() {
  const h = getHistory();
  const row = document.getElementById('history-row');
  const pills = document.getElementById('history-pills');
  if (!h.length) { row.style.display='none'; return; }
  row.style.display='flex';
  pills.innerHTML = h.map(m => `<span class="history-pill" onclick="setMolecule('${m}')">${m}</span>`).join('');
}

// ── SINGLE ANALYSIS ───────────────────────────────────────────────────────────
async function startAnalysis() {
  const molecule = document.getElementById('molecule-input').value.trim();
  if (!molecule) { showError('Please enter a drug name.'); return; }
  const btn = document.getElementById('analyze-btn');
  btn.classList.add('loading'); btn.querySelector('.btn-text').textContent = 'Analysing...';
  document.getElementById('loading-molecule').textContent = molecule;
  showSection('loading-section');
  resetAgents(); animateAgents();
  try {
    const res  = await fetch('/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({molecule}) });
    const data = await res.json();
    if (data.error) { showSection('hero'); showError(data.error); }
    else { currentData = data; addHistory(molecule); renderResults(data); showSection('results-section'); }
  } catch { showSection('hero'); showError('Cannot connect. Is the server running on port 5000?'); }
  finally { btn.classList.remove('loading'); btn.querySelector('.btn-text').textContent = 'Analyse Drug'; }
}

function resetAgents() {
  ['clinical','patent','market','regulatory','pubmed'].forEach(a => {
    document.getElementById('agent-'+a)?.classList.remove('running','done');
    const p = document.getElementById('prog-'+a); if (p) p.style.width='0%';
  });
  document.getElementById('synthesis-row').classList.add('hidden');
}
function animateAgents() {
  ['clinical','patent','market','regulatory','pubmed'].forEach((a,i) => {
    setTimeout(() => {
      document.getElementById('agent-'+a)?.classList.add('running');
      const p = document.getElementById('prog-'+a);
      if (p) { setTimeout(()=>p.style.width='60%',100); setTimeout(()=>p.style.width='90%',1600); }
    }, i*220);
  });
  setTimeout(() => document.getElementById('synthesis-row').classList.remove('hidden'), 2200);
}

// ── RENDER RESULTS ────────────────────────────────────────────────────────────
function renderResults(data) {
  const { molecule, report, clinical, patents, market, regulatory, pubmed,
          confidence, contradictions, clinical_context, elapsed_seconds } = data;

  document.getElementById('results-molecule-name').textContent = molecule;
  document.getElementById('results-timestamp').textContent = 'Analysed ' + new Date().toLocaleString();
  if (elapsed_seconds) document.getElementById('results-elapsed').textContent = `⚡ ${elapsed_seconds}s`;

  document.getElementById('report-title').textContent = `Repurposing Intelligence Report — ${molecule}`;
  document.getElementById('report-summary').textContent = report.executive_summary || '';

  const conf = report.confidence_score || 0;
  document.getElementById('conf-value').textContent = conf + '%';
  document.getElementById('conf-label-text').textContent = report.confidence_label || '';
  setTimeout(() => document.getElementById('confidence-fill').style.width = conf+'%', 300);

  populateCard('unmet',    report.unmet_needs,      `https://clinicaltrials.gov/search?intr=${molecule}`);
  populateCard('pipeline', report.pipeline_status,  `https://clinicaltrials.gov/search?intr=${molecule}`);
  populateCard('patent',   report.patent_landscape, patents.source_url || '#');
  populateCard('market',   report.market_potential, market.source_url  || '#');

  document.getElementById('cross-insight').textContent = report.cross_domain_insight || '';

  const rec = report.strategic_recommendation || {};
  const ve = document.getElementById('rec-verdict');
  ve.textContent = rec.verdict || '—'; ve.className='rec-verdict';
  if ((rec.verdict||'').includes('LOW'))    ve.classList.add('low');
  if ((rec.verdict||'').includes('CAUTION')) ve.classList.add('danger');
  document.getElementById('rec-reasoning').textContent = rec.reasoning || '';
  const sl = document.getElementById('rec-steps'); sl.innerHTML='';
  (rec.next_steps||[]).forEach(s => { const li=document.createElement('li'); li.textContent=s; sl.appendChild(li); });

  const rl = document.getElementById('risks-list'); rl.innerHTML='';
  (report.key_risks||[]).forEach(r => { const t=document.createElement('div'); t.className='risk-tag'; t.textContent=r; rl.appendChild(t); });

  renderContradictions(contradictions || []);
  renderContextBanner(clinical_context);
  // Repurposing opportunities — shown prominently first
  renderOpportunities(report, molecule);

  renderConfidenceBreakdown(confidence);
  destroyCharts();
  renderCharts(clinical);
  renderRadar(confidence);
  renderClinical(clinical, molecule);
  renderPatents(patents, molecule);
  renderMarket(market);
  renderRegulatory(regulatory, molecule);
  renderPubmed(pubmed, molecule);

  document.getElementById('qa-history').innerHTML='';
  document.getElementById('qa-input').value='';
}

function populateCard(id, s, url) {
  if (!s) return;
  document.getElementById(id+'-finding').textContent  = s.finding  || '';
  document.getElementById(id+'-evidence').textContent = s.evidence || '';
  const lk = document.getElementById(id+'-source-link');
  lk.textContent = '↗ '+(s.source||'Source'); lk.href = url;
}

// ── CONTRADICTIONS ────────────────────────────────────────────────────────────
function renderContradictions(flags) {
  const banner = document.getElementById('contradiction-banner');
  if (!flags.length) { banner.classList.add('hidden'); return; }
  banner.classList.remove('hidden');
  banner.className = 'contradiction-banner';
  banner.innerHTML = flags.map(f => `
    <div class="contra-flag ${f.level}">
      <div class="contra-type">${f.type}</div>
      <div class="contra-msg">${f.message}</div>
    </div>`).join('');
}

// ── CONTEXT BANNER ────────────────────────────────────────────────────────────
function renderContextBanner(ctx) {
  const b = document.getElementById('context-banner');
  if (!ctx || !ctx.signal_summary) { b.classList.add('hidden'); return; }
  b.classList.remove('hidden');
  b.innerHTML = `<strong>Context memory:</strong> ${ctx.signal_summary}`;
}

// ── CONFIDENCE BREAKDOWN ──────────────────────────────────────────────────────
function renderConfidenceBreakdown(confidence) {
  if (!confidence?.breakdown) return;
  const bd = confidence.breakdown;
  [['clinical','cdb-clinical'],['patents','cdb-patents'],['market','cdb-market'],['regulatory','cdb-regulatory']].forEach(([key,pre]) => {
    const d = bd[key]; if (!d) return;
    const pct = Math.round((d.score/d.max)*100);
    setTimeout(() => {
      const f = document.getElementById(pre+'-fill'); if (f) f.style.width=pct+'%';
      const v = document.getElementById(pre+'-val');  if (v) v.textContent=d.score+'/'+d.max;
    }, 400);
  });
}

// ── CHARTS ────────────────────────────────────────────────────────────────────
function destroyCharts() {
  [phasesChart,statusChart,radarChart].forEach(c => { if(c) c.destroy(); });
  phasesChart=statusChart=radarChart=null;
}

function renderCharts(clinical) {
  const trials = clinical?.trials || [];
  if (!trials.length) return;

  // Phase bar
  const pc = {}; 
  trials.forEach(t => { const p=(t.phase||'N/A').replace(/PHASE_?/i,'Phase ').trim(); pc[p]=(pc[p]||0)+1; });
  const phCanvas = document.getElementById('phases-chart');
  if (phCanvas) phasesChart = new Chart(phCanvas, {
    type:'bar',
    data:{ labels:Object.keys(pc), datasets:[{ data:Object.values(pc), backgroundColor:'rgba(79,255,176,0.5)', borderColor:'#4fffb0', borderWidth:1, borderRadius:4 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
      scales:{ x:{ticks:{color:'#8a8fa8',font:{size:10}}}, y:{ticks:{color:'#8a8fa8',font:{size:10},stepSize:1}, grid:{color:'rgba(255,255,255,0.05)'}} } }
  });

  // Status donut
  const sc = {}; 
  trials.forEach(t => { const s=t.status||'UNKNOWN'; sc[s]=(sc[s]||0)+1; });
  const stCanvas = document.getElementById('status-chart');
  if (stCanvas) statusChart = new Chart(stCanvas, {
    type:'doughnut',
    data:{ labels:Object.keys(sc), datasets:[{ data:Object.values(sc), backgroundColor:['#4fffb0','#00d4ff','#7b61ff','#ffb347','#ff5a5a'], borderWidth:0 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'right', labels:{color:'#8a8fa8',font:{size:10},boxWidth:10}}} }
  });
}

function renderRadar(confidence) {
  const bd = confidence?.breakdown || {};
  const rc = document.getElementById('radar-chart'); if (!rc) return;
  const scores = [
    Math.round(((bd.clinical?.score||0)/(bd.clinical?.max||35))*100),
    Math.round(((bd.patents?.score||0)/(bd.patents?.max||25))*100),
    Math.round(((bd.market?.score||0)/(bd.market?.max||25))*100),
    Math.round(((bd.regulatory?.score||0)/(bd.regulatory?.max||15))*100),
  ];
  radarChart = new Chart(rc, {
    type:'radar',
    data:{ labels:['Clinical','Patents','Market','Regulatory'],
      datasets:[{ data:scores, backgroundColor:'rgba(79,255,176,0.15)', borderColor:'#4fffb0', borderWidth:2, pointBackgroundColor:'#4fffb0', pointRadius:4 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
      scales:{ r:{ min:0, max:100, ticks:{stepSize:25,color:'#555a70',font:{size:9},backdropColor:'transparent'}, grid:{color:'rgba(255,255,255,0.07)'}, pointLabels:{color:'#8a8fa8',font:{size:11}} } } }
  });
}

// ── RAW PANELS ────────────────────────────────────────────────────────────────
function renderClinical(data, molecule) {
  const panel = document.getElementById('clinical-raw'); panel.innerHTML='';
  const count = data.total_found || data.trials?.length || 0;
  const hdr = document.createElement('div');
  hdr.style.cssText='font-family:var(--font-mono);font-size:11px;color:var(--text3);margin-bottom:12px';
  hdr.textContent=`${count} total trials · showing top ${data.trials?.length||0} · Source: ClinicalTrials.gov`;
  panel.appendChild(hdr);
  if (!data.trials?.length) { panel.innerHTML+=`<div class="raw-empty">No trials found. <a class="raw-item-link" href="https://clinicaltrials.gov/search?intr=${molecule}" target="_blank">Search manually →</a></div>`; return; }
  data.trials.forEach(t => {
    const el=document.createElement('div'); el.className='raw-item';
    const sc=(t.status||'').toLowerCase().includes('recruit')?'status-recruiting':'status-completed';
    el.innerHTML=`<div class="raw-item-title">${t.title||'Untitled'}</div>
      <div class="raw-item-meta">
        <span class="raw-meta-tag phase">${t.phase||'N/A'}</span>
        <span class="raw-meta-tag ${sc}">${t.status||'N/A'}</span>
        <span class="raw-meta-tag">${t.sponsor||''}</span>
        ${(t.conditions||[]).slice(0,2).map(c=>`<span class="raw-meta-tag">${c}</span>`).join('')}
      </div>
      <a class="raw-item-link" href="${t.source_url}" target="_blank">${t.nct_id} — View on ClinicalTrials.gov →</a>`;
    panel.appendChild(el);
  });
}

function renderPatents(data, molecule) {
  const panel = document.getElementById('patent-raw'); panel.innerHTML='';
  const info = data.compound_info||{};
  if (info.formula||info.iupac_name) {
    const el=document.createElement('div'); el.className='raw-item';
    el.innerHTML=`<div class="raw-item-title">Compound — PubChem</div>
      <div class="raw-item-meta">
        ${info.formula?`<span class="raw-meta-tag">${info.formula}</span>`:''}
        ${info.molecular_weight?`<span class="raw-meta-tag">MW: ${Number(info.molecular_weight).toFixed(2)}</span>`:''}
        ${info.cid?`<span class="raw-meta-tag">CID: ${info.cid}</span>`:''}
      </div>
      ${info.iupac_name?`<div style="font-size:11px;color:var(--text2);font-family:var(--font-mono);margin-bottom:8px">${info.iupac_name}</div>`:''}
      <a class="raw-item-link" href="${data.source_url}" target="_blank">View on PubChem →</a>`;
    panel.appendChild(el);
  }
  if (!data.patents?.length) { panel.innerHTML+=`<div class="raw-empty">No patents in PubChem. <a class="raw-item-link" href="${data.google_patents_url||'#'}" target="_blank">Search Google Patents →</a></div>`; return; }
  data.patents.forEach(p => {
    const el=document.createElement('div'); el.className='raw-item';
    el.innerHTML=`<div class="raw-item-title">${p.patent_id}</div><a class="raw-item-link" href="${p.source_url}" target="_blank">View on Google Patents →</a>`;
    panel.appendChild(el);
  });
}

function renderMarket(data) {
  const panel = document.getElementById('market-raw'); panel.innerHTML='';
  const el=document.createElement('div'); el.className='raw-item';
  el.innerHTML=`<div class="raw-item-title">Market Overview — OpenFDA</div>
    <div class="raw-item-meta">
      <span class="raw-meta-tag">${data.products_found||0} products</span>
      <span class="raw-meta-tag">${(data.adverse_event_reports||0).toLocaleString()} adverse event reports</span>
    </div>
    <div style="font-size:13px;color:var(--text2);margin-top:5px">${data.market_insight||''}</div>
    <br><a class="raw-item-link" href="${data.source_url}" target="_blank">View OpenFDA →</a>`;
  panel.appendChild(el);
  (data.products||[]).forEach(p => {
    const item=document.createElement('div'); item.className='raw-item';
    item.innerHTML=`<div class="raw-item-title">${p.brand_name||p.generic_name}</div>
      <div class="raw-item-meta"><span class="raw-meta-tag">${p.dosage_form||''}</span><span class="raw-meta-tag">${p.route||''}</span><span class="raw-meta-tag">${p.manufacturer||''}</span></div>`;
    panel.appendChild(item);
  });
}

function renderRegulatory(data, molecule) {
  const panel = document.getElementById('regulatory-raw'); panel.innerHTML='';
  (data.approvals||[]).forEach(a => {
    const el=document.createElement('div'); el.className='raw-item';
    el.innerHTML=`<div class="raw-item-title">FDA Approval — ${a.brand_name}</div>
      <div class="raw-item-meta"><span class="raw-meta-tag">${a.application_number}</span><span class="raw-meta-tag">${a.manufacturer}</span></div>
      <a class="raw-item-link" href="${data.fda_label_url||'#'}" target="_blank">View on DailyMed →</a>`;
    panel.appendChild(el);
  });
  if (data.current_indications?.length) {
    const el=document.createElement('div'); el.className='raw-item';
    el.innerHTML=`<div class="raw-item-title">Current Approved Indications</div>
      <div style="font-size:12px;color:var(--text2);line-height:1.6;margin-top:6px">${data.current_indications[0]}</div>`;
    panel.appendChild(el);
  }
  if (!panel.innerHTML) panel.innerHTML=`<div class="raw-empty">No regulatory label data. <a class="raw-item-link" href="${data.fda_label_url||'#'}" target="_blank">Search DailyMed →</a></div>`;
}

function renderPubmed(data, molecule) {
  const panel = document.getElementById('pubmed-raw'); panel.innerHTML='';
  const hdr=document.createElement('div');
  hdr.style.cssText='font-family:var(--font-mono);font-size:11px;color:var(--text3);margin-bottom:12px';
  hdr.textContent=`${data.total_found||0} papers found · Source: PubMed NCBI`;
  panel.appendChild(hdr);
  if (!data.papers?.length) { panel.innerHTML+=`<div class="raw-empty">No papers found. <a class="raw-item-link" href="${data.source_url}" target="_blank">Search PubMed →</a></div>`; return; }
  data.papers.forEach(p => {
    const el=document.createElement('div'); el.className='raw-item';
    el.innerHTML=`<div class="raw-item-title">${p.title}</div>
      <div class="raw-item-meta"><span class="raw-meta-tag">${p.year}</span><span class="raw-meta-tag">${p.authors}</span><span class="raw-meta-tag">${p.journal}</span></div>
      <a class="raw-item-link" href="${p.source_url}" target="_blank">PMID:${p.pmid} — View on PubMed →</a>`;
    panel.appendChild(el);
  });
}

function showTab(id, btn) {
  document.querySelectorAll('.raw-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.raw-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if (btn) btn.classList.add('active');
}

// ── Q&A ───────────────────────────────────────────────────────────────────────
function askSuggestion(el) { document.getElementById('qa-input').value=el.textContent; askFollowup(); }
async function askFollowup() {
  const input = document.getElementById('qa-input');
  const question = input.value.trim();
  if (!question || !currentData) return;
  const btn = document.getElementById('qa-btn');
  btn.disabled=true; btn.textContent='...';
  const history = document.getElementById('qa-history');
  const item = document.createElement('div');
  item.innerHTML=`<div class="qa-item-q">${question}</div><div class="qa-item-a qa-item-loading">Thinking...</div>`;
  history.insertBefore(item, history.firstChild);
  input.value='';
  try {
    const res = await fetch('/followup', { method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ question, context:{ molecule:currentData.molecule, report:currentData.report } }) });
    const data = await res.json();
    item.querySelector('.qa-item-a').classList.remove('qa-item-loading');
    item.querySelector('.qa-item-a').textContent = data.answer || 'No answer.';
  } catch { item.querySelector('.qa-item-a').textContent='Error connecting to server.'; }
  finally { btn.disabled=false; btn.textContent='Ask →'; }
}

// ── COMPARE ───────────────────────────────────────────────────────────────────
async function startComparison() {
  const m1=document.getElementById('compare-mol1').value.trim();
  const m2=document.getElementById('compare-mol2').value.trim();
  if (!m1||!m2) { showError('Please enter both drug names.'); return; }
  const btn=document.getElementById('compare-btn');
  btn.disabled=true; document.getElementById('compare-btn-text').textContent='Analysing both drugs...';
  document.getElementById('compare-results').classList.add('hidden');
  try {
    const res = await fetch('/compare', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({molecule1:m1,molecule2:m2}) });
    const data = await res.json();
    if (data.error) { showError(data.error); return; }
    const r1=data.molecule1, r2=data.molecule2;
    const s1=r1.report?.confidence_score||0, s2=r2.report?.confidence_score||0;
    const winner = s1>=s2 ? r1.molecule : r2.molecule;
    const container=document.getElementById('compare-results');
    container.innerHTML=`<div class="compare-grid">${compCard(r1)}${compCard(r2)}</div>
      <div class="compare-winner">
        <div class="compare-winner-label">Higher repurposing potential</div>
        <div class="compare-winner-text">${winner} — ${Math.max(s1,s2)}% confidence score</div>
      </div>`;
    container.classList.remove('hidden');
  } catch { showError('Cannot connect to backend.'); }
  finally { btn.disabled=false; document.getElementById('compare-btn-text').textContent='Compare Drugs →'; }
}

function compCard(d) {
  const r=d.report||{}, rec=r.strategic_recommendation||{};
  return `<div class="compare-card">
    <div class="compare-card-title">${d.molecule}</div>
    <div class="compare-verdict">${rec.verdict||'N/A'}</div>
    <div class="compare-summary">${r.executive_summary||'No summary.'}</div>
    <div class="compare-score">Confidence: <span>${r.confidence_score||0}%</span></div>
    <div style="margin-top:10px;font-size:11px;color:var(--text3);font-family:var(--font-mono)">Cross-domain insight</div>
    <div style="font-size:12px;color:var(--text2);margin-top:4px;line-height:1.6">${r.cross_domain_insight||'—'}</div>
  </div>`;
}

// ── BATCH ─────────────────────────────────────────────────────────────────────
async function startBatch() {
  const molecules = ['b1','b2','b3','b4','b5']
    .map(id => document.getElementById(id).value.trim()).filter(Boolean);
  if (molecules.length < 2) { showError('Enter at least 2 drug names for batch mode.'); return; }
  const btn=document.getElementById('batch-btn');
  btn.disabled=true; document.getElementById('batch-btn-text').textContent=`Analysing ${molecules.length} drugs...`;
  document.getElementById('batch-results').classList.add('hidden');
  try {
    const res = await fetch('/batch', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({molecules}) });
    const data = await res.json();
    if (data.error) { showError(data.error); return; }
    renderBatch(data.results);
  } catch { showError('Cannot connect to backend.'); }
  finally { btn.disabled=false; document.getElementById('batch-btn-text').textContent='Run Batch Analysis →'; }
}

function renderBatch(results) {
  const medals = ['gold','silver','bronze','',''];
  const container = document.getElementById('batch-results');
  container.innerHTML = `<div style="font-family:var(--font-mono);font-size:11px;color:var(--text3);margin-bottom:16px;text-transform:uppercase;letter-spacing:1px">
    Ranked by repurposing opportunity score</div>` +
    results.map((r,i) => {
      const report = r.report||{}, rec = report.strategic_recommendation||{};
      return `<div class="batch-rank-card">
        <div class="batch-rank-num ${medals[i]}">${i+1}</div>
        <div class="batch-rank-info">
          <div class="batch-rank-name">${r.molecule}</div>
          <div class="batch-rank-verdict">${rec.verdict||'N/A'}</div>
          <div class="batch-rank-summary">${report.executive_summary||'No summary.'}</div>
        </div>
        <div class="batch-score-bar">
          <div class="batch-score-num">${report.confidence_score||0}%</div>
          <span class="batch-score-label">confidence</span>
        </div>
      </div>`;
    }).join('');
  container.classList.remove('hidden');
}

// ── EXPORT ────────────────────────────────────────────────────────────────────
function exportReport() {
  if (!currentData) return;
  const blob=new Blob([JSON.stringify(currentData,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url; a.download=`repurpose-ai-${currentData.molecule}-${Date.now()}.json`;
  a.click(); URL.revokeObjectURL(url);
}

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderHistory();
  document.getElementById('molecule-input').addEventListener('keydown', e => { if(e.key==='Enter') startAnalysis(); });
  document.getElementById('qa-input').addEventListener('keydown', e => { if(e.key==='Enter') askFollowup(); });
  document.getElementById('compare-mol1').addEventListener('keydown', e => { if(e.key==='Enter') document.getElementById('compare-mol2').focus(); });
  document.getElementById('compare-mol2').addEventListener('keydown', e => { if(e.key==='Enter') startComparison(); });
});

// ── REPURPOSING OPPORTUNITIES ─────────────────────────────────────────────
function renderOpportunities(report, molecule) {
  const opps = report.repurposing_opportunities || [];
  const section = document.getElementById('opportunities-section');
  const cards = document.getElementById('opp-cards');
  const countEl = document.getElementById('opp-count');
  const subtitleEl = document.getElementById('opp-subtitle');

  if (!opps.length) { section.classList.add('hidden'); return; }
  section.classList.remove('hidden');

  const validOpps = opps.filter(o => o.disease && !o.disease.toLowerCase().includes('demo'));
  countEl.textContent = `${validOpps.length} indication${validOpps.length !== 1 ? 's' : ''} found`;
  subtitleEl.textContent = `${molecule} shows repurposing potential beyond its current approved use`;

  cards.innerHTML = '';
  validOpps.forEach((opp, i) => {
    const conf = opp.confidence || 'INVESTIGATE';
    const score = opp.confidence_score || 0;
    const patentClass = (opp.patent_status || '').toLowerCase().includes('free') ? 'patent-free' : 'patent-protected';
    const patentLabel = opp.patent_status || 'Unknown';

    const trialPill = opp.trial_id
      ? `<a class="opp-pill trial" href="https://clinicaltrials.gov/study/${opp.trial_id}" target="_blank">
           ${opp.trial_id}${opp.trial_phase ? ' · ' + opp.trial_phase : ''} ↗
         </a>`
      : '';

    const card = document.createElement('div');
    card.className = 'opp-card';
    card.innerHTML = `
      <div class="opp-card-left">
        <div class="opp-num">0${i + 1}</div>
        <div class="opp-disease">${opp.disease}</div>
        <div class="opp-description">${opp.description}</div>
        <div class="opp-pills">
          ${trialPill}
          ${opp.market_gap ? `<span class="opp-pill market">${opp.market_gap.slice(0, 50)}${opp.market_gap.length > 50 ? '...' : ''}</span>` : ''}
          <span class="opp-pill ${patentClass}">${patentLabel}</span>
          <span class="opp-pill source">${opp.source || 'ClinicalTrials.gov'}</span>
        </div>
      </div>
      <div class="opp-card-right">
        <div class="opp-confidence-badge ${conf}">${conf}</div>
        ${score > 0 ? `<span class="opp-score">${score}%</span><span class="opp-score-label">confidence</span>` : ''}
      </div>`;
    cards.appendChild(card);
  });
}
