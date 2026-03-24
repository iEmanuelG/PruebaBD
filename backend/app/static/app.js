/* ══════════════════════════════════════════════
   Holcim MDM — SPA JavaScript
   ══════════════════════════════════════════════ */

const API = '';  // Misma URL base que el servidor FastAPI

// ─── State ──────────────────────────────────────
let currentUser = null;
let currentPage = 'dashboard';
let suppliersPage = 0;
let auditPage = 0;
let editingSupplierId = null;
let deletingSupplierId = null;
const PAGE_SIZE = 15;
const AUDIT_SIZE = 20;

// ─── Utils ───────────────────────────────────────
const $ = id => document.getElementById(id);
const token = () => localStorage.getItem('mdm_token');

function showToast(msg, type = 'info', duration = 3000) {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), duration);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false
  });
}

function formatDateShort(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-CO', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  });
}

function showAlert(id, msg) {
  const el = $(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}
function hideAlert(id) { $(id)?.classList.add('hidden'); }

// ─── API Helpers ─────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token()) headers['Authorization'] = `Bearer ${token()}`;

  const res = await fetch(API + path, { ...options, headers });

  if (res.status === 401) {
    logout();
    return null;
  }

  const data = res.headers.get('Content-Type')?.includes('application/json')
    ? await res.json()
    : await res.text();

  if (!res.ok) {
    const msg = data?.detail || (typeof data === 'string' ? data : 'Error en el servidor');
    throw new Error(msg);
  }
  return data;
}

// ─── Auth ─────────────────────────────────────────
$('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  hideAlert('login-error');
  const btn = $('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px"></div>';

  try {
    const data = await apiFetch('/api/auth/login-json', {
      method: 'POST',
      body: JSON.stringify({
        username: $('login-username').value.trim(),
        password: $('login-password').value,
      })
    });
    if (!data) return;

    localStorage.setItem('mdm_token', data.access_token);
    await loadUserAndStart();
  } catch (err) {
    showAlert('login-error', err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Ingresar</span><i class="fa-solid fa-arrow-right-to-bracket"></i>';
  }
});

async function loadUserAndStart() {
  try {
    currentUser = await apiFetch('/api/auth/me');
    if (!currentUser) return;

    // Update sidebar
    $('sidebar-username').textContent = currentUser.full_name;
    $('user-avatar-letter').textContent = currentUser.full_name[0].toUpperCase();
    const roleEl = $('sidebar-role');
    roleEl.textContent = currentUser.role;
    roleEl.className = `role-badge ${currentUser.role}`;

    // Show/hide role-based elements
    document.querySelectorAll('.admin-only').forEach(el => {
      el.classList.toggle('hidden', currentUser.role !== 'admin');
    });
    document.querySelectorAll('.editor-only').forEach(el => {
      el.classList.toggle('hidden', !['admin', 'editor'].includes(currentUser.role));
    });

    $('login-screen').classList.add('hidden');
    $('app').classList.remove('hidden');
    navigateTo('dashboard');
  } catch (err) {
    logout();
  }
}

function logout() {
  localStorage.removeItem('mdm_token');
  currentUser = null;
  $('app').classList.add('hidden');
  $('login-screen').classList.remove('hidden');
  $('login-password').value = '';
}

$('logout-btn').addEventListener('click', logout);

// ─── Navigation ───────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(item.dataset.page);
  });
});

function navigateTo(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = $(`page-${page}`);
  if (pageEl) pageEl.classList.remove('hidden');

  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  switch (page) {
    case 'dashboard':  loadDashboard(); break;
    case 'suppliers':  loadSuppliers(0); break;
    case 'audit':      loadAuditLog(0); break;
    case 'users':      if (currentUser?.role === 'admin') loadUsers(); break;
  }
}

// ─── Dashboard ────────────────────────────────────
async function loadDashboard() {
  try {
    const [suppData, auditData] = await Promise.all([
      apiFetch('/api/suppliers?limit=100'),
      apiFetch('/api/audit-logs?limit=5')
    ]);
    if (!suppData || !auditData) return;

    const suppliers = suppData.items;
    const total = suppData.total;
    const active   = suppliers.filter(s => s.status === 'Activo').length;
    const pending  = suppliers.filter(s => s.status === 'Pendiente').length;
    const inactive = suppliers.filter(s => s.status === 'Inactivo').length;

    $('stat-total').textContent   = total;
    $('stat-active').textContent  = active;
    $('stat-pending').textContent = pending;
    $('stat-inactive').textContent= inactive;
    $('suppliers-count').textContent = total;

    // Mini audit log
    const auditEl = $('audit-preview');
    if (auditData.items.length === 0) {
      auditEl.innerHTML = '<div class="audit-item-mini"><span class="text-muted">Sin actividades recientes</span></div>';
    } else {
      auditEl.innerHTML = auditData.items.map(log => {
        const colors = { CREATE: '#22D3A5', UPDATE: '#3B82F6', DELETE: '#EF4444' };
        return `
          <div class="audit-item-mini">
            <div class="audit-dot" style="background:${colors[log.action]||'#8B949E'}"></div>
            <div class="audit-text">${log.description || log.action + ' en ' + log.entity}</div>
            <div class="audit-time">${formatDateShort(log.timestamp)}</div>
          </div>`;
      }).join('');
    }

    // Category breakdown
    const catCount = {};
    suppliers.forEach(s => {
      catCount[s.category] = (catCount[s.category] || 0) + 1;
    });
    const catEl = $('category-breakdown');
    const catColors = { Bienes: '#A78BFA', Servicios: '#60A5FA', Logística: '#F59E0B', Mixto: '#9CA3AF' };
    catEl.innerHTML = Object.entries(catCount).map(([cat, cnt]) => {
      const pct = total > 0 ? Math.round((cnt / total) * 100) : 0;
      return `
        <div class="category-row">
          <span class="category-label">${cat}</span>
          <div class="category-bar-wrap">
            <div class="category-bar" style="width:${pct}%; background:${catColors[cat]||'#6C63FF'}"></div>
          </div>
          <span class="category-count">${cnt}</span>
        </div>`;
    }).join('') || '<p class="text-muted" style="text-align:center">Sin datos</p>';

  } catch (err) {
    console.error('Error cargando dashboard:', err);
  }
}

// ─── Suppliers ────────────────────────────────────
let suppliersSearchTimer = null;

function getFilters() {
  return {
    search: $('search-input').value.trim(),
    status: $('filter-status').value,
    category: $('filter-category').value,
  };
}

$('search-input').addEventListener('input', () => {
  clearTimeout(suppliersSearchTimer);
  suppliersSearchTimer = setTimeout(() => loadSuppliers(0), 350);
});
$('filter-status').addEventListener('change', () => loadSuppliers(0));
$('filter-category').addEventListener('change', () => loadSuppliers(0));
$('btn-clear-filters').addEventListener('click', () => {
  $('search-input').value = '';
  $('filter-status').value = '';
  $('filter-category').value = '';
  loadSuppliers(0);
});

async function loadSuppliers(page = 0) {
  suppliersPage = page;
  $('suppliers-loading').classList.remove('hidden');
  $('suppliers-empty').classList.add('hidden');
  $('suppliers-table-wrap').classList.add('hidden');

  try {
    const f = getFilters();
    const params = new URLSearchParams({
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
      ...(f.search && { search: f.search }),
      ...(f.status && { status: f.status }),
      ...(f.category && { category: f.category }),
    });

    const data = await apiFetch(`/api/suppliers?${params}`);
    if (!data) return;

    $('suppliers-count').textContent = data.total;
    $('suppliers-loading').classList.add('hidden');

    if (data.items.length === 0) {
      $('suppliers-empty').classList.remove('hidden');
      return;
    }

    $('suppliers-table-wrap').classList.remove('hidden');
    $('suppliers-tbody').innerHTML = data.items.map(s => {
      const statusBadge = {
        'Activo':    '<span class="badge badge-active">Activo</span>',
        'Pendiente': '<span class="badge badge-pending">Pendiente</span>',
        'Inactivo':  '<span class="badge badge-inactive">Inactivo</span>',
      }[s.status] || s.status;

      const catBadge = {
        'Bienes':    '<span class="badge badge-goods">Bienes</span>',
        'Servicios': '<span class="badge badge-services">Servicios</span>',
        'Logística': '<span class="badge badge-logistics">Logística</span>',
        'Mixto':     '<span class="badge badge-mixed">Mixto</span>',
      }[s.category] || s.category;

      const canEdit   = ['admin','editor'].includes(currentUser?.role);
      const canDelete = currentUser?.role === 'admin';

      return `
        <tr>
          <td><strong>${escHtml(s.business_name)}</strong></td>
          <td><code>${escHtml(s.nit)}</code></td>
          <td>${escHtml(s.country)}${s.city ? ' / ' + escHtml(s.city) : ''}</td>
          <td>${catBadge}</td>
          <td>${statusBadge}</td>
          <td>
            ${s.contact_name ? `<div style="font-size:.8rem">${escHtml(s.contact_name)}</div>` : ''}
            ${s.contact_email ? `<div style="font-size:.75rem;color:var(--text-muted)">${escHtml(s.contact_email)}</div>` : ''}
          </td>
          <td>
            <div class="action-btns">
              ${canEdit ? `<button class="btn-icon" title="Editar" onclick="openEditModal(${s.id})"><i class="fa-solid fa-pen-to-square"></i></button>` : ''}
              ${canDelete ? `<button class="btn-icon" title="Eliminar" style="color:var(--danger)" onclick="confirmDelete(${s.id},'${escHtml(s.business_name).replace(/'/g,'\\\'')}')" ><i class="fa-solid fa-trash"></i></button>` : ''}
              ${!canEdit ? '<span style="color:var(--text-muted);font-size:.75rem">Solo lectura</span>' : ''}
            </div>
          </td>
        </tr>`;
    }).join('');

    renderPagination('suppliers-pagination', data.total, page, PAGE_SIZE, loadSuppliers);
  } catch (err) {
    $('suppliers-loading').classList.add('hidden');
    showToast('Error al cargar proveedores: ' + err.message, 'error');
  }
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Pagination ───────────────────────────────────
function renderPagination(containerId, total, page, size, loadFn) {
  const totalPages = Math.ceil(total / size);
  const el = $(containerId);
  if (totalPages <= 1) { el.innerHTML = ''; return; }

  let html = `<span class="page-info">${total} registros</span>`;
  html += `<button ${page === 0 ? 'disabled' : ''} onclick="${loadFn.name}(${page-1})">‹ Anterior</button>`;

  for (let i = 0; i < totalPages; i++) {
    if (totalPages > 7 && Math.abs(i - page) > 2 && i !== 0 && i !== totalPages-1) {
      if (i === 1 || i === totalPages-2) html += '<span style="color:var(--text-muted);padding:0 4px">…</span>';
      continue;
    }
    html += `<button class="${i===page?'active':''}" onclick="${loadFn.name}(${i})">${i+1}</button>`;
  }

  html += `<button ${page >= totalPages-1 ? 'disabled' : ''} onclick="${loadFn.name}(${page+1})">Siguiente ›</button>`;
  el.innerHTML = html;
}

// ─── Supplier Modal ───────────────────────────────
$('btn-new-supplier').addEventListener('click', () => openModal());
$('modal-close').addEventListener('click', closeModal);
$('modal-cancel').addEventListener('click', closeModal);
$('supplier-modal').addEventListener('click', e => { if (e.target === $('supplier-modal')) closeModal(); });

function openModal() {
  editingSupplierId = null;
  $('modal-title').textContent = 'Nuevo Proveedor';
  $('supplier-form').reset();
  hideAlert('modal-error');
  $('supplier-modal').classList.remove('hidden');
}

async function openEditModal(id) {
  try {
    const s = await apiFetch(`/api/suppliers/${id}`);
    if (!s) return;
    editingSupplierId = id;
    $('modal-title').textContent = 'Editar Proveedor';
    hideAlert('modal-error');

    const form = $('supplier-form');
    const fields = ['business_name','nit','country','city','category','status','contact_name','contact_email','contact_phone','address','notes'];
    fields.forEach(f => {
      const el = form.elements[f];
      if (el) el.value = s[f] ?? '';
    });

    // Deshabilitar NIT en edición (clave de negocio)
    form.elements['nit'].disabled = true;
    $('supplier-modal').classList.remove('hidden');
  } catch (err) {
    showToast('Error cargando proveedor: ' + err.message, 'error');
  }
}

function closeModal() {
  $('supplier-modal').classList.add('hidden');
  editingSupplierId = null;
  const nitField = $('supplier-form').elements['nit'];
  if (nitField) nitField.disabled = false;
}

$('supplier-form').addEventListener('submit', async e => {
  e.preventDefault();
  hideAlert('modal-error');
  const saveBtn = $('modal-save');
  saveBtn.disabled = true;

  const form = e.target;
  const body = {};
  const fields = ['business_name','nit','country','city','category','status','contact_name','contact_email','contact_phone','address','notes'];
  fields.forEach(f => {
    const el = form.elements[f];
    if (el && !el.disabled) body[f] = el.value.trim() || null;
  });

  // Siempre incluir required fields (aunque estén disabled)
  if (!body['business_name']) body['business_name'] = form.elements['business_name'].value;
  if (!body['category']) body['category'] = form.elements['category'].value;

  try {
    if (editingSupplierId) {
      await apiFetch(`/api/suppliers/${editingSupplierId}`, {
        method: 'PUT', body: JSON.stringify(body)
      });
      showToast('Proveedor actualizado correctamente', 'success');
    } else {
      body['nit'] = form.elements['nit'].value.trim();
      await apiFetch('/api/suppliers', {
        method: 'POST', body: JSON.stringify(body)
      });
      showToast('Proveedor creado correctamente', 'success');
    }
    closeModal();
    await loadSuppliers(suppliersPage);
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    showAlert('modal-error', err.message);
  } finally {
    saveBtn.disabled = false;
  }
});

// ─── Delete Modal ─────────────────────────────────
function confirmDelete(id, name) {
  deletingSupplierId = id;
  $('delete-supplier-name').textContent = name;
  $('delete-modal').classList.remove('hidden');
}

$('delete-modal-close').addEventListener('click', () => $('delete-modal').classList.add('hidden'));
$('delete-cancel').addEventListener('click', () => $('delete-modal').classList.add('hidden'));
$('delete-modal').addEventListener('click', e => { if (e.target === $('delete-modal')) $('delete-modal').classList.add('hidden'); });

$('delete-confirm').addEventListener('click', async () => {
  if (!deletingSupplierId) return;
  try {
    await apiFetch(`/api/suppliers/${deletingSupplierId}`, { method: 'DELETE' });
    $('delete-modal').classList.add('hidden');
    showToast('Proveedor eliminado', 'success');
    await loadSuppliers(suppliersPage);
    if (currentPage === 'dashboard') loadDashboard();
  } catch (err) {
    showToast('Error al eliminar: ' + err.message, 'error');
    $('delete-modal').classList.add('hidden');
  }
});

// ─── Import CSV ───────────────────────────────────
$('btn-import-csv').addEventListener('click', () => {
  $('import-modal').classList.remove('hidden');
  $('import-result').classList.add('hidden');
  $('csv-file-input').value = '';
});
$('import-modal-close').addEventListener('click', () => $('import-modal').classList.add('hidden'));
$('import-cancel').addEventListener('click', () => $('import-modal').classList.add('hidden'));
$('import-modal').addEventListener('click', e => { if (e.target === $('import-modal')) $('import-modal').classList.add('hidden'); });

$('import-confirm').addEventListener('click', async () => {
  const file = $('csv-file-input').files[0];
  if (!file) { showToast('Selecciona un archivo CSV primero', 'error'); return; }

  const btn = $('import-confirm');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px"></div> Importando...';

  try {
    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    if (token()) headers['Authorization'] = `Bearer ${token()}`;

    const res = await fetch('/api/suppliers/import-csv', {
      method: 'POST', body: formData, headers
    });
    const result = await res.json();

    const resultEl = $('import-result');
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
      <div class="alert ${result.created > 0 ? 'alert-success' : 'alert-error'}">
        ✅ Creados: <strong>${result.created}</strong> &nbsp;
        ⏭️  Omitidos (ya existían): <strong>${result.skipped}</strong>
        ${result.errors.length ? '<br>⚠️ Errores: ' + result.errors.slice(0,3).join(', ') : ''}
      </div>`;

    if (result.created > 0) {
      await loadSuppliers(0);
      if (currentPage === 'dashboard') loadDashboard();
    }
  } catch (err) {
    showToast('Error al importar: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-upload"></i> Importar';
  }
});

// ─── Audit Log ────────────────────────────────────
$('audit-filter-action').addEventListener('change', () => loadAuditLog(0));

async function loadAuditLog(page = 0) {
  auditPage = page;
  $('audit-loading').classList.remove('hidden');
  $('audit-empty').classList.add('hidden');
  $('audit-table-wrap').classList.add('hidden');

  try {
    const action = $('audit-filter-action').value;
    const params = new URLSearchParams({
      skip: page * AUDIT_SIZE,
      limit: AUDIT_SIZE,
      ...(action && { action }),
    });

    const data = await apiFetch(`/api/audit-logs?${params}`);
    if (!data) return;

    $('audit-loading').classList.add('hidden');

    if (data.items.length === 0) {
      $('audit-empty').classList.remove('hidden');
      return;
    }

    $('audit-table-wrap').classList.remove('hidden');

    const actionBadge = {
      CREATE: '<span class="badge badge-create">Creación</span>',
      UPDATE: '<span class="badge badge-update">Modificación</span>',
      DELETE: '<span class="badge badge-delete">Eliminación</span>',
    };

    $('audit-tbody').innerHTML = data.items.map(log => `
      <tr>
        <td style="font-size:.78rem;color:var(--text-secondary);white-space:nowrap">${formatDate(log.timestamp)}</td>
        <td><strong>${escHtml(log.username || '—')}</strong></td>
        <td>${actionBadge[log.action] || log.action}</td>
        <td>${escHtml(log.supplier_name || '—')}</td>
        <td><code>${escHtml(log.field_changed || '—')}</code></td>
        <td style="color:var(--danger);font-size:.8rem;">${escHtml(log.old_value || '—')}</td>
        <td style="color:var(--success);font-size:.8rem;">${escHtml(log.new_value || '—')}</td>
      </tr>`).join('');

    renderPagination('audit-pagination', data.total, page, AUDIT_SIZE, loadAuditLog);
  } catch (err) {
    $('audit-loading').classList.add('hidden');
    showToast('Error cargando audit log: ' + err.message, 'error');
  }
}

// ─── Users ────────────────────────────────────────
async function loadUsers() {
  try {
    const users = await apiFetch('/api/auth/users');
    if (!users) return;

    $('users-tbody').innerHTML = users.map(u => {
      const roleClass = { admin: 'admin', editor: 'editor', viewer: 'viewer' }[u.role] || '';
      return `
        <tr>
          <td><strong>${escHtml(u.full_name)}</strong></td>
          <td><code>${escHtml(u.username)}</code></td>
          <td style="color:var(--text-secondary)">${escHtml(u.email)}</td>
          <td><span class="role-badge ${roleClass}">${u.role}</span></td>
          <td><span class="badge ${u.is_active ? 'badge-active' : 'badge-inactive'}">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
        </tr>`;
    }).join('');
  } catch (err) {
    showToast('Error cargando usuarios: ' + err.message, 'error');
  }
}

// User Modal
$('btn-new-user').addEventListener('click', () => $('user-modal').classList.remove('hidden'));
$('user-modal-close').addEventListener('click', () => $('user-modal').classList.add('hidden'));
$('user-modal-cancel').addEventListener('click', () => $('user-modal').classList.add('hidden'));

$('user-form').addEventListener('submit', async e => {
  e.preventDefault();
  hideAlert('user-modal-error');
  const form = e.target;
  const body = {
    full_name: form.elements['full_name'].value.trim(),
    username: form.elements['username'].value.trim(),
    email: form.elements['email'].value.trim(),
    password: form.elements['password'].value,
    role: form.elements['role'].value,
  };
  try {
    await apiFetch('/api/auth/users', { method: 'POST', body: JSON.stringify(body) });
    $('user-modal').classList.add('hidden');
    form.reset();
    showToast('Usuario creado correctamente', 'success');
    loadUsers();
  } catch (err) {
    showAlert('user-modal-error', err.message);
  }
});

// ─── Init ─────────────────────────────────────────
(async () => {
  if (token()) {
    try {
      await loadUserAndStart();
    } catch {
      logout();
    }
  }
})();
