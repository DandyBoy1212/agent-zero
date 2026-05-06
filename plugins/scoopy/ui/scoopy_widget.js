(function() {
  'use strict';

  const API = '/api/plugins/scoopy';
  let autoApprove = true;
  let isExpanded = false;
  let cards = [];
  let pollTimer = null;

  // --- Styles ---
  const css = `
    #scoopy-widget {
      position: fixed; bottom: 16px; right: 16px; z-index: 99999;
      width: 360px; max-width: calc(100vw - 32px);
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      font-size: 14px; color: #1a1a1a;
      background: #fff; border: 1px solid #d4d4d4; border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      overflow: hidden; transition: all 0.2s ease;
    }
    #scoopy-widget.collapsed { width: auto; }
    #scoopy-widget-header {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px; background: #2d7a2d; color: #fff;
      cursor: pointer; user-select: none;
    }
    #scoopy-widget-title { flex: 1; font-weight: 600; }
    #scoopy-widget-badge {
      background: #fff; color: #2d7a2d; padding: 1px 8px;
      border-radius: 999px; font-size: 12px; font-weight: 700;
    }
    #scoopy-widget-toggle-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 14px; border-bottom: 1px solid #eee; background: #fafafa;
    }
    #scoopy-widget-toggle-label { font-size: 13px; color: #555; }
    .scoopy-toggle {
      width: 36px; height: 20px; background: #ccc; border-radius: 10px;
      position: relative; cursor: pointer; transition: background 0.2s;
    }
    .scoopy-toggle.on { background: #2d7a2d; }
    .scoopy-toggle::after {
      content: ''; position: absolute; left: 2px; top: 2px;
      width: 16px; height: 16px; background: #fff; border-radius: 50%;
      transition: left 0.2s;
    }
    .scoopy-toggle.on::after { left: 18px; }
    #scoopy-widget-cards { max-height: 50vh; overflow-y: auto; padding: 4px 0; }
    .scoopy-card { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
    .scoopy-card:last-child { border-bottom: none; }
    .scoopy-card-meta { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
    .scoopy-card-meta .badge {
      display: inline-block; padding: 1px 6px; border-radius: 4px;
      font-weight: 600; margin-right: 6px;
    }
    .scoopy-card-meta .badge.in_scope { background: #d6f4d4; color: #1a4d1a; }
    .scoopy-card-meta .badge.drift { background: #fff3cd; color: #856404; }
    .scoopy-card-meta .badge.escalation { background: #f8d7da; color: #721c24; }
    .scoopy-card-meta .badge.create_task { background: #d1ecf1; color: #0c5460; }
    .scoopy-card-meta .badge.memory_candidate { background: #e6e0f4; color: #4a3c8a; }
    .scoopy-card-reasoning { font-size: 12px; color: #666; font-style: italic; margin-bottom: 6px; }
    .scoopy-card-draft { background: #f4f4f4; padding: 6px 8px; border-radius: 4px; white-space: pre-wrap; font-size: 13px; margin-bottom: 6px; }
    .scoopy-card-actions { display: flex; gap: 6px; }
    .scoopy-btn {
      padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;
      cursor: pointer; border: 1px solid; flex: 1;
    }
    .scoopy-btn-approve { background: #2d7a2d; color: #fff; border-color: #2d7a2d; }
    .scoopy-btn-reject { background: #fff; color: #888; border-color: #ccc; }
    .scoopy-empty { padding: 20px; text-align: center; color: #999; font-size: 13px; }
  `;

  // --- DOM ---
  function init() {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    const widget = document.createElement('div');
    widget.id = 'scoopy-widget';
    widget.className = 'collapsed';
    widget.innerHTML = `
      <div id="scoopy-widget-header">
        <span id="scoopy-widget-title">Scoopy</span>
        <span id="scoopy-widget-badge">0</span>
      </div>
      <div id="scoopy-widget-body" style="display:none;">
        <div id="scoopy-widget-toggle-row">
          <span id="scoopy-widget-toggle-label">Auto-approve</span>
          <div class="scoopy-toggle" id="scoopy-widget-toggle"></div>
        </div>
        <div id="scoopy-widget-cards"></div>
      </div>
    `;
    document.body.appendChild(widget);

    document.getElementById('scoopy-widget-header').addEventListener('click', toggleExpand);
    document.getElementById('scoopy-widget-toggle').addEventListener('click', toggleAutoApprove);

    loadInitialState();
  }

  function toggleExpand() {
    isExpanded = !isExpanded;
    const widget = document.getElementById('scoopy-widget');
    const body = document.getElementById('scoopy-widget-body');
    if (isExpanded) {
      widget.classList.remove('collapsed');
      body.style.display = '';
      poll();
    } else {
      widget.classList.add('collapsed');
      body.style.display = 'none';
    }
  }

  async function loadInitialState() {
    try {
      const r = await fetch(API + '/scoopy_settings_get');
      const j = await r.json();
      autoApprove = !!j.auto_approve;
      renderToggle();
    } catch (e) { /* no-op */ }
    poll();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(poll, 5000);
  }

  async function toggleAutoApprove(e) {
    if (e) e.stopPropagation();
    const newVal = !autoApprove;
    try {
      const r = await fetch(API + '/scoopy_settings_set', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({auto_approve: newVal}),
      });
      const j = await r.json();
      if (j.status === 'ok') {
        autoApprove = newVal;
        renderToggle();
      }
    } catch (err) { console.error('toggle failed', err); }
  }

  function renderToggle() {
    const t = document.getElementById('scoopy-widget-toggle');
    if (!t) return;
    if (autoApprove) t.classList.add('on'); else t.classList.remove('on');
  }

  async function poll() {
    try {
      const r = await fetch(API + '/scoopy_inbox_json');
      const j = await r.json();
      cards = j.cards || [];
      renderBadge();
      if (isExpanded) renderCards();
    } catch (e) { /* no-op */ }
  }

  function renderBadge() {
    const b = document.getElementById('scoopy-widget-badge');
    if (!b) return;
    b.textContent = cards.length;
    b.style.display = cards.length > 0 ? '' : 'none';
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderCards() {
    const container = document.getElementById('scoopy-widget-cards');
    if (!container) return;
    if (cards.length === 0) {
      container.innerHTML = '<div class="scoopy-empty">No pending approvals.</div>';
      return;
    }
    container.innerHTML = cards.map(c => `
      <div class="scoopy-card" data-token="${escapeHtml(c.token)}">
        <div class="scoopy-card-meta">
          <span class="badge ${escapeHtml(c.action_type)}">${escapeHtml(c.action_type)}</span>
          ${escapeHtml(c.contact_id || '')}
        </div>
        <div class="scoopy-card-reasoning">${escapeHtml(c.reasoning || '')}</div>
        <div class="scoopy-card-draft">${escapeHtml(c.draft || '')}</div>
        <div class="scoopy-card-actions">
          <button class="scoopy-btn scoopy-btn-approve" data-action="approve">Approve</button>
          <button class="scoopy-btn scoopy-btn-reject" data-action="reject">Reject</button>
        </div>
      </div>
    `).join('');
    container.querySelectorAll('.scoopy-btn').forEach(btn => {
      btn.addEventListener('click', handleAction);
    });
  }

  async function handleAction(e) {
    const card = e.target.closest('.scoopy-card');
    const token = card.dataset.token;
    const action = e.target.dataset.action;
    e.target.disabled = true;
    e.target.textContent = '...';
    try {
      await fetch(API + '/scoopy_' + action, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token: token}),
      });
      await poll();
    } catch (err) { console.error(action, 'failed', err); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
