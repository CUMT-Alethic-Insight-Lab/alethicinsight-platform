(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const key = 'member_platform_session_v1';
  const prefix = document.body.dataset.prefix.includes('__PREFIX__') ? '' : document.body.dataset.prefix;
  let token = localStorage.getItem(key) || '';
  let secretTimer = null;
  function message(value) { $('status').textContent = value; }
  async function hash(password, salt) {
    const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
    const bytes = Uint8Array.from(salt.match(/../g), value => parseInt(value, 16));
    const result = await crypto.subtle.deriveBits({name: 'PBKDF2', salt: bytes, iterations: 100000, hash: 'SHA-256'}, material, 256);
    return Array.from(new Uint8Array(result), value => value.toString(16).padStart(2, '0')).join('');
  }
  async function api(path, body) {
    const response = await fetch(prefix + '/api/' + path, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store', credentials: 'omit', redirect: 'error',
      headers: Object.assign(token ? {Authorization: 'Bearer ' + token} : {}, body === undefined ? {} : {'Content-Type': 'application/json'}),
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求失败：HTTP ' + response.status);
    return data;
  }
  function temporary(value) {
    clearTimeout(secretTimer);
    $('temporary-password').textContent = value || '';
    if (value) secretTimer = setTimeout(() => temporary(''), 60000);
  }
  function form(id, callback) {
    $(id).addEventListener('submit', async event => {
      event.preventDefault();
      const button = $(id).querySelector('button[type=submit]');
      button.disabled = true;
      try { await callback(); } catch (error) { message(error.message); }
      finally { button.disabled = false; }
    });
  }
  async function refresh() {
    if (!token) { $('account').hidden = true; $('admin').hidden = true; return; }
    try {
      const me = await api('auth/me');
      $('account').hidden = false;
      $('identity').textContent = me.student_id + ' · ' + me.role + (me.pw_changed ? '' : ' · 必须修改初始密码');
      $('admin').hidden = me.role !== 'admin' || !me.pw_changed;
      message(me.pw_changed ? '已登录，可前往成员事务。' : '请先修改初始密码。');
    } catch (error) {
      localStorage.removeItem(key); token = ''; $('account').hidden = true; $('admin').hidden = true; message(error.message);
    }
  }
  form('login-form', async () => {
    const id = $('student-id').value.trim();
    const salt = (await api('auth/salt?student_id=' + encodeURIComponent(id))).salt;
    const data = await api('auth/login', {student_id: id, client_hash: await hash($('password').value, salt)});
    $('password').value = ''; token = data.token; localStorage.setItem(key, token); temporary(''); await refresh();
  });
  form('password-form', async () => {
    const me = await api('auth/me');
    const password = $('new-password').value;
    if (password.length < 12 || password !== $('repeat-password').value || password === $('old-password').value) throw new Error('请使用至少 12 字符的新密码，并确认两次输入相同且不同于原密码。');
    const oldSalt = (await api('auth/salt?student_id=' + encodeURIComponent(me.student_id))).salt;
    const newSalt = Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, '0')).join('');
    await api('auth/change_password', {old_client_hash: await hash($('old-password').value, oldSalt), new_salt: newSalt, new_client_hash: await hash(password, newSalt)});
    $('old-password').value = ''; $('new-password').value = ''; $('repeat-password').value = ''; await refresh();
  });
  $('logout').addEventListener('click', async () => {
    try { await api('auth/logout', {}); } catch (_) { /* Local logout still clears the member token. */ }
    token = ''; localStorage.removeItem(key); temporary(''); $('members').replaceChildren(); await refresh(); message('已注销本服务会话。');
  });
  async function members() {
    const data = await api('admin/accounts');
    $('members').replaceChildren();
    for (const member of data.items) {
      const row = document.createElement('div');
      const title = document.createElement('p'); title.textContent = member.student_id + ' · ' + member.nickname + ' · ' + member.role; row.appendChild(title);
      const select = document.createElement('select'); select.setAttribute('aria-label', member.student_id + ' 角色');
      for (const role of ['member', 'admin', 'inactive']) { const option = document.createElement('option'); option.value = role; option.textContent = role; select.appendChild(option); }
      select.value = member.role;
      const change = document.createElement('button'); change.type = 'button'; change.textContent = '修改角色并撤销会话';
      const reset = document.createElement('button'); reset.type = 'button'; reset.textContent = '重置密码并撤销会话';
      change.addEventListener('click', async () => {
        if (!window.confirm('确认修改 ' + member.student_id + ' 的角色并撤销所有授权？')) return;
        change.disabled = true;
        try { await api('admin/accounts/' + encodeURIComponent(member.student_id) + '/role', {role: select.value}); await members(); } catch (e) { message(e.message); } finally { change.disabled = false; }
      });
      reset.addEventListener('click', async () => {
        if (!window.confirm('确认重置 ' + member.student_id + ' 密码并撤销所有授权？')) return;
        reset.disabled = true;
        try { const result = await api('admin/accounts/' + encodeURIComponent(member.student_id) + '/reset_password', {}); temporary(member.student_id + ': ' + result.temporary_password); await refresh(); } catch (e) { message(e.message); } finally { reset.disabled = false; }
      });
      row.append(select, change, reset); $('members').appendChild(row);
    }
  }
  $('refresh-members').addEventListener('click', () => members().catch(e => message(e.message)));
  $('hide-password').addEventListener('click', () => temporary(''));
  form('create-form', async () => {
    const result = await api('admin/accounts', {student_id: $('create-id').value, nickname: $('create-name').value, role: $('create-role').value});
    temporary(result.student_id + ': ' + result.temporary_password); await members();
  });
  window.addEventListener('pagehide', () => temporary(''));
  refresh();
})();
