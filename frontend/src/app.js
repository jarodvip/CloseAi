const baseApi = 'http://127.0.0.1:8000';
let authToken = localStorage.getItem('access_token');
let currentUser = null;
let currentSessionId = null;
let currentCustomerId = null;
let customerCache = [];
let appOptions = null;

// 标签选择状态
const selectedTags = { decisions: new Set(), actions: new Set() };

const DEFAULT_OPTIONS = {
  industries: ['母婴', '食品', '饮料', '美妆家电', '新消费', '餐饮', '服饰', '其他'],
  stages: ['初创期', '成长期', '扩张期', '成熟期', '转型期'],
  customer_types: [
    {code: 'BRAND_AMBITION', name: '品牌野心型'},
    {code: 'POSITIONING', name: '定位卡位型'},
    {code: 'CATEGORY_CREATOR', name: '品类开创者型'},
    {code: 'COMPETITIVE_BREAKOUT', name: '竞争突围型'},
    {code: 'CAPITAL_NARRATIVE', name: '资本叙事型'},
    {code: 'NATIONAL_EXPANSION', name: '全国化扩张型'},
    {code: 'BRAND_REJUVENATION', name: '品牌焕新型'},
  ],
  scenes: ['破冰', '异议应答', '逼单', '售后', '转介绍'],
  decisions: ['确定合作', '暂缓', '需再评估', '指定负责人', '明确预算'],
  actions: ['发方案', '约下次会议', '内部评审', '报价', '寄样品'],
};

function getOptions() {
  return appOptions || DEFAULT_OPTIONS;
}

async function loadOptions() {
  try {
    const data = await api('/api/v1/knowledge/options');
    if (data && data.data) {
      appOptions = data.data;
    }
  } catch (e) {
    console.error('loadOptions failed:', e);
  }
  populateOptions();
}

function populateOptions() {
  const options = getOptions();
  const industrySelects = ['cust-industry', 'case-industry'];
  const stageSelects = ['cust-stage', 'case-stage', 'filter-stage'];
  const typeSelects = ['case-type', 'script-type', 'type-primary'];
  const sceneSelects = ['script-scene'];
  const assistTypeSelects = ['assist-type'];

  industrySelects.forEach(id => fillSelect(id, options.industries || [], '请选择行业'));
  stageSelects.forEach(id => fillSelect(id, options.stages || [], '请选择阶段'));
  typeSelects.forEach(id => fillSelect(id, (options.customer_types || []).map(t => t.name), '请选择客户类型'));
  sceneSelects.forEach(id => fillSelect(id, options.scenes || [], '请选择场景'));
  assistTypeSelects.forEach(id => fillSelect(id, (options.customer_types || []).map(t => t.name), '请选择客户类型'));

  // 分析页下拉
  fillSelect('analyze-industry', options.industries || [], '行业（可选）');
  fillSelect('analyze-stage', options.stages || [], '阶段（可选）');

  // 标签选项
  const decisionsContainer = document.getElementById('followup-decisions');
  const actionsContainer = document.getElementById('followup-actions');
  if (decisionsContainer && !decisionsContainer.dataset.populated) {
    decisionsContainer.dataset.populated = 'true';
    decisionsContainer.innerHTML = (options.decisions || []).map(d =>
      `<span class="tag" onclick="toggleTag(this)" data-group="decisions">${escapeHtml(d)}</span>`
    ).join('');
  }
  if (actionsContainer && !actionsContainer.dataset.populated) {
    actionsContainer.dataset.populated = 'true';
    actionsContainer.innerHTML = (options.actions || []).map(a =>
      `<span class="tag" onclick="toggleTag(this)" data-group="actions">${escapeHtml(a)}</span>`
    ).join('');
  }
}

function fillSelect(id, items, placeholder) {
  const el = document.getElementById(id);
  if (!el || el.dataset.populated) return;
  el.dataset.populated = 'true';
  const currentValue = el.value;
  const options = items.map(item => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join('');
  el.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
  if (currentValue) el.value = currentValue;
}

async function api(path, options = {}) {
  const url = `${baseApi}${path}`;
  const headers = {'content-type': 'application/json', ...options.headers};
  if (authToken) headers['authorization'] = `Bearer ${authToken}`;
  const res = await fetch(url, { headers, ...options });
  const data = await res.json().catch(() => ({}));
  if (Array.isArray(data)) return {data};
  if (!res.ok) throw new Error(data.detail || data.message || `请求失败: ${res.status}`);
  return data;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\n/g, '<br/>');
}

function sourceCardsHtml(cards = []) {
  if (!Array.isArray(cards) || !cards.length) return '';
  const items = cards.map(card => {
    const badge = card.scene ? `<span class="source-badge">${escapeHtml(card.scene)}</span>` : '';
    const detail = [card.detail, card.label].filter(Boolean).join(' · ');
    return `<li>
      <div class="source-row">
        <span class="source-source">${escapeHtml(card.source || '未知来源')}</span>
        ${badge}
      </div>
      <div class="source-detail">${escapeHtml(card.label || '来源')}${detail ? ' · ' + escapeHtml(detail) : ''}</div>
    </li>`;
  }).join('');
  return `<div class="source-card"><div class="source-card-title">引用来源</div><ul class="source-list source-list--compact">${items}</ul></div>`;
}

// 外部情报区块：有数据才渲染；仅 http(s) 链接可点击（协议白名单，防 javascript: 等危险 scheme）
function intelBlockHtml(intel) {
  if (!Array.isArray(intel) || !intel.length) return '';
  const items = intel.map((i) => {
    const url = String(i.url || '');
    const link = /^https?:\/\//i.test(url)
      ? ` · <a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(i.source_name || '链接')}</a>`
      : '';
    return `<li>${escapeHtml(i.title || '')}${link}<div class="intel-snippet">${escapeHtml(i.snippet || '')}</div></li>`;
  }).join('');
  return `
  <div class="card intel-block">
    <div class="source-card-title">外部情报</div>
    <ul class="source-list">
      ${items}
    </ul>
  </div>`;
}

function copyText(text) {
  navigator.clipboard.writeText(text).catch(() => {});
  showToast('📋 已复制到剪贴板', 'success');
}

function setLoading(btnId, isLoading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>处理中...';
  } else {
    btn.textContent = btn.dataset.originalText || btn.textContent;
  }
}

function showPage(page) {
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  const target = document.getElementById(page);
  if (target) target.classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === page);
  });
  if (page === 'dashboard-page') loadDashboard();
  if (window.innerWidth <= 860) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('show');
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 200);
  }, 2500);
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('show');
}

async function fetchCurrentUser() {
  if (!authToken) return null;
  try {
    const data = await api('/api/v1/auth/me');
    currentUser = data.data || null;
    return currentUser;
  } catch (e) {
    return null;
  }
}

function applyRoleVisibility() {
  const isAdmin = currentUser?.role === 'admin';
  document.querySelectorAll('[data-admin-only]').forEach(el => {
    el.style.display = isAdmin ? '' : 'none';
  });
}

async function refreshUserAndVisibility() {
  await fetchCurrentUser();
  applyRoleVisibility();
}

// ─── 客户列表 ───

async function loadCustomers() {
  const data = await api('/api/v1/customers');
  customerCache = data.data || [];
  const tbody = document.getElementById('customer-table-body');
  if (!tbody) return;
  tbody.innerHTML = customerCache.map(item => `
    <tr data-name="${escapeHtml(item.name || '')}" data-type="${escapeHtml(item.primary_type || '')}" data-stage="${escapeHtml(item.stage || '')}">
      <td>${item.id}</td>
      <td>${escapeHtml(item.name || '')}</td>
      <td>${escapeHtml(item.industry || '-')}</td>
      <td>${escapeHtml(item.stage || '-')}</td>
      <td>${escapeHtml(item.primary_type || '-')}</td>
      <td>
        <span class="button-stack">
          <button class="sm secondary" onclick="viewCustomerDetail(${item.id})">详情</button>
          <button class="sm" onclick="openBriefing(${item.id})">简报</button>
          <button class="sm" onclick="openAssist(${item.id})">会中</button>
          <button class="sm" onclick="openFollowup(${item.id})">跟进</button>
        </span>
      </td>
    </tr>
  `).join('');
  filterCustomers();
}

function filterCustomers() {
  const search = (document.getElementById('customer-search')?.value || '').toLowerCase();
  const typeFilter = document.getElementById('filter-type')?.value || '';
  const stageFilter = document.getElementById('filter-stage')?.value || '';
  const rows = document.querySelectorAll('#customer-table-body tr');
  let visibleCount = 0;
  rows.forEach(row => {
    const name = (row.dataset.name || '').toLowerCase();
    const type = row.dataset.type || '';
    const stage = row.dataset.stage || '';
    const matchSearch = !search || name.includes(search);
    const matchType = !typeFilter || type === typeFilter;
    const matchStage = !stageFilter || stage === stageFilter;
    row.style.display = (matchSearch && matchType && matchStage) ? '' : 'none';
    if (matchSearch && matchType && matchStage) visibleCount++;
  });
  const empty = document.getElementById('customer-empty');
  if (empty) empty.style.display = visibleCount ? 'none' : 'block';
}

// ─── 客户详情 ───

async function loadCustomerDetail() {
  const id = currentCustomerId || document.getElementById('customer-detail-id')?.value;
  const container = document.getElementById('customer-detail');
  if (!id || !container) return;
  try {
    const [customer, interactions, briefings] = await Promise.all([
      api(`/api/v1/customers/${id}`),
      api(`/api/v1/customers/${id}/interactions`).catch(() => ({data: []})),
      api(`/api/v1/customers/${id}/briefing-history`).catch(() => ({data: []})),
    ]);
    const rows = (interactions.data || []).slice().reverse().map(item => `
      <tr>
        <td>${escapeHtml(item.created_at?.slice(0, 19) || '-')}</td>
        <td>${escapeHtml(item.stage || '-')}</td>
        <td>${escapeHtml(item.summary || '-')}</td>
        <td>${escapeHtml(item.decisions || '-')}</td>
        <td>${escapeHtml(item.pending_actions || '-')}</td>
      </tr>
    `).join('');
    const briefingRows = (briefings.data || []).slice().reverse().map(item => {
      // 历史表格列宽紧张：外情只显计数徽标，点击进简报详情看全量
      const intelCount = Array.isArray(item.external_intel) ? item.external_intel.length : 0;
      return `
      <tr>
        <td>${escapeHtml(item.created_at?.slice(0, 19) || '-')}</td>
        <td>${escapeHtml(item.primary_type || '-')}</td>
        <td>${escapeHtml(item.focus || item.opening_line || '-')}</td>
        <td>${escapeHtml((item.recommended_cases || []).map(x => x.title).join('、') || '-')}</td>
        <td>${sourceCardsHtml(item.llm_source_cards || [])}${intelCount ? `<span class="intel-badge" onclick="openBriefing(${item.customer_id})">外情×${intelCount}</span>` : ''}</td>
      </tr>
    `;
    }).join('');
    container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h3 style="margin:0;font-size:18px;">${escapeHtml(customer.name || id)}</h3>
        <button class="sm secondary" onclick="openTypeForm(${customer.id})">修改类型</button>
      </div>
      <div class="grid" style="margin-bottom:16px;">
        <div><strong>行业：</strong>${escapeHtml(customer.industry || '-')}</div>
        <div><strong>阶段：</strong>${escapeHtml(customer.stage || '-')}</div>
        <div><strong>区域：</strong>${escapeHtml(customer.region || '-')}</div>
        <div><strong>主类型：</strong>${escapeHtml(customer.primary_type || '-')}</div>
        <div><strong>次类型：</strong>${escapeHtml(customer.secondary_type || '-')}</div>
        <div><strong>类型依据：</strong>${escapeHtml(customer.type_evidence || '-')}</div>
      </div>
      <h4 style="margin:16px 0 8px;font-size:16px;">会前简报历史</h4>
      <div style="overflow-x:auto;">
        <table>${briefingRows ? `<thead><tr><th>时间</th><th>类型</th><th>重点</th><th>案例</th><th>来源</th></tr></thead><tbody>${briefingRows}</tbody>` : '<p class="muted">暂无会前简报</p>'}</table>
      </div>
      <h4 style="margin:16px 0 8px;font-size:16px;">互动记录</h4>
      <div style="overflow-x:auto;">
        <table>${rows ? `<thead><tr><th>时间</th><th>阶段</th><th>摘要</th><th>决策</th><th>待办</th></tr></thead><tbody>${rows}</tbody>` : '<p class="muted">暂无互动记录</p>'}</table>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `<p style="color:#dc2626;">加载客户详情失败：${e.message}</p>`;
  }
}

// ─── 客户创建 ───

async function createCustomer() {
  const payload = {
    name: document.getElementById('cust-name').value.trim(),
    industry: document.getElementById('cust-industry').value.trim(),
    revenue_range: document.getElementById('cust-revenue').value.trim(),
    stage: document.getElementById('cust-stage').value.trim(),
    region: '',
  };
  if (!payload.name) return showToast('请填写客户名称', 'error');
  setLoading('create-customer', true);
  try {
    await api('/api/v1/customers', { method: 'POST', body: JSON.stringify(payload) });
    document.getElementById('customer-form').reset();
    await loadCustomers();
    refreshDashboard();
    showToast('客户创建成功', 'success');
  } catch (e) {
    showToast(e.message);
  } finally {
    setLoading('create-customer', false);
  }
}

// ─── 类型更新 ───

async function updateCustomerType(customerId) {
  const payload = {
    primary_type: document.getElementById('type-primary').value,
    secondary_type: document.getElementById('type-secondary').value,
    type_confidence: parseFloat(document.getElementById('type-confidence').value || '0'),
    type_evidence: document.getElementById('type-evidence').value,
  };
  if (!payload.primary_type) return showToast('请选择主类型', 'error');
  try {
    await api(`/api/v1/customers/${customerId}/type`, { method: 'PATCH', body: JSON.stringify(payload) });
    await loadCustomers();
    closeModal('type-modal');
    showToast('类型已更新', 'success');
  } catch (e) {
    showToast(e.message);
  }
}

// ─── 会前/会中/会后 ───

async function renderBriefing(customerId) {
  const sessionId = currentSessionId ? `&session_id=${encodeURIComponent(currentSessionId)}` : '';
  const data = await api(`/api/v1/customers/${customerId}/briefing?${sessionId}`, { method: 'POST' });
  const payload = data.data || {};
  const sourceCards = sourceCardsHtml(payload.llm_source_cards || []);
  // 外部情报区块：有数据才渲染，不占空态版面
  const intelHtml = intelBlockHtml(payload.external_intel);
  const container = document.getElementById('briefing-result');
  container.innerHTML = `
    <div class="result-block">
      <h3>${escapeHtml(payload.customer_name || customerId)}</h3>
      <p><strong>类型：</strong>${escapeHtml(payload.primary_type || '待判断')}${payload.secondary_type ? ' / ' + escapeHtml(payload.secondary_type) : ''} <span class="badge ${payload.confidence ? 'badge-green' : 'badge-gray'}">置信度 ${payload.confidence ?? '-'}</span></p>
      <p><strong>判断依据：</strong>${escapeHtml(payload.evidence || '-')}</p>
      <p><strong>破冰话术：</strong>${escapeHtml(payload.opening_line || '-')} ${payload.opening_line ? `<button class="copy-btn" data-copy="${escapeHtml(payload.opening_line)}">📋 复制</button>` : ''}</p>
      <p><strong>重点方向：</strong>${escapeHtml(payload.focus || '-')}</p>
      <p><strong>下一步：</strong>${escapeHtml(payload.next_step || '-')}</p>
      <p><strong>潜在异议：</strong>${escapeHtml((payload.potential_objections || []).join('；') || '-')}</p>
      <p><strong>推荐案例：</strong>${escapeHtml((payload.recommended_cases || []).map(x => x.title).join('、') || '-')}</p>
      ${sourceCards}
      ${intelHtml}
      <p class="muted" style="font-size:12px; margin-top:8px;">LLM 输出：${escapeHtml((payload.llm_text || '未生成').slice(0, 200))}</p>
    </div>
  `;
  container.style.display = 'block';
  await loadChatSessions();
  await loadCustomerDetail();
}

async function renderAssist(customerId) {
  const payload = {
    current_stage: document.getElementById('assist-stage').value,
    transcript: document.getElementById('assist-transcript').value,
    customer_type: document.getElementById('assist-type')?.value || '',
  };
  const data = await api(`/api/v1/customers/${customerId}/assist`, { method: 'POST', body: JSON.stringify(payload) });
  const out = data.data || {};
  const sourceCards = sourceCardsHtml(out.source_cards || []);
  const container = document.getElementById('assist-result');
  container.innerHTML = `
    <div class="result-block">
      <h3>会中辅助</h3>
      <p><strong>阶段：</strong>${escapeHtml(out.current_stage || '-')} → 检测到 <strong>${escapeHtml(out.detected_stage || '-')}</strong></p>
      <p><strong>阶段提示：</strong>${escapeHtml(out.stage_guidance || '-')}</p>
      <p><strong>建议话术：</strong>${escapeHtml(out.suggested_response || '-')} ${out.suggested_response ? `<button class="copy-btn" data-copy="${escapeHtml(out.suggested_response)}">📋 复制</button>` : ''}</p>
      <p><strong>异议：</strong>${escapeHtml(out.objection_detected || '未识别')}</p>
      <p><strong>异议应答：</strong>${escapeHtml(out.objection_response || '-')}</p>
      <p><strong>备注：</strong>${escapeHtml((out.notes || []).join(' / ') || '-')}</p>
      ${sourceCards}
    </div>
  `;
  container.style.display = 'block';
}

function getTagValues(group) {
  return Array.from(selectedTags[group]).join('；');
}

async function renderFollowup(customerId) {
  const payload = {
    summary: document.getElementById('followup-summary').value,
    decisions: getTagValues('decisions') ? getTagValues('decisions').split(/；/) : [],
    pending_actions: getTagValues('actions') ? getTagValues('actions').split(/；/) : [],
    transcript: document.getElementById('followup-transcript').value,
    customer_type: '',
  };
  const data = await api(`/api/v1/customers/${customerId}/followup`, { method: 'POST', body: JSON.stringify(payload) });
  const out = data.data || {};
  const sourceCards = sourceCardsHtml(out.source_cards || []);
  const container = document.getElementById('followup-result');
  container.innerHTML = `
    <div class="result-block">
      <h3>会后跟进</h3>
      <p><strong>摘要：</strong>${escapeHtml(out.summary || '-')}</p>
      <p><strong>决策：</strong>${escapeHtml((out.decisions || []).join('；') || '-')}</p>
      <p><strong>任务：</strong>${escapeHtml((out.tasks || []).map(x => `${x.title}(${x.deadline})`).join('；') || '-')}</p>
      <p><strong>邮件草稿：</strong>${escapeHtml(out.followup_email || '-')}</p>
      <p><strong>微信跟进：</strong>${escapeHtml(out.followup_wechat || '-')}</p>
      <p><strong>知识沉淀建议：</strong>${escapeHtml(out.knowledge_update_suggestion || '-')}</p>
      ${sourceCards}
    </div>
  `;
  container.style.display = 'block';
}

// ─── 渲染会议结果 ───

function renderMeetingResult(payload) {
  const container = document.getElementById('meeting-result');
  if (!container) return;
  const type = payload.primary_type || payload.current_stage || '待判断';
  const sourceCards = payload.llm_source_cards
    ? sourceCardsHtml(Array.isArray(payload.llm_source_cards) ? payload.llm_source_cards : JSON.parse(payload.llm_source_cards || '[]'))
    : '';
  // 外部情报区块：简报响应才有该键，会中/会后 payload 无此键时自然不渲染
  const intelHtml = intelBlockHtml(payload.external_intel);
  if (payload.opening_line !== undefined || payload.suggested_response !== undefined) {
    const line = payload.opening_line || payload.suggested_response || '-';
    container.innerHTML = `
      <div class="result-block">
        <h3>${escapeHtml(type)}</h3>
        ${payload.customer_name ? `<p><strong>客户：</strong>${escapeHtml(payload.customer_name)}</p>` : ''}
        ${payload.focus ? `<p><strong>重点方向：</strong>${escapeHtml(payload.focus)}</p>` : ''}
        ${payload.next_step ? `<p><strong>下一步：</strong>${escapeHtml(payload.next_step)}</p>` : ''}
        ${payload.potential_objections ? `<p><strong>潜在异议：</strong>${escapeHtml(Array.isArray(payload.potential_objections) ? payload.potential_objections.join('；') : String(payload.potential_objections))}</p>` : ''}
        <p><strong>建议话术：</strong>${escapeHtml(line)} <button class="copy-btn" data-copy="${escapeHtml(line)}">📋 复制</button></p>
        ${payload.llm_text ? `<p class="muted" style="font-size:12px; margin-top:8px;">LLM 输出：${escapeHtml(String(payload.llm_text).slice(0, 200))}</p>` : ''}
        ${sourceCards}
        ${intelHtml}
      </div>
    `;
  } else {
    container.innerHTML = `<p class="muted">未生成有效结果</p>`;
  }
  container.style.display = 'block';
}

// 全局复制按钮事件委托
document.addEventListener('click', (e) => {
  if (e.target.matches('[data-copy]')) {
    copyText(e.target.dataset.copy);
    e.target.textContent = '已复制';
    setTimeout(() => { e.target.textContent = '📋 复制'; }, 1500);
  }
});

// ─── 模态框 ───

function openBriefing(customerId) {
  document.getElementById('briefing-result').style.display = 'none';
  document.getElementById('briefing-result').innerHTML = '<p class="muted"><span class="spinner" style="border-color:#6b7280;border-top-color:transparent;"></span> 正在生成会前简报...</p>';
  document.getElementById('briefing-modal').style.display = 'flex';
  renderBriefing(customerId);
}
function openAssist(customerId) {
  document.getElementById('assist-result').style.display = 'none';
  document.getElementById('assist-modal').style.display = 'flex';
  document.getElementById('assist-form').dataset.customerId = customerId;
}
function openFollowup(customerId) {
  document.getElementById('followup-result').style.display = 'none';
  document.getElementById('followup-modal').style.display = 'flex';
  document.getElementById('followup-form').dataset.customerId = customerId;
}
function openTypeForm(customerId) {
  const customer = customerCache.find(c => c.id === customerId);
  if (customer) {
    document.getElementById('type-primary').value = customer.primary_type || '';
    document.getElementById('type-secondary').value = customer.secondary_type || '';
    document.getElementById('type-confidence').value = customer.type_confidence ?? '';
    document.getElementById('type-evidence').value = customer.type_evidence || '';
  }
  document.getElementById('type-form').dataset.customerId = customerId;
  document.getElementById('type-modal').style.display = 'flex';
}
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}
function logout() {
  authToken = null;
  localStorage.removeItem('access_token');
  currentUser = null;
  currentSessionId = null;
  currentCustomerId = null;
  customerCache = [];
  showPage('login-page');
}

function viewCustomerDetail(customerId) {
  currentCustomerId = customerId;
  showPage('customer-detail-page');
  loadCustomerDetail();
}

// ─── 一键分析 ───

async function quickAnalyze() {
  const name = document.getElementById('analyze-name').value.trim();
  if (!name) return showToast('请输入客户名称', 'error');
  const industry = document.getElementById('analyze-industry').value.trim();
  const stage = document.getElementById('analyze-stage').value.trim();
  const container = document.getElementById('analyze-result');
  container.style.display = 'block';
  container.innerHTML = '<p class="muted"><span class="spinner" style="border-color:#6b7280;border-top-color:transparent;"></span> 正在分析中...</p>';
  setLoading('quick-analyze-btn', true);
  try {
    const payload = { name, industry, stage };
    const data = await api('/api/v1/analyze', { method: 'POST', body: JSON.stringify(payload) });
    const out = data.data || {};
    const b = out.briefing || {};
    const sourceCards = sourceCardsHtml(b.llm_source_cards || []);
    // 外部情报区块：有数据才渲染，不占空态版面
    const intelHtml = intelBlockHtml(b.external_intel);
    container.innerHTML = `
      <div class="result-block">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
          ${out.is_new ? '<span class="badge badge-green">新客户</span>' : '<span class="badge badge-gray">已有客户</span>'}
          <span style="font-weight:600;font-size:16px;">${escapeHtml(out.customer_name || name)}</span>
        </div>
        <p><strong>类型：</strong>${escapeHtml(out.primary_type || '待判断')}${out.secondary_type ? ' / ' + escapeHtml(out.secondary_type) : ''}</p>
        <p><strong>置信度：</strong><span class="badge badge-green">${escapeHtml(String(out.type_confidence ?? '-'))}</span></p>
        <p><strong>判断依据：</strong>${escapeHtml(out.type_evidence || '-')}</p>
        <p><strong>破冰话术：</strong>${escapeHtml(b.opening_line || '-')} ${b.opening_line ? `<button class="copy-btn" data-copy="${escapeHtml(b.opening_line)}">📋 复制</button>` : ''}</p>
        <p><strong>重点方向：</strong>${escapeHtml(b.focus || '-')}</p>
        <p><strong>下一步：</strong>${escapeHtml(b.next_step || '-')}</p>
        <p><strong>潜在异议：</strong>${escapeHtml((b.potential_objections || []).join('；') || '-')}</p>
        ${sourceCards}
        ${intelHtml}
      </div>
    `;
    await loadCustomers();
    await populateCustomerSelects();
    refreshDashboard();
    showToast('分析完成', 'success');
  } catch (e) {
    container.innerHTML = `<p style="color:#dc2626;">分析失败：${e.message}</p>`;
    showToast(e.message);
  } finally {
    setLoading('quick-analyze-btn', false);
  }
}

function smartDetect() {
  const name = document.getElementById('analyze-name').value.trim() || '飞鹤奶粉';
  const options = getOptions();
  const industrySelect = document.getElementById('analyze-industry');
  const stageSelect = document.getElementById('analyze-stage');
  if (industrySelect && options.industries && options.industries.includes('母婴')) {
    industrySelect.value = '母婴';
  }
  if (stageSelect && options.stages && options.stages.includes('扩张期')) {
    stageSelect.value = '扩张期';
  }
  const revenueSelect = document.getElementById('analyze-revenue');
  if (revenueSelect) revenueSelect.value = '10亿以上';
  showToast('✨ 已根据知识库预填客户信息', 'success');
}

// ─── 聊天 ───

function appendChatBubble(role, text, extraHtml = '') {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  const div = document.createElement('div');
  div.className = `agent-msg ${role === 'user' ? 'agent-user' : 'agent-ai'}`;
  div.innerHTML = `${escapeHtml(text)}${extraHtml ? '<div class="source-card-embed">' + extraHtml + '</div>' : ''}`;
  box.appendChild(div);
  box.parentElement.scrollTop = box.parentElement.scrollHeight;
}

async function createChatSession() {
  const customerId = Number(document.getElementById('chat-customer')?.value || 0) || null;
  const titleInput = document.getElementById('chat-new-title')?.value?.trim();
  const payload = { customer_id: customerId || null };
  if (titleInput) payload.title = titleInput;
  const data = await api('/api/v1/chat/sessions', { method: 'POST', body: JSON.stringify(payload) });
  currentSessionId = data.id;
  await loadChatSessions();
  await openChatSession(data.id, data.customer_id, data.title);
  appendChatBubble('assistant', `会话已创建：${data.title || data.id}，可以开始提问。`);
}

async function loadChatSessions() {
  try {
    const customerId = Number(document.getElementById('chat-customer')?.value || 0) || null;
    const data = await api(`/api/v1/chat/sessions${customerId ? `?customer_id=${customerId}` : ''}`);
    const list = document.getElementById('chat-session-list');
    if (!list) return;
    const items = data.data || [];
    document.getElementById('chat-empty-hint').style.display = items.length ? 'none' : 'block';
    list.innerHTML = items.map(item => {
      const title = escapeHtml(item.title || `会话 #${item.id}`);
      return `<li style="margin-bottom:6px;" data-session-id="${item.id}" data-customer-id="${item.customer_id || ''}" data-title="${escapeHtml(item.title || '')}">
        <button class="open-session-btn" style="width:auto; margin:0; padding:4px 8px; font-size:13px;">${title}</button>
        <span class="button-stack" style="margin-left:4px;">
          <button class="sm secondary" onclick="renameChatSession(${item.id})">重命名</button>
          <button class="sm secondary" onclick="deleteChatSession(${item.id})">删除</button>
        </span>
      </li>`;
    }).join('');
  } catch (e) { console.error('loadChatSessions:', e); }
}

async function renameChatSession(sessionId) {
  const li = document.querySelector(`li[data-session-id="${sessionId}"]`);
  const current = li?.querySelector('.open-session-btn')?.textContent?.trim() || `会话 #${sessionId}`;
  const title = prompt('会话标题', current);
  if (title === null) return;
  const data = await api(`/api/v1/chat/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify({ title: title || '' }) });
  await loadChatSessions();
  if (currentSessionId === sessionId) {
    appendChatBubble('assistant', `标题已更新为：${data.title || sessionId}`);
  }
}

async function deleteChatSession(sessionId) {
  if (!confirm('确定删除该会话吗？')) return;
  try {
    await api(`/api/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
    if (currentSessionId === sessionId) {
      currentSessionId = null;
      document.getElementById('chat-messages').innerHTML = '<p class="muted">请选择或新建一个会话。</p>';
    }
    await loadChatSessions();
    showToast('会话已删除', 'success');
  } catch (e) {
    showToast(e.message);
  }
}

async function openChatSession(sessionId, customerId, title) {
  currentSessionId = sessionId;
  if (customerId) currentCustomerId = customerId;
  const input = document.getElementById('chat-input');
  if (input) input.value = '';
  const label = document.getElementById('active-session-title');
  if (label) label.textContent = title ? `当前会话：${title}` : `当前会话：${sessionId}`;
  await loadChatMessages(sessionId);
}

async function loadChatMessages(sessionId) {
  try {
    const data = await api(`/api/v1/chat/sessions/${sessionId}/messages`);
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    (data.data || []).forEach((item) => {
      let extraHtml = '';
      if (item.role === 'assistant') {
        try {
          const meta = JSON.parse(item.meta || '{}');
          const cards = Array.isArray(meta.source_cards) ? meta.source_cards : [];
          if (cards.length) extraHtml = sourceCardsHtml(cards);
        } catch (e) { console.error(e); }
      }
      appendChatBubble(item.role, item.content, extraHtml);
    });
    if (!container.children.length) {
      container.innerHTML = '<p class="muted">暂无消息，请直接输入销售问题。</p>';
    }
    container.parentElement.scrollTop = container.parentElement.scrollHeight;
  } catch (e) { console.error('loadChatMessages:', e); }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const text = (input.value || '').trim();
  if (!text) return;
  let sessionId = currentSessionId || Number(document.getElementById('chat-session-id')?.value || 0);
  if (!sessionId) {
    await createChatSession();
    sessionId = currentSessionId;
  }
  appendChatBubble('user', text);
  input.value = '';
  setLoading('chat-send', true);
  try {
    const data = await api(`/api/v1/chat/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({role:'user', content:text}) });
    const reply = data.message || {};
    const cards = sourceCardsHtml(data.source_cards || []);
    appendChatBubble('assistant', reply.content || '未收到回复', cards);
    await loadChatSessions();
  } catch (e) {
    showToast(e.message);
  } finally {
    setLoading('chat-send', false);
  }
}

// ─── 知识库 ───

async function loadKnowledgeCases() {
  try {
    const data = await api('/api/v1/knowledge/cases');
    const tbody = document.getElementById('knowledge-case-table-body');
    if (!tbody) return;
    tbody.innerHTML = (data.data || []).map(item => `
      <tr><td>${escapeHtml(item.code||'')}</td><td>${escapeHtml(item.title||'')}</td><td>${escapeHtml(item.type||'')}</td><td>${escapeHtml(item.industry||'')}</td><td>${escapeHtml(item.result||'')}</td><td>${escapeHtml(item.source||'')}</td></tr>
    `).join('');
  } catch (e) { console.error('loadKnowledgeCases:', e); }
}

async function createKnowledgeCase() {
  const payload = {
    code: document.getElementById('case-code').value.trim(),
    title: document.getElementById('case-title').value.trim(),
    type: document.getElementById('case-type').value.trim(),
    industry: document.getElementById('case-industry').value.trim(),
    stage: document.getElementById('case-stage').value.trim(),
    result: document.getElementById('case-result').value.trim(),
    source: document.getElementById('case-source').value.trim(),
  };
  if (!payload.code || !payload.title) return showToast('请填写案例编码和标题', 'error');
  try {
    await api('/api/v1/knowledge/cases', { method: 'POST', body: JSON.stringify(payload) });
    document.getElementById('knowledge-case-form').reset();
    loadKnowledgeCases();
    showToast('案例已保存', 'success');
  } catch (e) {
    showToast(e.message);
  }
}

async function loadKnowledgeScripts() {
  try {
    const data = await api('/api/v1/knowledge/scripts');
    const tbody = document.getElementById('knowledge-script-table-body');
    if (!tbody) return;
    tbody.innerHTML = (data.data || []).map(item => `
      <tr><td>${escapeHtml(item.scene||'')}</td><td>${escapeHtml(item.type||'')}</td><td>${escapeHtml(item.template||'')}</td><td>${escapeHtml(item.source||'')}</td></tr>
    `).join('');
  } catch (e) { console.error('loadKnowledgeScripts:', e); }
}

async function createKnowledgeScript() {
  const payload = {
    scene: document.getElementById('script-scene').value.trim(),
    type: document.getElementById('script-type').value.trim(),
    template: document.getElementById('script-template').value.trim(),
    source: document.getElementById('script-source').value.trim(),
  };
  if (!payload.type || !payload.template) return showToast('请选择客户类型并填写话术', 'error');
  try {
    await api('/api/v1/knowledge/scripts', { method: 'POST', body: JSON.stringify(payload) });
    document.getElementById('knowledge-script-form').reset();
    loadKnowledgeScripts();
    showToast('话术已保存', 'success');
  } catch (e) {
    showToast(e.message);
  }
}

// ─── Dashboard ───

async function refreshDashboard() {
  try {
    const [interactions, briefings] = await Promise.all([
      api('/api/v1/knowledge/cases'),
      api('/api/v1/knowledge/scripts'),
    ]);
    const kpiCustomers = document.getElementById('kpi-customers');
    const kpiBriefing = document.getElementById('kpi-briefing');
    const kpiInteractions = document.getElementById('kpi-interactions');
    const kpiFollowup = document.getElementById('kpi-followup');
    if (kpiCustomers) kpiCustomers.textContent = customerCache.length;
    if (kpiBriefing) kpiBriefing.textContent = customerCache.length;
    if (kpiInteractions) kpiInteractions.textContent = (interactions.data || []).length;
    if (kpiFollowup) kpiFollowup.textContent = (briefings.data || []).length;
  } catch (e) {
    console.error(e);
  }
}

// ─── 快速助手 ───

async function askAgent() {
  const input = document.getElementById('agent-input');
  const text = (input.value || '').trim();
  if (!text) return;
  appendChatBubble('user', text);
  input.value = '';
  setTimeout(() => {
    appendChatBubble('ai', `已收到你的问题：${text}。建议使用"客户分析"功能获取专业建议。`);
  }, 300);
}

function quickAsk(text) {
  document.getElementById('agent-input').value = text;
  askAgent();
}

// ─── 辅助函数 ───

async function populateCustomerSelects() {
  const selects = ['chat-customer', 'meeting-customer', 'followup-customer'];
  for (const id of selects) {
    const sel = document.getElementById(id);
    if (!sel) continue;
    const options = customerCache.map(item => {
      const type = item.primary_type ? `（${item.primary_type}）` : '';
      return `<option value="${item.id}">${item.id} - ${escapeHtml(item.name || '未命名')} ${type}</option>`;
    }).join('');
    const base = '<option value="">选择客户</option>';
    sel.innerHTML = base + options;
  }
}

function onMeetingCustomerChange() {
  const sel = document.getElementById('meeting-customer');
  const val = sel.value;
  const customer = customerCache.find(c => String(c.id) === String(val));
  if (customer) {
    document.getElementById('meeting-type').value = customer.primary_type || '';
    document.getElementById('meeting-industry').value = customer.industry || '';
  } else {
    document.getElementById('meeting-type').value = '';
    document.getElementById('meeting-industry').value = '';
  }
}

function clearMeetingResult() {
  const container = document.getElementById('meeting-result');
  if (container) {
    container.innerHTML = '<span class="muted">请在左侧选择客户和动作。</span>';
    container.style.display = 'block';
  }
}

function importFromAssist() {
  const transcript = document.getElementById('assist-transcript')?.value || '';
  document.getElementById('followup-summary').value = transcript || '客户对品牌认知测试方案感兴趣，但关注投入产出比。';
  showToast('📥 已从会中辅助导入会议摘要', 'success');
}

function toggleTag(el) {
  const group = el.dataset.group;
  const text = el.textContent.trim();
  if (selectedTags[group].has(text)) {
    selectedTags[group].delete(text);
    el.classList.remove('selected');
  } else {
    selectedTags[group].add(text);
    el.classList.add('selected');
  }
  updateSelectedSummary(group);
}

function updateSelectedSummary(group) {
  const summary = document.getElementById(group + '-summary');
  const selected = document.getElementById(group + '-selected');
  const arr = Array.from(selectedTags[group]);
  if (arr.length) {
    summary.style.display = 'flex';
    selected.textContent = arr.join('、');
  } else {
    summary.style.display = 'none';
  }
}

function clearGroup(group) {
  selectedTags[group].clear();
  document.querySelectorAll(`[data-group="${group}"]`).forEach(el => el.classList.remove('selected'));
  updateSelectedSummary(group);
}

function autoGenCode() {
  const code = 'CASE_' + String(Date.now()).slice(-6);
  const input = document.getElementById('case-code');
  if (input) input.value = code;
  showToast(`已生成编码：${code}`, 'success');
}

function skipLogin() {
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('workbench-page').style.display = 'block';
  showPage('home-page');
  showToast('欢迎预览原型！', 'success');
}

// ─── 数据看板 ───
async function loadDashboard() {
  try {
    const data = await api('/api/v1/dashboard/stats');
    const stats = data.data || {};

    // 更新 KPI 卡片
    document.getElementById('dash-customers').textContent = stats.total_customers || 0;
    document.getElementById('dash-briefings').textContent = stats.total_briefings || 0;
    document.getElementById('dash-interactions').textContent = stats.total_interactions || 0;
    document.getElementById('dash-followups').textContent = stats.followups_with_summary || 0;

    // 渲染类型分布饼图（简化版：条形图）
    renderTypeChart(stats.type_distribution || []);

    // 渲染趋势图
    renderTrendChart(stats.briefing_trend || []);

    // 渲染详细表格
    renderTypeTable(stats.type_distribution || []);

    // 显示内容，隐藏加载状态
    document.getElementById('dashboard-loading').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
  } catch (e) {
    console.error('Dashboard load error:', e);
    document.getElementById('dashboard-loading').innerHTML = `<p style="color:#dc2626;">加载失败：${e.message}</p>`;
  }
}

function renderTypeChart(distribution) {
  const container = document.getElementById('type-chart');
  if (!container || !distribution.length) {
    if (container) container.innerHTML = '<p class="muted">暂无数据</p>';
    return;
  }

  const total = distribution.reduce((sum, item) => sum + item.count, 0);
  const colors = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#4f46e5', '#0891b2', '#7c3aed'];

  let html = '<div style="display:flex; flex-direction:column; gap:10px;">';
  distribution.forEach((item, idx) => {
    const pct = total > 0 ? Math.round(item.count / total * 100) : 0;
    const color = colors[idx % colors.length];
    html += `
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="width:100px; font-size:13px; color:#374151;">${escapeHtml(item.type)}</span>
        <div style="flex:1; height:24px; background:#f3f4f6; border-radius:12px; overflow:hidden;">
          <div style="height:100%; width:${pct}%; background:${color}; border-radius:12px; transition:width 0.5s;"></div>
        </div>
        <span style="width:60px; text-align:right; font-size:13px; font-weight:600;">${item.count}</span>
        <span style="width:40px; text-align:right; font-size:12px; color:#6b7280;">${pct}%</span>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;
}

function renderTrendChart(trend) {
  const container = document.getElementById('trend-chart');
  if (!container || !trend.length) {
    if (container) container.innerHTML = '<p class="muted">暂无数据</p>';
    return;
  }

  const maxCount = Math.max(...trend.map(t => t.count), 1);
  const height = 150;
  const barWidth = Math.min(40, Math.max(20, 300 / trend.length));

  let html = '<div style="display:flex; align-items:flex-end; gap:8px; height:' + (height + 30) + 'px; padding-top:10px;">';
  trend.forEach((item, idx) => {
    const barHeight = (item.count / maxCount) * height;
    html += `
      <div style="display:flex; flex-direction:column; align-items:center; flex:1;">
        <span style="font-size:11px; color:#6b7280; margin-bottom:4px;">${item.count}</span>
        <div style="width:${barWidth}px; height:${barHeight}px; background:#2563eb; border-radius:4px 4px 0 0;"></div>
        <span style="font-size:11px; color:#6b7280; margin-top:4px; writing-mode:vertical-rl; text-orientation:mixed;">${item.date}</span>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;
}

function renderTypeTable(distribution) {
  const tbody = document.getElementById('type-table-body');
  if (!tbody) return;

  const total = distribution.reduce((sum, item) => sum + item.count, 0);
  tbody.innerHTML = distribution.map(item => {
    const pct = total > 0 ? Math.round(item.count / total * 100) : 0;
    return `<tr>
      <td>${escapeHtml(item.type)}</td>
      <td>${item.count}</td>
      <td>${pct}%</td>
    </tr>`;
  }).join('');
}

// ─── 语音转写 ───
let recognition = null;
let isRecording = false;

function initVoiceRecognition() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    console.warn('浏览器不支持语音识别');
    return null;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SpeechRecognition();
  rec.lang = 'zh-CN';
  rec.continuous = true;
  rec.interimResults = true;

  let finalTranscript = '';

  rec.onstart = () => {
    isRecording = true;
    const btn = document.getElementById('voice-btn');
    const status = document.getElementById('voice-status');
    if (btn) {
      btn.classList.add('voice-recording');
      btn.textContent = '⏹ 停止';
    }
    if (status) status.textContent = '🔴 正在录音...';
  };

  rec.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interim += transcript;
      }
    }
    const textarea = document.getElementById('assist-transcript');
    if (textarea) {
      textarea.value = finalTranscript + interim;
    }
  };

  rec.onerror = (event) => {
    console.error('语音识别错误:', event.error);
    stopVoiceRecognition();
    if (event.error === 'not-allowed') {
      showToast('请允许麦克风权限', 'error');
    } else if (event.error !== 'aborted') {
      showToast(`语音识别错误: ${event.error}`, 'error');
    }
  };

  rec.onend = () => {
    if (isRecording) {
      // 意外结束，重新启动
      try { rec.start(); } catch (e) {}
    }
  };

  return rec;
}

function toggleVoiceRecognition() {
  if (!recognition) {
    recognition = initVoiceRecognition();
    if (!recognition) {
      showToast('您的浏览器不支持语音识别，请使用 Chrome 或 Edge', 'error');
      return;
    }
  }

  if (isRecording) {
    stopVoiceRecognition();
  } else {
    try {
      recognition.start();
      showToast('已开始语音识别，请说话...', 'info');
    } catch (e) {
      console.error(e);
    }
  }
}

function stopVoiceRecognition() {
  isRecording = false;
  if (recognition) {
    try { recognition.stop(); } catch (e) {}
  }
  const btn = document.getElementById('voice-btn');
  const status = document.getElementById('voice-status');
  if (btn) {
    btn.classList.remove('voice-recording');
    btn.textContent = '🎤 语音输入';
  }
  if (status) status.textContent = '';
}

// ─── 初始化 ───

document.addEventListener('DOMContentLoaded', async () => {
  if (authToken) {
    const user = await fetchCurrentUser();
    if (!user) {
      authToken = null;
      localStorage.removeItem('access_token');
      showPage('login-page');
    } else {
      showPage('workbench-page');
      applyRoleVisibility();
      await loadOptions();
      await loadCustomers();
      await populateCustomerSelects();
      loadKnowledgeCases();
      loadKnowledgeScripts();
      refreshDashboard();
      await loadChatSessions();
      const detail = document.getElementById('customer-detail');
      if (detail) detail.innerHTML = '<p class="muted">请在客户画像选择一条客户查看详情。</p>';
      const roleLabel = document.getElementById('current-role');
      if (roleLabel) roleLabel.textContent = currentUser?.role ? `当前身份：${currentUser.role}` : '';
    }
  } else {
    showPage('login-page');
  }

  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = { username: document.getElementById('login-username').value, password: document.getElementById('login-password').value };
    try {
      const data = await api('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) });
      authToken = data.access_token;
      localStorage.setItem('access_token', authToken);
      showPage('workbench-page');
      await refreshUserAndVisibility();
      await loadOptions();
      await loadCustomers();
      await populateCustomerSelects();
      loadKnowledgeCases();
      loadKnowledgeScripts();
      refreshDashboard();
      await loadChatSessions();
      showToast('登录成功，欢迎回来！', 'success');
    } catch (err) {
      showToast(err.message || '登录失败', 'error');
    }
  });

  document.getElementById('create-customer').addEventListener('click', createCustomer);
  document.getElementById('create-knowledge-case').addEventListener('click', createKnowledgeCase);
  document.getElementById('create-knowledge-script').addEventListener('click', createKnowledgeScript);

  document.getElementById('save-type').addEventListener('click', async () => {
    const customerId = document.getElementById('type-form').dataset.customerId;
    await updateCustomerType(customerId);
  });

  document.getElementById('quick-analyze-btn').addEventListener('click', quickAnalyze);
  document.getElementById('analyze-name').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !document.getElementById('quick-analyze-btn').disabled) quickAnalyze();
  });

  document.getElementById('agent-send')?.addEventListener('click', askAgent);
  document.getElementById('agent-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !document.getElementById('agent-send')?.disabled) askAgent(); });

  document.getElementById('chat-send')?.addEventListener('click', sendChatMessage);
  document.getElementById('chat-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !document.getElementById('chat-send')?.disabled) sendChatMessage(); });
  document.getElementById('chat-new-session')?.addEventListener('click', createChatSession);
  document.getElementById('chat-reload')?.addEventListener('click', async () => {
    if (currentSessionId) await loadChatMessages(currentSessionId);
  });
  document.getElementById('chat-customer')?.addEventListener('change', async () => {
    await loadChatSessions();
    currentSessionId = null;
    document.getElementById('chat-messages').innerHTML = '<p class="muted">已切换客户筛选，请选择或新建一个会话。</p>';
    document.getElementById('active-session-title').textContent = '当前会话：未选择';
  });

  // 委托：会话列表按钮
  document.getElementById('chat-session-list')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.open-session-btn');
    if (!btn) return;
    const li = btn.closest('li');
    if (!li) return;
    const sid = Number(li.dataset.sessionId);
    const cid = li.dataset.customerId ? Number(li.dataset.customerId) : null;
    const title = li.dataset.title || '';
    openChatSession(sid, cid, title);
  });

  document.getElementById('refresh-assist')?.addEventListener('click', async () => {
    const customerId = document.getElementById('assist-form').dataset.customerId;
    await renderAssist(customerId);
  });
  document.getElementById('refresh-followup')?.addEventListener('click', async () => {
    const customerId = document.getElementById('followup-form').dataset.customerId;
    await renderFollowup(customerId);
  });

  document.getElementById('briefing-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return showToast('请选择客户', 'error');
    setLoading('briefing-action', true);
    try {
      const result = await api(`/api/v1/customers/${customerId}/briefing`, { method: 'POST' });
      await renderMeetingResult(result.data);
    } catch (e) {
      showToast(e.message);
    } finally {
      setLoading('briefing-action', false);
    }
  });

  document.getElementById('assist-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return showToast('请选择客户', 'error');
    setLoading('assist-action', true);
    try {
      const payload = {
        current_stage: document.getElementById('meeting-stage').value,
        transcript: document.getElementById('meeting-transcript').value,
        customer_type: document.getElementById('meeting-type').value,
      };
      const result = await api(`/api/v1/customers/${customerId}/assist`, { method: 'POST', body: JSON.stringify(payload) });
      await renderMeetingResult(result.data);
    } catch (e) {
      showToast(e.message);
    } finally {
      setLoading('assist-action', false);
    }
  });

  document.getElementById('followup-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return showToast('请选择客户', 'error');
    setLoading('followup-action', true);
    try {
      const payload = {
        summary: document.getElementById('meeting-transcript').value,
        decisions: getTagValues('decisions') ? getTagValues('decisions').split(/；/) : [],
        pending_actions: getTagValues('actions') ? getTagValues('actions').split(/；/) : [],
        transcript: document.getElementById('followup-transcript').value,
        customer_type: document.getElementById('meeting-type')?.value || '',
      };
      const result = await api(`/api/v1/customers/${customerId}/followup`, { method: 'POST', body: JSON.stringify(payload) });
      await renderMeetingResult(result.data);
    } catch (e) {
      showToast(e.message);
    } finally {
      setLoading('followup-action', false);
    }
  });

  document.getElementById('meeting-customer')?.addEventListener('change', onMeetingCustomerChange);
});
