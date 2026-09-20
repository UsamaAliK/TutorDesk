(() => {
  const form = document.querySelector('[data-auth-form]');
  if (!form) return;
  if (localStorage.getItem('tutordesk_token')) {
    window.location.replace('/app');
    return;
  }

  const apiBase = document.querySelector('meta[name="api-base"]')?.content.replace(/\/$/, '') || '';
  const tabs = [...document.querySelectorAll('[data-auth-mode]')];
  const email = form.elements.email;
  const password = form.elements.password;
  const confirmField = document.querySelector('.confirm-field');
  const confirmPassword = form.elements['confirm-password'];
  const submit = form.querySelector('.submit');
  const submitLabel = form.querySelector('[data-submit-label]');
  const submitIcon = form.querySelector('[data-submit-icon]');
  const error = form.querySelector('.error');
  const introEyebrow = document.querySelector('.auth-card header .eyebrow');
  const introTitle = document.querySelector('.auth-card header h2');
  const introCopy = document.querySelector('.auth-card header p:last-child');
  const switchCopy = document.querySelector('[data-switch-copy]');
  const switchButton = document.querySelector('[data-switch-mode]');
  let mode = 'signin';

  function setError(message = '', success = false) {
    error.textContent = message;
    error.hidden = !message;
    error.classList.toggle('success', success);
  }

  function setMode(nextMode) {
    mode = nextMode;
    const signingUp = mode === 'signup';
    tabs.forEach((tab) => {
      const active = tab.dataset.authMode === mode;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    confirmField.hidden = !signingUp;
    confirmPassword.required = signingUp;
    password.autocomplete = signingUp ? 'new-password' : 'current-password';
    introEyebrow.textContent = signingUp ? 'Start your journey' : 'Welcome back';
    introTitle.textContent = signingUp ? 'Create your account' : 'Continue learning';
    introCopy.textContent = signingUp ? 'Your AI study partner is ready when you are.' : 'Sign in to pick up where you left off.';
    submitLabel.textContent = signingUp ? 'Create Account' : 'Sign In';
    switchCopy.textContent = signingUp ? 'Already have an account?' : 'New to TutorDesk?';
    switchButton.textContent = signingUp ? 'Sign in' : 'Create an account';
    setError();
  }

  function setLoading(loading) {
    submit.disabled = loading;
    submit.classList.toggle('is-loading', loading);
    submitLabel.textContent = loading ? (mode === 'signup' ? 'Creating account...' : 'Signing in...') : (mode === 'signup' ? 'Create Account' : 'Sign In');
    submitIcon.hidden = loading;
  }

  tabs.forEach((tab) => tab.addEventListener('click', () => setMode(tab.dataset.authMode)));
  switchButton.addEventListener('click', () => setMode(mode === 'signup' ? 'signin' : 'signup'));
  document.querySelector('[data-forgot-password]').addEventListener('click', (event) => {
    event.preventDefault();
    setError('Password reset is not available yet. Please contact your administrator.');
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setError();
    if (!email.validity.valid) return setError('Enter a valid email address.');
    if (password.value.length < 8) return setError('Password must be at least 8 characters.');
    if (mode === 'signup' && password.value !== confirmPassword.value) return setError('Passwords do not match.');

    setLoading(true);
    try {
      const endpoint = mode === 'signup' ? '/signup' : '/login';
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.value.trim(), password: password.value }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Something went wrong. Please try again.');
      if (mode === 'signup') {
        setMode('signin');
        password.value = '';
        confirmPassword.value = '';
        setError('Account created. Sign in to continue.', true);
        return;
      }
      localStorage.setItem('tutordesk_token', body.access_token);
      window.location.assign('/app');
    } catch (requestError) {
      setError(requestError.message || 'Unable to reach TutorDesk. Please try again.');
    } finally {
      setLoading(false);
    }
  });
})();

(() => {
  if (!document.body.classList.contains('app-page')) return;

  const token = localStorage.getItem('tutordesk_token');
  if (!token) { window.location.replace('/'); return; }
  const apiBase = document.querySelector('meta[name="api-base"]')?.content.replace(/\/$/, '') || '';
  const thread = document.querySelector('.message-thread');
  const form = document.querySelector('.message-form');
  const input = document.querySelector('#message-input');
  const fileInput = document.querySelector('#pdf-input');
  const attach = document.querySelector('.attach-button');
  const send = document.querySelector('.send-button');
  const composer = document.querySelector('.composer');
  const dropzone = document.querySelector('.upload-dropzone');
  const status = document.querySelector('.upload-status');
  let conversationId = null;

  function authHeaders(extra = {}) { return { Authorization: `Bearer ${token}`, ...extra }; }
  function setStatus(message = '', isError = false) { status.textContent = message; status.classList.toggle('error', isError); }
  function scrollThread() { thread.scrollTop = thread.scrollHeight; }
  function timestamp() { return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date()); }
  function appendInline(container, value) {
    const pieces = value.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<]+)/g);
    pieces.forEach((piece) => {
      if (piece.startsWith('**') && piece.endsWith('**')) { const strong = document.createElement('strong'); strong.textContent = piece.slice(2, -2); container.append(strong); }
      else if (piece.startsWith('`') && piece.endsWith('`')) { const code = document.createElement('code'); code.textContent = piece.slice(1, -1); container.append(code); }
      else if (piece.startsWith('[')) { const match = piece.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/); if (match) { const link = document.createElement('a'); link.href = match[2]; link.textContent = match[1]; link.target = '_blank'; link.rel = 'noopener noreferrer'; container.append(link); } else container.append(document.createTextNode(piece)); }
      else if (/^https?:\/\//.test(piece)) { const link = document.createElement('a'); link.href = piece; link.textContent = piece; link.target = '_blank'; link.rel = 'noopener noreferrer'; container.append(link); }
      else container.append(document.createTextNode(piece));
    });
  }
  function renderMarkdown(container, value) {
    container.classList.add('message-markdown');
    const lines = value.split('\n'); let list = null; let listType = '';
    const closeList = () => { list = null; listType = ''; };
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      if (line.startsWith('```')) { closeList(); const block = []; i += 1; while (i < lines.length && !lines[i].startsWith('```')) block.push(lines[i++]); const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = block.join('\n'); pre.append(code); container.append(pre); continue; }
      const heading = line.match(/^(#{1,3})\s+(.+)/);
      const bullet = line.match(/^[-*]\s+(.+)/);
      const numbered = line.match(/^\d+\.\s+(.+)/);
      if (heading) { closeList(); const node = document.createElement(`h${heading[1].length}`); appendInline(node, heading[2]); container.append(node); continue; }
      if (bullet || numbered) { const type = numbered ? 'ol' : 'ul'; if (!list || listType !== type) { closeList(); list = document.createElement(type); listType = type; container.append(list); } const item = document.createElement('li'); appendInline(item, (bullet || numbered)[1]); list.append(item); continue; }
      closeList(); if (line.trim()) { const paragraph = document.createElement('p'); appendInline(paragraph, line); container.append(paragraph); }
    }
  }
  function addMessage(role, text, typing = false) {
    thread.querySelector('.thread-welcome')?.remove();
    const item = document.createElement('article');
    item.className = `message ${role}${typing ? ' typing' : ''}`;
    const avatar = document.createElement('span'); avatar.className = 'message-avatar'; avatar.textContent = role === 'user' ? 'You' : 'TD';
    const content = document.createElement('div'); content.className = 'message-content';
    const bubble = document.createElement('div'); bubble.className = 'message-bubble';
    if (role === 'assistant' && !typing) renderMarkdown(bubble, text); else bubble.textContent = text;
    const time = document.createElement('time'); time.className = 'message-time'; time.textContent = typing ? '' : timestamp();
    content.append(bubble, time); item.append(avatar, content); thread.append(item); scrollThread();
    return item;
  }
  function resizeInput() { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 140)}px`; }
  async function apiError(response) { const body = await response.json().catch(() => ({})); if (response.status === 401) { localStorage.removeItem('tutordesk_token'); window.location.assign('/'); } return body.detail || 'Request failed. Please try again.'; }

  input.addEventListener('input', resizeInput);
  input.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
  attach.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => uploadFile(fileInput.files[0]));
  form.addEventListener('submit', async (event) => {
    event.preventDefault(); const query = input.value.trim(); if (!query || send.disabled) return;
    setStatus(); addMessage('user', query); input.value = ''; resizeInput(); send.disabled = true;
    const typing = addMessage('assistant', 'TutorDesk is thinking…', true);
    try {
      const response = await fetch(`${apiBase}/ask`, { method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ query, conversation_id: conversationId }) });
      if (!response.ok) throw new Error(await apiError(response));
      const body = await response.json(); conversationId = body.conversation_id || conversationId;
      if (conversationId) localStorage.setItem('tutordesk_active_conversation', String(conversationId));
      typing.remove(); addMessage('assistant', body.response || 'I could not generate a response.');
      window.dispatchEvent(new CustomEvent('tutordesk:conversation-updated', { detail: { id: conversationId, title: query } }));
      window.dispatchEvent(new CustomEvent('tutordesk:sources', { detail: body.sources || [] }));
    } catch (error) { typing.remove(); addMessage('assistant', error.message || 'Unable to reach TutorDesk.'); }
    finally { send.disabled = false; input.focus(); }
  });
  async function uploadFile(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) return setStatus('Please select a PDF file.', true);
    if (file.size > 20 * 1024 * 1024) return setStatus('PDF must be 20 MB or smaller.', true);
    attach.disabled = true; setStatus(`Uploading ${file.name}…`);
    try {
      const data = new FormData(); data.append('file', file);
      const response = await fetch(`${apiBase}/upload`, { method: 'POST', headers: authHeaders(), body: data });
      if (!response.ok) throw new Error(await apiError(response));
      setStatus(`${file.name} uploaded and indexed successfully.`);
    } catch (error) { setStatus(error.message || 'Upload failed. Please try again.', true); }
    finally { attach.disabled = false; fileInput.value = ''; }
  }
  ['dragenter', 'dragover'].forEach((name) => composer.addEventListener(name, (event) => { event.preventDefault(); composer.classList.add('drag-over'); dropzone.hidden = false; }));
  ['dragleave', 'drop'].forEach((name) => composer.addEventListener(name, (event) => { event.preventDefault(); composer.classList.remove('drag-over'); dropzone.hidden = true; }));
  composer.addEventListener('drop', (event) => uploadFile(event.dataTransfer.files[0]));
  window.addEventListener('tutordesk:select-conversation', (event) => {
    const { id, title, messages } = event.detail; conversationId = id;
    localStorage.setItem('tutordesk_active_conversation', String(id));
    thread.replaceChildren(); messages.forEach((message) => addMessage(message.role, message.content));
    document.querySelector('[data-conversation-title]').textContent = title;
  });
  window.addEventListener('tutordesk:new-conversation', () => {
    conversationId = null; localStorage.removeItem('tutordesk_active_conversation'); thread.innerHTML = '<div class="thread-welcome"><div class="welcome-icon">✦</div><h2>What would you like to create?</h2><p>Build a lesson plan, quiz, MCQs, worksheet, or classroom activity from your material—or research a topic from the web.</p></div>';
    document.querySelector('[data-conversation-title]').textContent = 'New conversation';
    window.dispatchEvent(new CustomEvent('tutordesk:sources', { detail: [] }));
  });
})();

(() => {
  if (!document.body.classList.contains('app-page')) return;

  const sidebar = document.querySelector('.conversation-sidebar');
  const sources = document.querySelector('.sources-sidebar');
  const scrim = document.querySelector('.sidebar-scrim');
  const closeSidebar = () => { sidebar.classList.remove('is-open'); scrim.classList.remove('is-visible'); };
  document.querySelector('.menu-button').addEventListener('click', () => { sidebar.classList.add('is-open'); scrim.classList.add('is-visible'); });
  document.querySelector('.close-sidebar').addEventListener('click', closeSidebar);
  scrim.addEventListener('click', closeSidebar);
  document.querySelectorAll('.conversation').forEach((item) => item.addEventListener('click', () => { document.querySelector('.conversation.active')?.classList.remove('active'); item.classList.add('active'); closeSidebar(); }));
  document.querySelector('.sources-toggle').addEventListener('click', () => sources.classList.add('is-open'));
  document.querySelector('.sources-sidebar header button').addEventListener('click', () => sources.classList.remove('is-open'));
  document.querySelector('[data-logout]').addEventListener('click', () => { localStorage.removeItem('tutordesk_token'); window.location.assign('/'); });
})();

(() => {
  if (!document.body.classList.contains('app-page')) return;
  const token = localStorage.getItem('tutordesk_token');
  if (!token) return;
  const apiBase = document.querySelector('meta[name="api-base"]')?.content.replace(/\/$/, '') || '';
  const list = document.querySelector('.conversation-list');
  const title = document.querySelector('[data-conversation-title]');
  const email = document.querySelector('.user-email');
  const sourceList = document.querySelector('.sources-list');
  const headers = { Authorization: `Bearer ${token}` };
  const request = async (path) => {
    const response = await fetch(`${apiBase}${path}`, { headers });
    if (!response.ok) throw new Error('Unable to load your workspace.');
    return response.json();
  };
  const dateGroup = (value) => {
    const date = new Date(value); const now = new Date(); const days = Math.floor((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - new Date(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000);
    return days === 0 ? 'Today' : days === 1 ? 'Yesterday' : 'Older';
  };
  const displayDate = (value) => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value));
  function renderConversations(conversations) {
    list.replaceChildren();
    const groups = new Map([['Today', []], ['Yesterday', []], ['Older', []]]);
    conversations.forEach((item) => groups.get(dateGroup(item.created_at)).push(item));
    groups.forEach((items, group) => {
      if (!items.length) return;
      const section = document.createElement('section'); const heading = document.createElement('h3'); heading.textContent = group; section.append(heading);
      items.forEach((item) => {
        const button = document.createElement('button'); button.className = 'conversation'; button.type = 'button'; button.dataset.id = item.id;
        button.innerHTML = `<strong></strong><small>${group === 'Older' ? displayDate(item.created_at) : group}</small><span class="delete-conversation" aria-hidden="true">⌫</span>`;
        button.querySelector('strong').textContent = item.title || 'Untitled conversation';
        button.addEventListener('click', () => loadConversation(item, button)); section.append(button);
      });
      list.append(section);
    });
  }
  async function loadConversation(conversation, button) {
    try {
      const messages = await request(`/conversations/${conversation.id}/messages`);
      document.querySelector('.conversation.active')?.classList.remove('active'); button.classList.add('active'); title.textContent = conversation.title || 'Untitled conversation';
      window.dispatchEvent(new CustomEvent('tutordesk:select-conversation', { detail: { id: conversation.id, title: title.textContent, messages } }));
    } catch (error) { title.textContent = error.message; }
  }
  async function refreshConversations({ restore = false, activeId = null } = {}) {
    try {
      const conversations = await request('/conversations'); renderConversations(conversations);
      const selectedId = activeId || Number(localStorage.getItem('tutordesk_active_conversation'));
      const selectedButton = selectedId && document.querySelector(`[data-id="${selectedId}"]`);
      if (selectedButton) selectedButton.classList.add('active');
      if (restore && selectedButton) {
        const selectedConversation = conversations.find((conversation) => conversation.id === selectedId);
        if (selectedConversation) await loadConversation(selectedConversation, selectedButton);
      }
    } catch (error) { list.textContent = error.message; }
  }
  document.querySelector('.new-conversation').addEventListener('click', () => window.dispatchEvent(new Event('tutordesk:new-conversation')));
  window.addEventListener('tutordesk:conversation-updated', (event) => { title.textContent = event.detail.title.slice(0, 60); refreshConversations({ activeId: event.detail.id }); });
  window.addEventListener('tutordesk:sources', (event) => {
    sourceList.replaceChildren(); const sources = event.detail;
    if (!sources.length) { sourceList.innerHTML = '<p class="sources-empty">No sources were returned for this response.</p>'; return; }
    sources.forEach((source) => { const card = document.createElement('article'); card.className = 'source-card'; const link = source.url || source; const label = source.title || link; card.innerHTML = `<span class="source-icon">◎</span><div><strong></strong><a target="_blank" rel="noopener noreferrer"></a></div>`; card.querySelector('strong').textContent = label; const anchor = card.querySelector('a'); anchor.href = link; try { anchor.textContent = new URL(link).hostname; } catch { anchor.textContent = link; } sourceList.append(card); });
  });
  fetch(`${apiBase}/me`, { headers }).then((response) => {
    if (response.status === 401) {
      localStorage.removeItem('tutordesk_token');
      window.location.replace('/');
      return null;
    }
    if (!response.ok) return null;
    return response.json();
  }).then((user) => { if (user) email.textContent = user.email; });
  refreshConversations({ restore: true });
})();

(() => {
  const toggle = document.querySelector('[data-theme-toggle]');
  if (!toggle) return;
  const applyTheme = (dark) => {
    document.body.classList.toggle('dark-theme', dark);
    toggle.setAttribute('aria-pressed', String(dark));
    toggle.innerHTML = `<span aria-hidden="true">${dark ? '☀' : '◐'}</span> ${dark ? 'Light theme' : 'Dark theme'}`;
  };
  applyTheme(localStorage.getItem('tutordesk_theme') === 'dark');
  toggle.addEventListener('click', () => {
    const dark = !document.body.classList.contains('dark-theme');
    localStorage.setItem('tutordesk_theme', dark ? 'dark' : 'light');
    applyTheme(dark);
  });
})();
