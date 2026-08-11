function sourceCardsHtml(cards = []) {
  if (!Array.isArray(cards) || !cards.length) return '';
  const items = cards.map(card => {
    const badge = card.scene ? `<span class="source-badge">${escapeHtml(card.scene)}</span>` : '';
    const detail = [card.detail, card.label].filter(Boolean).join(' · ');
    const extra = detail ? ` · ${escapeHtml(detail)}` : '';
    return `<li>
      <div class="source-row">
        <span class="source-source">${escapeHtml(card.source || '未知来源')}</span>
        ${badge}
      </div>
      <div class="source-detail">${escapeHtml(card.label || '来源')}${extra}</div>
    </li>`;
  }).join('');
  return `<div class="source-card"><div class="source-card-title">引用来源</div><ul class="source-list source-list--compact">${items}</ul></div>`;
}const baseApi = 'http://127.0.0.1:8002';
let authToken = localStorage.getItem('access_token');
let currentUser = null;
let currentSessionId = null;
let currentCustomerId = null;

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
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/\n/g, '<br/>');
}

function sourceCardsHtml(cards = []) {
  if (!cards.length) return '';
  const items = cards.map(card => {
    const detail = [card.detail, card.scene].filter(Boolean).join(' · ') || '来源';
    return `<li><strong>${escapeHtml(card.source)}</strong>：${escapeHtml(card.label)} / ${escapeHtml(detail)}</li>`;
  }).join('');
  return `<div class="source-card"><ul class="source-list">${items}</ul></div>`;
}

function showPage(page) {
  const target = document.getElementById(page);
  if (!target) return;
  const isTopLevel = target.parentElement && target.parentElement.id === 'app-shell';
  if (isTopLevel) {
    // 顶层页面切换：只清 #app-shell 直接子级
    document.querySelectorAll('#app-shell > .page').forEach((el) => el.classList.remove('active'));
  } else {
    // 嵌套页面切换：清所有非顶层 .page
    document.querySelectorAll('.page').forEach((el) => {
      if (!el.parentElement || el.parentElement.id !== 'app-shell') {
        el.classList.remove('active');
      }
    });
  }
  target.classList.add('active');
}

function appendChatBubble(role, text, extraHtml = '') {
  const div = document.createElement('div');
  div.className = `agent-msg ${role === 'user' ? 'agent-user' : 'agent-ai'}`;
  div.innerHTML = `${escapeHtml(text)}${extraHtml ? '<div class="source-card-embed">' + extraHtml + '</div>' : ''}`;
  const box = document.getElementById('chat-messages');
  box.appendChild(div);
  box.parentElement.scrollTop = box.parentElement.scrollHeight;
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
  document.querySelectorAll('[data-admin-only]').forEach(el => el.style.display = isAdmin ? '' : 'none');
}

async function refreshUserAndVisibility() {
  await fetchCurrentUser();
  applyRoleVisibility();
}

async function loadCustomers() {
  const data = await api('/api/v1/customers');
  const tbody = document.getElementById('customer-table-body');
  tbody.innerHTML = '';
  (data.data || []).forEach((item) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.id}</td>
      <td>${escapeHtml(item.name || '')}</td>
      <td>${escapeHtml(item.industry || '')}</td>
      <td>${escapeHtml(item.primary_type || '')}</td>
      <td>
        <span class="button-stack">
          <button onclick="viewCustomerDetail(${item.id})">详情</button>
          <button onclick="openBriefing(${item.id})">会前简报</button>
          <button onclick="openAssist(${item.id})">会中辅助</button>
          <button onclick="openFollowup(${item.id})">会后跟进</button>
          <button onclick="openTypeForm(${item.id})">更新类型</button>
        </span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

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
        <td>${escapeHtml(item.created_at || '-')}</td>
        <td>${escapeHtml(item.stage || '-')}</td>
        <td>${escapeHtml(item.summary || '-')}</td>
        <td>${escapeHtml(item.decisions || '-')}</td>
        <td>${escapeHtml(item.pending_actions || '-')}</td>
      </tr>
    `).join('');
    const briefingRows = (briefings.data || []).slice().reverse().map(item => {
      const sourceCards = sourceCardsHtml(item.llm_source_cards || []);
      return `
        <tr>
          <td>${escapeHtml(item.created_at || '-')}</td>
          <td>${escapeHtml(item.primary_type || '-')}</td>
          <td>${escapeHtml(item.focus || item.opening_line || '-')}</td>
          <td>${escapeHtml((item.recommended_cases || []).map(x => x.title).join('、') || '-')}</td>
          <td>${sourceCards}</td>
        </tr>
      `;
    }).join('');
    container.innerHTML = `
      <h3 style="margin:0 0 8px;font-size:18px;">客户详情：${escapeHtml(customer.name || id)}</h3>
      <p>行业：${escapeHtml(customer.industry || '-')}</p>
      <p>阶段：${escapeHtml(customer.stage || '-')}</p>
      <p>区域：${escapeHtml(customer.region || '-')}</p>
      <p>主类型：${escapeHtml(customer.primary_type || '-')}</p>
      <p>次类型：${escapeHtml(customer.secondary_type || '-')}</p>
      <p>类型依据：${escapeHtml(customer.type_evidence || '-')}</p>
      <h4 style="margin:16px 0 8px;font-size:16px;">会前简报历史</h4>
      <table>
        <thead>
          <tr><th>时间</th><th>类型</th><th>重点</th><th>推荐案例</th><th>来源卡</th></tr>
        </thead>
        <tbody>${briefingRows || '<tr><td colspan="5" class="muted">暂无会前简报</td></tr>'}</tbody>
      </table>
      <h4 style="margin:16px 0 8px;font-size:16px;">会前/会中/会后历史</h4>
      <table>
        <thead>
          <tr><th>时间</th><th>阶段</th><th>摘要</th><th>决策</th><th>待办</th></tr>
        </thead>
        <tbody>${rows || '<tr><td colspan="5" class="muted">暂无互动记录</td></tr>'}</tbody>
      </table>
    `;
  } catch (e) {
    container.innerHTML = `<p class="muted">加载客户详情失败：${e.message}</p>`;
  }
}

async function createCustomer() {
  const payload = {
    name: document.getElementById('cust-name').value,
    industry: document.getElementById('cust-industry').value,
    revenue_range: document.getElementById('cust-revenue').value,
    stage: document.getElementById('cust-stage').value,
    region: document.getElementById('cust-region').value,
  };
  if (!payload.name) return alert('请填写客户名称');
  await api('/api/v1/customers', { method: 'POST', body: JSON.stringify(payload) });
  document.getElementById('customer-form').reset();
  await loadCustomers();
}

async function updateCustomerType(customerId) {
  const payload = {
    primary_type: document.getElementById('type-primary').value,
    secondary_type: document.getElementById('type-secondary').value,
    type_confidence: parseFloat(document.getElementById('type-confidence').value || '0'),
    type_evidence: document.getElementById('type-evidence').value,
  };
  await api(`/api/v1/customers/${customerId}/type`, { method: 'PATCH', body: JSON.stringify(payload) });
  await loadCustomers();
  closeModal('type-modal');
}

async function renderBriefing(customerId) {
  const sessionId = currentSessionId ? `&session_id=${encodeURIComponent(currentSessionId)}` : '';
  const data = await api(`/api/v1/customers/${customerId}/briefing?${sessionId}` , { method: 'POST' });
  const payload = data.data || {};
  const sourceCards = sourceCardsHtml(payload.llm_source_cards || []);
  const container = document.getElementById('briefing-result');
  container.innerHTML = `
    <div class="result-block">
      <h3>会前简报：${escapeHtml(payload.customer_name || customerId)}</h3>
      <p><strong>类型：</strong>${escapeHtml(payload.primary_type || '待判断')}${payload.secondary_type ? ' / ' + escapeHtml(payload.secondary_type) : ''}</p>
      <p><strong>置信度：</strong>${escapeHtml(String(payload.confidence ?? '-'))}</p>
      <p><strong>判断依据：</strong>${escapeHtml(payload.evidence || '-')}</p>
      <p><strong>破冰话术：</strong>${escapeHtml(payload.opening_line || '-')}</p>
      <p><strong>重点方向：</strong>${escapeHtml(payload.focus || '-')}</p>
      <p><strong>下一步：</strong>${escapeHtml(payload.next_step || '-')}</p>
      <p><strong>潜在异议：</strong>${escapeHtml((payload.potential_objections || []).join('；') || '-')}</p>
      <p><strong>推荐案例：</strong>${escapeHtml((payload.recommended_cases || []).map(x => x.title).join('、') || '-')}</p>
      ${sourceCards}
      <p><strong>LLM：</strong>${escapeHtml(payload.llm_text || '未生成')}</p>
      <p><strong>trace_id：</strong>${escapeHtml(data.trace_id || '-')}</p>
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
    customer_type: document.getElementById('assist-type').value,
  };
  const data = await api(`/api/v1/customers/${customerId}/assist`, { method: 'POST', body: JSON.stringify(payload) });
  const out = data.data || {};
  const sourceCards = sourceCardsHtml(out.source_cards || out.source_refs || []);
  const container = document.getElementById('assist-result');
  container.innerHTML = `
    <div class="result-block">
      <h3>会中辅助</h3>
      <p><strong>当前阶段：</strong>${escapeHtml(out.current_stage || '-')}</p>
      <p><strong>检测阶段：</strong>${escapeHtml(out.detected_stage || '-')}</p>
      <p><strong>阶段提示：</strong>${escapeHtml(out.stage_guidance || '-')}</p>
      <p><strong>建议话术：</strong>${escapeHtml(out.suggested_response || '-')}</p>
      <p><strong>异议：</strong>${escapeHtml(out.objection_detected || '未识别')}</p>
      <p><strong>异议应答：</strong>${escapeHtml(out.objection_response || '-')}</p>
      <p><strong>备注：</strong>${escapeHtml((out.notes || []).join(' / ') || '-')}</p>
      ${sourceCards}
      <p><strong>LLM：</strong>${escapeHtml(out.llm_text || '未生成')}</p>
      <p><strong>trace_id：</strong>${escapeHtml(data.trace_id || '-')}</p>
    </div>
  `;
  container.style.display = 'block';
}

async function renderFollowup(customerId) {
  const payload = {
    summary: document.getElementById('followup-summary').value,
    decisions: (document.getElementById('followup-decisions').value || '').split(/；/).filter(Boolean),
    pending_actions: (document.getElementById('followup-actions').value || '').split(/；/).filter(Boolean),
    transcript: document.getElementById('followup-transcript').value,
    customer_type: document.getElementById('followup-type').value,
  };
  const data = await api(`/api/v1/customers/${customerId}/followup`, { method: 'POST', body: JSON.stringify(payload) });
  const out = data.data || {};
  const sourceCards = sourceCardsHtml(out.source_cards || out.source_refs || []);
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
      <p><strong>LLM：</strong>${escapeHtml(out.llm_text || '未生成')}</p>
      <p><strong>trace_id：</strong>${escapeHtml(data.trace_id || '-')}</p>
    </div>
  `;
  container.style.display = 'block';
}

async function loadKnowledgeCases() {
  const data = await api('/api/v1/knowledge/cases');
  const tbody = document.getElementById('knowledge-case-table-body');
  tbody.innerHTML = '';
  (data.data || []).forEach((item) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escapeHtml(item.code||'')}</td><td>${escapeHtml(item.title||'')}</td><td>${escapeHtml(item.type||'')}</td><td>${escapeHtml(item.industry||'')}</td><td>${escapeHtml(item.result||'')}</td><td>${escapeHtml(item.source||'')}</td>`;
    tbody.appendChild(tr);
  });
}

async function createKnowledgeCase() {
  const payload = {
    code: document.getElementById('case-code').value,
    title: document.getElementById('case-title').value,
    type: document.getElementById('case-type').value,
    industry: document.getElementById('case-industry').value,
    stage: document.getElementById('case-stage').value,
    result: document.getElementById('case-result').value,
    source: document.getElementById('case-source').value,
  };
  if (!payload.code || !payload.title) return alert('请填写案例编码和标题');
  await api('/api/v1/knowledge/cases', { method: 'POST', body: JSON.stringify(payload) });
  document.getElementById('knowledge-case-form').reset();
  loadKnowledgeCases();
}

async function loadKnowledgeScripts() {
  const data = await api('/api/v1/knowledge/scripts');
  const tbody = document.getElementById('knowledge-script-table-body');
  tbody.innerHTML = '';
  (data.data || []).forEach((item) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${escapeHtml(item.scene||'')}</td><td>${escapeHtml(item.type||'')}</td><td>${escapeHtml(item.template||'')}</td><td>${escapeHtml(item.source||'')}</td>`;
    tbody.appendChild(tr);
  });
}

async function createKnowledgeScript() {
  const payload = {
    scene: document.getElementById('script-scene').value,
    type: document.getElementById('script-type').value,
    template: document.getElementById('script-template').value,
    source: document.getElementById('script-source').value,
  };
  if (!payload.type || !payload.template) return alert('请填写客户类型和话术');
  await api('/api/v1/knowledge/scripts', { method: 'POST', body: JSON.stringify(payload) });
  document.getElementById('knowledge-script-form').reset();
  loadKnowledgeScripts();
}

async function quickAnalyze() {
  const nameInput = document.getElementById('analyze-name');
  const name = (nameInput.value || '').trim();
  if (!name) return alert('请输入客户名称');
  const industry = document.getElementById('analyze-industry').value;
  const stage = document.getElementById('analyze-stage').value;
  const container = document.getElementById('analyze-result');
  container.style.display = 'block';
  container.innerHTML = '<p class="muted">正在分析中...</p>';
  try {
    const payload = { name, industry, stage };
    const data = await api('/api/v1/analyze', { method: 'POST', body: JSON.stringify(payload) });
    const out = data.data || {};
    const b = out.briefing || {};
    const sourceCards = sourceCardsHtml(b.llm_source_cards || []);
    container.innerHTML = `
      <div class="result-block">
        ${out.is_new ? '<p style="color:#16a34a;font-weight:600;">新客户已创建</p>' : '<p class="muted">已找到已有客户</p>'}
        <h3>${escapeHtml(out.customer_name || name)}</h3>
        <p><strong>类型：</strong>${escapeHtml(out.primary_type || '待判断')}${out.secondary_type ? ' / ' + escapeHtml(out.secondary_type) : ''}</p>
        <p><strong>置信度：</strong>${escapeHtml(String(out.type_confidence ?? '-'))}</p>
        <p><strong>判断依据：</strong>${escapeHtml(out.type_evidence || '-')}</p>
        <p><strong>破冰话术：</strong>${escapeHtml(b.opening_line || '-')}</p>
        <p><strong>重点方向：</strong>${escapeHtml(b.focus || '-')}</p>
        <p><strong>下一步：</strong>${escapeHtml(b.next_step || '-')}</p>
        <p><strong>潜在异议：</strong>${escapeHtml((b.potential_objections || []).join('；') || '-')}</p>
        ${sourceCards}
        <p><strong>LLM：</strong>${escapeHtml(b.llm_text || '未生成')}</p>
      </div>
    `;
    await loadCustomers();
  } catch (e) {
    container.innerHTML = `<p style="color:#dc2626;">分析失败：${e.message}</p>`;
  }
}

async function refreshDashboard() {
  try {
    const [customers, cases, scripts] = await Promise.all([
      api('/api/v1/customers'),
      api('/api/v1/knowledge/cases'),
      api('/api/v1/knowledge/scripts'),
    ]);
    document.getElementById('kpi-customers').textContent = (customers.data || []).length;
    document.getElementById('kpi-interactions').textContent = '0';
    document.getElementById('kpi-briefing').textContent = (customers.data || []).length;
    document.getElementById('kpi-followup').textContent = '0';
    const feed = document.getElementById('activity-feed');
    if (feed) {
      feed.innerHTML = `
        <p>客户库：${(customers.data || []).length} 个</p>
        <p>案例库：${(cases.data || []).length} 条</p>
        <p>话术库：${(scripts.data || []).length} 条</p>
      `;
    }
  } catch (e) {
    console.error(e);
  }
}

async function askAgent() {
  const input = document.getElementById('agent-input');
  const text = (input.value || '').trim();
  if (!text) return;
  appendChatBubble('user', text);
  input.value = '';
  let reply = '';
  if (text.includes('会前') || text.includes('简报')) {
    reply = '请先到“客户画像”创建客户，再进入“会前/会中/会后”输入客户ID生成会前简报。';
  } else if (text.includes('案例') || text.includes('话术')) {
    reply = '你可以在“知识库后台”新增或查看案例与话术，后续助手会直接调用。';
  } else if (text.includes('客户')) {
    reply = '建议先明确客户名称、行业、发展阶段，我会协助判断客户类型。';
  } else {
    reply = '收到。你可以继续追问客户类型、会中应对话术或会后跟进动作。';
  }
  appendChatBubble('ai', reply);
}

function openBriefing(customerId) {
  document.getElementById('briefing-modal').style.display = 'flex';
  renderBriefing(customerId);
}
function openAssist(customerId) {
  document.getElementById('assist-modal').style.display = 'flex';
  document.getElementById('assist-form').dataset.customerId = customerId;
}
function openFollowup(customerId) {
  document.getElementById('followup-modal').style.display = 'flex';
  document.getElementById('followup-form').dataset.customerId = customerId;
}
function openTypeForm(customerId) {
  document.getElementById('type-modal').style.display = 'flex';
  document.getElementById('type-form').dataset.customerId = customerId;
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
  showPage('login-page');
}

function viewCustomerDetail(customerId) {
  currentCustomerId = customerId;
  showPage('customer-detail-page');
  loadCustomerDetail();
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
  const customerId = Number(document.getElementById('chat-customer')?.value || 0) || null;
  const data = await api(`/api/v1/chat/sessions${customerId ? `?customer_id=${customerId}` : ''}`);
  const list = document.getElementById('chat-session-list');
  if (!list) return;
  list.innerHTML = (data.data || []).map(item => {
    const title = escapeHtml(item.title || `会话 #${item.id}`);
    return `<li>
      <button onclick="openChatSession(${item.id}, ${item.customer_id || 'null'}, '${escapeHtml(item.title || '')}')">${title}</button>
      <span class="button-stack">
        <button class="secondary" onclick="renameChatSession(${item.id})">重命名</button>
        <button class="secondary" onclick="deleteChatSession(${item.id})">删除</button>
      </span>
    </li>`;
  }).join('');
  if (document.getElementById('chat-empty-hint')) {
    document.getElementById('chat-empty-hint').style.display = (data && data.length) ? 'none' : 'block';
  }
}

async function renameChatSession(sessionId) {
  const current = document.querySelector(`button[onclick="openChatSession(${sessionId}"]`)?.textContent?.replace('重命名','').replace('删除','').trim() || '';
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
  } catch (e) {
    alert(e.message);
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
  const data = await api(`/api/v1/chat/sessions/${sessionId}/messages`);
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  (data.data || []).forEach((item) => {
    let extraHtml = '';
    if (item.role === 'assistant') {
      try {
        const meta = JSON.parse(item.meta || '{}');
        const refs = Array.isArray(meta.source_refs) ? meta.source_refs : [];
        const cards = Array.isArray(meta.source_cards) ? meta.source_cards : [];
        if (refs.length || cards.length) extraHtml = sourceCardsHtml(cards);
      } catch (e) {
        console.error(e);
      }
    }
    appendChatBubble(item.role, item.content, extraHtml);
  });
  if (!container.children.length) {
    container.innerHTML = '<p class="muted">暂无消息，请直接输入销售问题。</p>';
  }
  container.parentElement.scrollTop = container.parentElement.scrollHeight;
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
  const data = await api(`/api/v1/chat/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({role:'user', content:text}) });
  const reply = data.message || {};
  const cards = sourceCardsHtml(data.source_cards || []);
  appendChatBubble('assistant', reply.content || '未收到回复', cards);
  await loadChatSessions();
  await loadCustomerDetail();
}

async function renderMeetingResult(result) {
  const container = document.getElementById('meeting-result');
  container.innerHTML = '';
  if (!result) {
    container.innerHTML = '<p class="muted">暂无结果</p>';
    return;
  }
  const block = document.createElement('div');
  block.className = 'result-block';
  const entries = Object.entries(result).filter(([, value]) => value !== null && value !== undefined && value !== '');
  for (const [key, value] of entries) {
    const title = document.createElement('strong');
    title.textContent = key;
    const body = document.createElement('div');
    body.style.whiteSpace = 'pre-wrap';
    body.style.background = '#f8fafc';
    body.style.padding = '10px';
    body.style.borderRadius = '10px';
    body.style.marginBottom = '10px';
    if (Array.isArray(value)) {
      body.innerHTML = value.map(item => {
        if (typeof item === 'string') return escapeHtml(item);
        if (item && typeof item === 'object') return escapeHtml(JSON.stringify(item, null, 2));
        return escapeHtml(String(item));
      }).join('<br/>');
    } else if (key === 'llm_source_cards') {
      body.innerHTML = sourceCardsHtml(Array.isArray(value) ? value : []);
    } else {
      body.textContent = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
    }
    const row = document.createElement('div');
    row.style.marginBottom = '10px';
    row.appendChild(title);
    row.appendChild(body);
    block.appendChild(row);
  }
  container.appendChild(block);
}

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
      await loadCustomers();
      loadKnowledgeCases();
      loadKnowledgeScripts();
      refreshDashboard();
      await loadChatSessions();
      const detail = document.getElementById('customer-detail');
      if (detail) detail.innerHTML = '<p class="muted">请在客户画像选择一条客户查看详情。</p>';
      const customerSelect = document.getElementById('chat-customer');
      if (customerSelect) {
        const list = await api('/api/v1/customers');
        customerSelect.innerHTML = '<option value="">选择客户</option>' + (list.data || []).map(item => `<option value="${item.id}">${item.id} - ${escapeHtml(item.name || '未命名')}</option>`).join('');
      }
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
      await loadCustomers();
      loadKnowledgeCases();
      loadKnowledgeScripts();
      refreshDashboard();
      await loadChatSessions();
    } catch (err) {
      alert(err.message || '登录失败');
    }
  });

  document.getElementById('create-customer').addEventListener('click', createCustomer);
  document.getElementById('create-knowledge-case').addEventListener('click', createKnowledgeCase);
  document.getElementById('create-knowledge-script').addEventListener('click', createKnowledgeScript);

  document.getElementById('save-type').addEventListener('click', async () => {
    const customerId = document.getElementById('type-form').dataset.customerId;
    await updateCustomerType(customerId);
  });

  document.getElementById('refresh-assist').addEventListener('click', async () => {
    const customerId = document.getElementById('assist-form').dataset.customerId;
    await renderAssist(customerId);
  });
  document.getElementById('refresh-followup').addEventListener('click', async () => {
    const customerId = document.getElementById('followup-form').dataset.customerId;
    await renderFollowup(customerId);
  });

  document.getElementById('agent-send')?.addEventListener('click', askAgent);
  document.getElementById('agent-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') askAgent();
  });
  document.getElementById('quick-analyze-btn')?.addEventListener('click', quickAnalyze);
  document.getElementById('analyze-name')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') quickAnalyze();
  });

  document.getElementById('chat-send')?.addEventListener('click', sendChatMessage);
  document.getElementById('chat-input')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendChatMessage(); });
  document.getElementById('chat-new-session')?.addEventListener('click', createChatSession);
  document.getElementById('chat-reload')?.addEventListener('click', async () => {
    if (currentSessionId) await loadChatMessages(currentSessionId);
  });
  document.getElementById('chat-customer')?.addEventListener('change', async () => {
    await loadChatSessions();
    currentSessionId = null;
    document.getElementById('chat-messages').innerHTML = '<p class="muted">已切换客户筛选，请选择或新建一个会话。</p>';
    const label = document.getElementById('active-session-title');
    if (label) label.textContent = '当前会话：未选择';
  });

  document.getElementById('briefing-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return alert('请填写客户 ID');
    const result = await api(`/api/v1/customers/${customerId}/briefing`, { method: 'POST' });
    await renderMeetingResult(result.data);
  });

  document.getElementById('assist-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return alert('请填写客户 ID');
    const payload = {
      current_stage: document.getElementById('meeting-stage').value,
      transcript: document.getElementById('meeting-transcript').value,
      customer_type: '',
    };
    const result = await api(`/api/v1/customers/${customerId}/assist`, { method: 'POST', body: JSON.stringify(payload) });
    await renderMeetingResult(result.data);
  });

  document.getElementById('followup-action')?.addEventListener('click', async () => {
    const customerId = Number(document.getElementById('meeting-customer').value);
    if (!customerId) return alert('请填写客户 ID');
    const payload = {
      summary: document.getElementById('meeting-transcript').value,
      decisions: (document.getElementById('meeting-decisions').value || '').split(/；/).filter(Boolean),
      pending_actions: (document.getElementById('meeting-actions').value || '').split(/；/).filter(Boolean),
      transcript: document.getElementById('followup-transcript').value,
      customer_type: '',
    };
    const result = await api(`/api/v1/customers/${customerId}/followup`, { method: 'POST', body: JSON.stringify(payload) });
    await renderMeetingResult(result.data);
  });

  document.getElementById('load-customer-detail')?.addEventListener('click', loadCustomerDetail);
});
