// ── Auth Handling (Login & Signup) ───────────────────────────────────
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
  document.querySelector('[data-forgot-password]')?.addEventListener('click', (event) => {
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

// ── Application Workspace & Generator Controllers ────────────────────
(() => {
  if (!document.body.classList.contains('app-page')) return;

  const token = localStorage.getItem('tutordesk_token');
  if (!token) { window.location.replace('/'); return; }
  const apiBase = document.querySelector('meta[name="api-base"]')?.content.replace(/\/$/, '') || '';
  const headers = { Authorization: `Bearer ${token}` };

  function authHeaders(extra = {}) { return { Authorization: `Bearer ${token}`, ...extra }; }
  async function apiError(response) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      localStorage.removeItem('tutordesk_token');
      window.location.assign('/');
    }
    return body.detail || 'Request failed. Please try again.';
  }

  // ── Views Navigation ────────────────────────────────────────────────
  const viewNavItems = document.querySelectorAll('[data-view-target]');
  const appViews = document.querySelectorAll('.app-view');
  const viewTitle = document.querySelector('#workspace-view-title');
  let currentAudience = 'teacher';
  let activeMaterial = null;

  function switchView(target) {
    viewNavItems.forEach((btn) => btn.classList.toggle('is-active', btn.dataset.viewTarget === target));
    appViews.forEach((view) => {
      const active = view.id === `view-${target}`;
      view.classList.toggle('is-active', active);
      view.hidden = !active;
    });

    if (target === 'generator') {
      viewTitle.textContent = 'Educational Content Generator';
    } else if (target === 'library') {
      viewTitle.textContent = 'Saved Materials Library';
      loadLibraryMaterials();
    } else if (target === 'chat') {
      viewTitle.textContent = 'Teaching Assistant Chat';
    }
    // Mobile sidebar close on view switch
    document.querySelector('.conversation-sidebar')?.classList.remove('is-open');
    document.querySelector('.sidebar-scrim')?.classList.remove('is-visible');
  }

  viewNavItems.forEach((btn) => btn.addEventListener('click', () => switchView(btn.dataset.viewTarget)));

  // ── Generator Dynamic Form Modal ────────────────────────────────────
  const modal = document.querySelector('#generator-modal');
  const modalBadge = document.querySelector('#modal-type-badge');
  const modalTitle = document.querySelector('#modal-title');
  const closeModalBtn = document.querySelector('#close-modal-btn');
  const cancelFormBtn = document.querySelector('#cancel-form-btn');
  const genForm = document.querySelector('#generator-form');
  const submitGenBtn = document.querySelector('#submit-generate-btn');
  const btnText = submitGenBtn.querySelector('.btn-text');
  const btnSpinner = submitGenBtn.querySelector('.btn-spinner');

  const fieldsLesson = document.querySelector('#fields-lesson');
  const fieldsQuiz = document.querySelector('#fields-quiz');
  const fieldsAssignment = document.querySelector('#fields-assignment');

  let activeGenerationType = 'lesson';

  function openGeneratorForm(type) {
    activeGenerationType = type;
    modal.hidden = false;

    fieldsLesson.hidden = type !== 'lesson';
    fieldsQuiz.hidden = type !== 'quiz';
    fieldsAssignment.hidden = type !== 'assignment';

    if (type === 'lesson') {
      modalBadge.textContent = 'Lesson Plan';
      modalTitle.textContent = 'Configure Lesson Plan';
      btnText.textContent = 'Generate Lesson Plan';
    } else if (type === 'quiz') {
      modalBadge.textContent = 'Assessment Quiz';
      modalTitle.textContent = 'Configure Assessment Quiz';
      btnText.textContent = 'Generate Quiz';
      validateQuizDistributor();
    } else if (type === 'assignment') {
      modalBadge.textContent = 'Student Assignment';
      modalTitle.textContent = 'Configure Assignment';
      btnText.textContent = 'Generate Assignment';
    }
  }

  function closeGeneratorModal() {
    modal.hidden = true;
  }

  document.querySelectorAll('[data-open-form]').forEach((card) => {
    card.addEventListener('click', () => openGeneratorForm(card.dataset.openForm));
  });

  closeModalBtn?.addEventListener('click', closeGeneratorModal);
  cancelFormBtn?.addEventListener('click', closeGeneratorModal);

  // Duration Pills
  const durationPills = document.querySelectorAll('.duration-pill');
  const hiddenDuration = document.querySelector('#form-lesson-duration');
  durationPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      durationPills.forEach((p) => p.classList.remove('is-active'));
      pill.classList.add('is-active');
      hiddenDuration.value = pill.dataset.minutes;
    });
  });

  // Suggestion Chips
  const instructionsBox = document.querySelector('#form-instructions');
  document.querySelectorAll('.inst-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const addition = chip.dataset.text;
      const current = instructionsBox.value.trim();
      instructionsBox.value = current ? `${current} ${addition}` : addition;
      instructionsBox.focus();
    });
  });

  // Quiz Question Distributor Validation
  const quizTotal = document.querySelector('#form-quiz-total');
  const quizMCQs = document.querySelector('#form-quiz-mcqs');
  const quizShort = document.querySelector('#form-quiz-short');
  const quizLong = document.querySelector('#form-quiz-long');
  const distStatus = document.querySelector('#distributor-status');
  const distHint = document.querySelector('#distributor-hint');

  function validateQuizDistributor() {
    if (activeGenerationType !== 'quiz') return true;
    const total = parseInt(quizTotal.value, 10) || 0;
    const mcqs = parseInt(quizMCQs.value, 10) || 0;
    const short = parseInt(quizShort.value, 10) || 0;
    const long = parseInt(quizLong.value, 10) || 0;
    const currentSum = mcqs + short + long;

    if (currentSum === total && total > 0) {
      distStatus.textContent = `Total: ${total} / ${total} Balanced`;
      distStatus.classList.remove('error');
      distHint.textContent = '✓ Distribution is valid and matches total questions.';
      submitGenBtn.disabled = false;
      return true;
    } else {
      const diff = total - currentSum;
      distStatus.textContent = `Total: ${currentSum} / ${total}`;
      distStatus.classList.add('error');
      distHint.textContent = diff > 0
        ? `⚠️ Please allocate ${diff} more question${diff > 1 ? 's' : ''}.`
        : `⚠️ Distribution exceeds total by ${Math.abs(diff)} question${Math.abs(diff) > 1 ? 's' : ''}.`;
      submitGenBtn.disabled = true;
      return false;
    }
  }

  [quizTotal, quizMCQs, quizShort, quizLong].forEach((el) => {
    el?.addEventListener('input', validateQuizDistributor);
  });

  // Form Submit Handler
  genForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (activeGenerationType === 'quiz' && !validateQuizDistributor()) return;

    submitGenBtn.disabled = true;
    btnText.textContent = 'Generating Content…';

    const subject = document.querySelector('#form-subject').value.trim();
    const topic = document.querySelector('#form-topic').value.trim();
    const educational_level = document.querySelector('#form-level').value;
    const source_mode = document.querySelector('#form-source-mode').value;
    const additional_instructions = instructionsBox.value.trim() || null;

    let endpoint = '';
    let payload = { subject, topic, educational_level, source_mode, additional_instructions };

    if (activeGenerationType === 'lesson') {
      endpoint = '/materials/lessons/generate';
      payload.duration_minutes = parseInt(hiddenDuration.value, 10) || 45;
      payload.teaching_style = document.querySelector('#form-lesson-style').value.trim() || null;
      payload.learning_objectives = document.querySelector('#form-lesson-objectives').value.trim() || null;
    } else if (activeGenerationType === 'quiz') {
      endpoint = '/materials/quizzes/generate';
      payload.difficulty = document.querySelector('#form-quiz-difficulty').value;
      payload.total_questions = parseInt(quizTotal.value, 10);
      payload.num_mcqs = parseInt(quizMCQs.value, 10);
      payload.num_short_answer = parseInt(quizShort.value, 10);
      payload.num_long_answer = parseInt(quizLong.value, 10);
      payload.mcq_options_count = parseInt(document.querySelector('#form-quiz-options-count').value, 10);
      payload.include_answer_key = true;
      payload.include_explanations = true;
    } else if (activeGenerationType === 'assignment') {
      endpoint = '/materials/assignments/generate';
      payload.difficulty = document.querySelector('#form-assignment-difficulty').value;
      payload.total_tasks = parseInt(document.querySelector('#form-assignment-tasks-count').value, 10);
      const selectedTypes = [...document.querySelectorAll('input[name="task_type"]:checked')].map((cb) => cb.value);
      payload.task_types = selectedTypes.length ? selectedTypes : ['short_answer', 'problem_solving'];
    }

    try {
      const res = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await apiError(res));
      const material = await res.json();
      closeGeneratorModal();
      openContentWorkspace(material);
      updateMaterialsBadge();
    } catch (err) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      submitGenBtn.disabled = false;
      btnText.textContent = 'Generate Content';
    }
  });

  // ── Dedicated Content Workspace ─────────────────────────────────────
  const generatorHub = document.querySelector('#generator-hub');
  const workspaceView = document.querySelector('#content-workspace');
  const documentSurface = document.querySelector('#document-surface');
  const backToHubBtn = document.querySelector('#back-to-hub-btn');
  const audienceButtons = document.querySelectorAll('.seg-btn');
  const btnExportPdf = document.querySelector('#btn-export-pdf');
  const btnExportDocx = document.querySelector('#btn-export-docx');

  backToHubBtn?.addEventListener('click', () => {
    workspaceView.hidden = true;
    generatorHub.hidden = false;
    activeMaterial = null;
  });

  audienceButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      audienceButtons.forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      currentAudience = btn.dataset.audience;
      if (activeMaterial) renderDocumentSurface(activeMaterial);
    });
  });

  function openContentWorkspace(material) {
    activeMaterial = material;
    generatorHub.hidden = true;
    workspaceView.hidden = false;
    renderDocumentSurface(material);
    // Broadcast sources to sources sidebar
    const sources = material.content_json?.sources || [];
    window.dispatchEvent(new CustomEvent('tutordesk:sources', { detail: sources }));
  }

  function renderDocumentSurface(material) {
    const content = material.content_json || {};
    const mtype = material.type.toLowerCase();
    const isTeacher = currentAudience === 'teacher';

    let html = `
      <div class="doc-header-block">
        <div class="doc-header-badges">
          <span class="meta-tag">${mtype.toUpperCase()}</span>
          <span class="meta-tag">${material.educational_level}</span>
          ${material.difficulty ? `<span class="meta-tag">${material.difficulty}</span>` : ''}
          <span class="meta-tag source-tag">${material.source_mode.replace('_', ' ').toUpperCase()}</span>
        </div>
        <h2 class="doc-editable-title" contenteditable="true" data-field="title">${material.title || 'Untitled Material'}</h2>
        ${content.overview ? `<p class="doc-overview" contenteditable="true" data-field="overview">${content.overview}</p>` : ''}
      </div>
    `;

    if (mtype === 'lesson') {
      if (content.learning_objectives?.length) {
        html += `
          <div class="doc-section-card">
            <h3 class="doc-section-title">Learning Objectives</h3>
            <ul class="doc-section-body">
              ${content.learning_objectives.map((obj) => `<li>${obj}</li>`).join('')}
            </ul>
          </div>
        `;
      }
      (content.sections || []).forEach((sec, idx) => {
        html += `
          <div class="doc-section-card" data-sec-id="${sec.id || idx + 1}">
            <div class="doc-section-header">
              <h3 class="doc-section-title">${sec.title} (${sec.time_minutes || 10} min)</h3>
              <button class="item-regen-btn" type="button" data-regen-type="section" data-item-id="${sec.id || idx + 1}">🔄 Regenerate Section</button>
            </div>
            <div class="doc-section-body" contenteditable="true" data-sec-field="concepts">
              <p>${sec.concepts || ''}</p>
              ${sec.examples?.length ? `<p><strong>Examples:</strong><br>${sec.examples.join('<br>')}</p>` : ''}
              ${sec.activities ? `<p><strong>Class Activity:</strong><br>${sec.activities}</p>` : ''}
            </div>
          </div>
        `;
      });
      if (content.summary) {
        html += `
          <div class="doc-section-card">
            <h3 class="doc-section-title">Summary & Key Takeaways</h3>
            <p class="doc-section-body">${content.summary}</p>
          </div>
        `;
      }
    } else if (mtype === 'quiz') {
      html += `
        <div class="doc-section-card">
          <p class="doc-section-body">${content.instructions_for_students || 'Answer all questions carefully.'}</p>
        </div>
      `;
      (content.questions || []).forEach((q, idx) => {
        const isMcq = q.type === 'mcq' && q.options?.length;
        html += `
          <div class="doc-section-card" data-q-id="${q.id || idx + 1}">
            <div class="doc-section-header">
              <h3 class="doc-section-title">Question ${idx + 1} (${q.type?.toUpperCase()} — ${q.marks || 1} pt)</h3>
              <button class="item-regen-btn" type="button" data-regen-type="question" data-item-id="${q.id || idx + 1}">🔄 Regenerate Question</button>
            </div>
            <div class="doc-section-body">
              <p contenteditable="true">${q.prompt}</p>
              ${isMcq ? `
                <ul class="quiz-options-list">
                  ${q.options.map((opt) => {
                    const isCorrect = isTeacher && (opt === q.correct_answer || opt.startsWith(q.correct_answer?.slice(0, 2)));
                    return `<li class="quiz-opt-item ${isCorrect ? 'is-correct' : ''}">${opt}</li>`;
                  }).join('')}
                </ul>
              ` : ''}
              ${isTeacher ? `
                <div class="doc-teacher-box">
                  <strong>Teacher Answer Key:</strong> ${q.correct_answer || 'See criteria'}
                  ${q.explanation ? `<br><strong>Explanation:</strong> ${q.explanation}` : ''}
                </div>
              ` : ''}
            </div>
          </div>
        `;
      });
    } else if (mtype === 'assignment') {
      html += `
        <div class="doc-section-card">
          <p class="doc-section-body">${content.instructions_for_students || 'Complete the following tasks.'}</p>
        </div>
      `;
      (content.tasks || []).forEach((t, idx) => {
        html += `
          <div class="doc-section-card" data-t-id="${t.id || idx + 1}">
            <div class="doc-section-header">
              <h3 class="doc-section-title">Task ${idx + 1}: ${t.title || ''} [${t.marks || 5} marks]</h3>
              <button class="item-regen-btn" type="button" data-regen-type="task" data-item-id="${t.id || idx + 1}">🔄 Regenerate Task</button>
            </div>
            <div class="doc-section-body">
              <p contenteditable="true">${t.prompt}</p>
              ${isTeacher ? `
                <div class="doc-teacher-box">
                  <strong>Model Answer / Solution:</strong> ${t.model_answer || 'Criteria-based'}
                  ${t.rubric_criteria?.length ? `
                    <br><strong>Marking Rubric:</strong>
                    <ul>${t.rubric_criteria.map((r) => `<li>${r.criterion} (${r.points} pts): ${r.description}</li>`).join('')}</ul>
                  ` : ''}
                </div>
              ` : ''}
            </div>
          </div>
        `;
      });
    }

    documentSurface.innerHTML = html;

    // Attach Item-Level Regeneration Handlers
    documentSurface.querySelectorAll('.item-regen-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const itemType = btn.dataset.regenType;
        const itemId = btn.dataset.itemId;
        const guidance = prompt(`Enter specific instructions for regenerating this ${itemType} (or leave blank for standard refresh):`);
        if (guidance === null) return;

        btn.disabled = true;
        btn.textContent = 'Regenerating…';
        try {
          const res = await fetch(`${apiBase}/materials/${material.id}/regenerate-item`, {
            method: 'POST',
            headers: authHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ item_type: itemType, item_id: itemId, teacher_guidance: guidance || null }),
          });
          if (!res.ok) throw new Error(await apiError(res));
          const updated = await res.json();
          activeMaterial = updated;
          renderDocumentSurface(updated);
        } catch (err) {
          alert(`Regeneration failed: ${err.message}`);
          btn.disabled = false;
          btn.textContent = `🔄 Regenerate ${itemType}`;
        }
      });
    });

    // Attach Inline Title Edit Listener
    const editableTitle = documentSurface.querySelector('.doc-editable-title');
    editableTitle?.addEventListener('blur', async () => {
      const newTitle = editableTitle.textContent.trim();
      if (newTitle && newTitle !== material.title) {
        material.title = newTitle;
        await fetch(`${apiBase}/materials/${material.id}`, {
          method: 'PATCH',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ title: newTitle }),
        });
      }
    });
  }

  // Export handlers
  btnExportPdf?.addEventListener('click', () => {
    if (!activeMaterial) return;
    window.open(`${apiBase}/materials/${activeMaterial.id}/export?format=pdf&audience=${currentAudience}`, '_blank');
  });

  btnExportDocx?.addEventListener('click', () => {
    if (!activeMaterial) return;
    window.open(`${apiBase}/materials/${activeMaterial.id}/export?format=docx&audience=${currentAudience}`, '_blank');
  });

  // ── Materials Library Controller ────────────────────────────────────
  const libraryGrid = document.querySelector('#library-grid');
  const libraryFilters = document.querySelectorAll('.lib-filter-pill');
  let currentFilter = 'all';

  libraryFilters.forEach((pill) => {
    pill.addEventListener('click', () => {
      libraryFilters.forEach((p) => p.classList.remove('is-active'));
      pill.classList.add('is-active');
      currentFilter = pill.dataset.filter;
      loadLibraryMaterials();
    });
  });

  async function loadLibraryMaterials() {
    if (!libraryGrid) return;
    try {
      const url = currentFilter === 'all' ? '/materials' : `/materials?type=${currentFilter}`;
      const res = await fetch(`${apiBase}${url}`, { headers });
      if (!res.ok) throw new Error(await apiError(res));
      const materials = await res.json();

      if (!materials.length) {
        libraryGrid.innerHTML = '<p class="library-empty">No saved materials in this category. Generate a lesson, quiz, or assignment to get started!</p>';
        return;
      }

      libraryGrid.innerHTML = materials.map((m) => `
        <article class="library-card" data-id="${m.id}">
          <div class="library-card-header">
            <span class="library-type-badge badge-${m.type}">${m.type}</span>
            <span class="library-date">${displayDate(m.created_at)}</span>
          </div>
          <h3 class="library-card-title">${m.title}</h3>
          <p class="library-card-meta">${m.subject} • ${m.educational_level}</p>
          <div class="library-card-actions">
            <button class="btn-lib-action btn-open" data-open-id="${m.id}">Open in Workspace</button>
            <button class="btn-lib-action" data-export-id="${m.id}">PDF</button>
            <button class="btn-lib-action btn-del" data-del-id="${m.id}" title="Delete material">🗑</button>
          </div>
        </article>
      `).join('');

      // Attach Card Actions
      libraryGrid.querySelectorAll('[data-open-id]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const mId = btn.dataset.openId;
          const r = await fetch(`${apiBase}/materials/${mId}`, { headers });
          if (r.ok) {
            const fullMat = await r.json();
            switchView('generator');
            openContentWorkspace(fullMat);
          }
        });
      });

      libraryGrid.querySelectorAll('[data-export-id]').forEach((btn) => {
        btn.addEventListener('click', () => {
          window.open(`${apiBase}/materials/${btn.dataset.exportId}/export?format=pdf&audience=teacher`, '_blank');
        });
      });

      libraryGrid.querySelectorAll('[data-del-id]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Are you sure you want to delete this educational material?')) return;
          const delRes = await fetch(`${apiBase}/materials/${btn.dataset.delId}`, { method: 'DELETE', headers });
          if (delRes.ok) {
            loadLibraryMaterials();
            updateMaterialsBadge();
          }
        });
      });
    } catch (err) {
      libraryGrid.innerHTML = `<p class="library-empty">${err.message}</p>`;
    }
  }

  async function updateMaterialsBadge() {
    try {
      const res = await fetch(`${apiBase}/materials`, { headers });
      if (res.ok) {
        const list = await res.json();
        const badge = document.querySelector('#materials-count-badge');
        if (badge) badge.textContent = String(list.length);
      }
    } catch (e) { /* ignore */ }
  }

  // ── Preserved RAG Chat, Audio Transcription & PDF Uploads ──────────
  const thread = document.querySelector('.message-thread');
  const chatForm = document.querySelector('.message-form');
  const chatInput = document.querySelector('#message-input');
  const fileInput = document.querySelector('#pdf-input');
  const topUploadBtn = document.querySelector('.top-upload-btn');
  const attach = document.querySelector('.attach-button');
  const mic = document.querySelector('.mic-button');
  const send = document.querySelector('.send-button');
  const composer = document.querySelector('.composer');
  const dropzone = document.querySelector('.upload-dropzone');
  const status = document.querySelector('.upload-status');
  let conversationId = null;

  function setStatus(message = '', isError = false) {
    if (!status) return;
    status.textContent = message;
    status.classList.toggle('error', isError);
  }
  function scrollThread() { if (thread) thread.scrollTop = thread.scrollHeight; }
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
    thread?.querySelector('.thread-welcome')?.remove();
    const item = document.createElement('article');
    item.className = `message ${role}${typing ? ' typing' : ''}`;
    const avatar = document.createElement('span'); avatar.className = 'message-avatar'; avatar.textContent = role === 'user' ? 'You' : 'TD';
    const content = document.createElement('div'); content.className = 'message-content';
    const bubble = document.createElement('div'); bubble.className = 'message-bubble';
    if (role === 'assistant' && !typing) renderMarkdown(bubble, text); else bubble.textContent = text;
    const time = document.createElement('time'); time.className = 'message-time'; time.textContent = typing ? '' : timestamp();
    content.append(bubble, time); item.append(avatar, content); thread?.append(item); scrollThread();
    return item;
  }

  function resizeInput() { if (!chatInput) return; chatInput.style.height = 'auto'; chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`; }

  chatInput?.addEventListener('input', resizeInput);
  chatInput?.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); chatForm.requestSubmit(); } });

  topUploadBtn?.addEventListener('click', () => fileInput?.click());
  attach?.addEventListener('click', () => fileInput?.click());
  fileInput?.addEventListener('change', () => uploadFile(fileInput.files[0]));

  chatForm?.addEventListener('submit', async (event) => {
    event.preventDefault(); const query = chatInput.value.trim(); if (!query || send.disabled) return;
    setStatus(); addMessage('user', query); chatInput.value = ''; resizeInput(); send.disabled = true;
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
    finally { send.disabled = false; chatInput.focus(); }
  });

  async function uploadFile(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) return setStatus('Please select a PDF file.', true);
    if (file.size > 20 * 1024 * 1024) return setStatus('PDF must be 20 MB or smaller.', true);
    setStatus(`Uploading ${file.name}…`);
    try {
      const data = new FormData(); data.append('file', file);
      const response = await fetch(`${apiBase}/upload`, { method: 'POST', headers: authHeaders(), body: data });
      if (!response.ok) throw new Error(await apiError(response));
      setStatus(`${file.name} uploaded and indexed successfully.`);
      window.dispatchEvent(new CustomEvent('tutordesk:document-uploaded'));
    } catch (error) { setStatus(error.message || 'Upload failed. Please try again.', true); }
    finally { if (fileInput) fileInput.value = ''; }
  }

  // Voice recording preservation
  let recorder = null;
  let audioStream = null;
  let recordTimer = null;
  let recordSeconds = 0;
  const AUDIO_MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4', 'audio/aac'];

  function pickAudioMimeType() {
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return '';
    return AUDIO_MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || '';
  }
  function stopAudioStream() { audioStream?.getTracks().forEach((track) => track.stop()); audioStream = null; }
  function endRecording() {
    if (recordTimer) { clearInterval(recordTimer); recordTimer = null; }
    mic?.classList.remove('is-recording');
    mic?.setAttribute('aria-label', 'Record voice message');
    stopAudioStream();
  }
  async function startRecording() {
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) return setStatus('Voice recording is not supported in this browser.', true);
    try { audioStream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { return setStatus('Microphone access was denied.', true); }
    const mimeType = pickAudioMimeType();
    let activeRecorder;
    try { activeRecorder = new MediaRecorder(audioStream, mimeType ? { mimeType } : undefined); }
    catch { stopAudioStream(); return setStatus('Could not start recording.', true); }
    const chunks = [];
    activeRecorder.addEventListener('dataavailable', (event) => { if (event.data.size) chunks.push(event.data); });
    activeRecorder.addEventListener('stop', () => uploadRecording(new Blob(chunks, { type: activeRecorder.mimeType || mimeType || 'audio/webm' })));
    activeRecorder.start();
    recorder = activeRecorder;
    mic?.classList.add('is-recording');
    recordSeconds = 0;
    recordTimer = setInterval(() => { recordSeconds += 1; setStatus(`Recording ${recordSeconds}s…`); if (recordSeconds >= 120) stopRecording(); }, 1000);
  }
  function stopRecording() { if (!recorder || recorder.state === 'inactive') return; recorder.stop(); recorder = null; setStatus('Transcribing…'); endRecording(); }
  async function uploadRecording(blob) {
    if (mic) mic.disabled = true;
    try {
      const data = new FormData(); data.append('file', blob, 'recording');
      const response = await fetch(`${apiBase}/transcribe`, { method: 'POST', headers: authHeaders(), body: data });
      if (!response.ok) throw new Error(await apiError(response));
      const body = await response.json();
      const text = (body.text || '').trim();
      if (!text) throw new Error('No speech detected.');
      if (chatInput) { chatInput.value = chatInput.value.trim() ? `${chatInput.value.trim()} ${text}` : text; resizeInput(); chatInput.focus(); }
      setStatus('Transcribed — send when ready.');
    } catch (error) { setStatus(error.message || 'Transcription failed.', true); }
    finally { if (mic) mic.disabled = false; }
  }
  mic?.addEventListener('click', () => { if (recorder) stopRecording(); else startRecording(); });

  if (composer) {
    ['dragenter', 'dragover'].forEach((name) => composer.addEventListener(name, (e) => { e.preventDefault(); composer.classList.add('drag-over'); if (dropzone) dropzone.hidden = false; }));
    ['dragleave', 'drop'].forEach((name) => composer.addEventListener(name, (e) => { e.preventDefault(); composer.classList.remove('drag-over'); if (dropzone) dropzone.hidden = true; }));
    composer.addEventListener('drop', (e) => uploadFile(e.dataTransfer.files[0]));
  }

  // ── Document List (Uploaded PDFs in Sidebar) ────────────────────────
  const docList = document.querySelector('.document-list');
  const docCount = document.querySelector('.documents-count');

  function displayDate(value) {
    if (!value) return 'Recently';
    try {
      const d = new Date(value);
      if (isNaN(d.getTime())) return 'Recently';
      return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(d);
    } catch { return 'Recently'; }
  }

  function renderDocuments(documents) {
    if (!docList) return;
    docList.replaceChildren();
    if (docCount) docCount.textContent = String(documents.length);
    if (!documents.length) {
      docList.innerHTML = '<p class="documents-empty">No PDFs uploaded yet.</p>';
      return;
    }
    documents.forEach((doc) => {
      const item = document.createElement('div');
      item.className = 'document-item';
      item.innerHTML = `
        <span class="document-icon" aria-hidden="true">📄</span>
        <div class="document-info">
          <span class="document-title"></span>
          <span class="document-date">${doc.created_at ? displayDate(doc.created_at) : 'Uploaded'}</span>
        </div>
        <button class="document-delete" type="button" title="Delete PDF" aria-label="Delete">✕</button>
      `;
      item.querySelector('.document-title').textContent = doc.filename;
      item.querySelector('.document-delete').addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete "${doc.filename}"? This will also remove its indexed material.`)) return;
        await deleteDocument(doc.id, doc.filename);
      });
      docList.append(item);
    });
  }

  async function deleteDocument(id, filename) {
    try {
      const response = await fetch(`${apiBase}/uploads/${id}`, { method: 'DELETE', headers });
      if (!response.ok) throw new Error('Could not delete document.');
      await refreshDocuments();
      setStatus(`Deleted "${filename}".`);
    } catch (err) { alert(err.message || 'Failed to delete PDF'); }
  }

  async function refreshDocuments() {
    try {
      const res = await fetch(`${apiBase}/uploads`, { headers });
      if (!res.ok) throw new Error('Failed to load uploads');
      const docs = await res.json();
      renderDocuments(Array.isArray(docs) ? docs : []);
    } catch (error) {
      if (docList) docList.innerHTML = `<p class="documents-empty">${error.message}</p>`;
    }
  }

  window.addEventListener('tutordesk:document-uploaded', () => refreshDocuments());

  // Sources Sidebar Display
  const sourceList = document.querySelector('.sources-list');
  window.addEventListener('tutordesk:sources', (event) => {
    if (!sourceList) return;
    sourceList.replaceChildren();
    const sources = event.detail || [];
    if (!sources.length) {
      sourceList.innerHTML = '<p class="sources-empty">No sources were cited for this item.</p>';
      return;
    }
    sources.forEach((source) => {
      const card = document.createElement('article');
      card.className = 'source-card';
      const link = typeof source === 'string' ? source : source.url || source.title;
      card.innerHTML = `<span class="source-icon">◎</span><div><strong></strong><a target="_blank" rel="noopener noreferrer"></a></div>`;
      card.querySelector('strong').textContent = link;
      const anchor = card.querySelector('a');
      if (link.startsWith('http')) {
        anchor.href = link;
        try { anchor.textContent = new URL(link).hostname; } catch { anchor.textContent = 'External Web Source'; }
      } else {
        anchor.textContent = 'User Document';
      }
      sourceList.append(card);
    });
  });

  // Sidebar toggle controllers
  const sidebar = document.querySelector('.conversation-sidebar');
  const sourcesSidebar = document.querySelector('.sources-sidebar');
  const scrim = document.querySelector('.sidebar-scrim');
  const closeSidebar = () => { sidebar?.classList.remove('is-open'); scrim?.classList.remove('is-visible'); };
  document.querySelector('.menu-button')?.addEventListener('click', () => { sidebar?.classList.add('is-open'); scrim?.classList.add('is-visible'); });
  document.querySelector('.close-sidebar')?.addEventListener('click', closeSidebar);
  scrim?.addEventListener('click', closeSidebar);
  document.querySelector('.sources-toggle')?.addEventListener('click', () => sourcesSidebar?.classList.toggle('is-open'));
  document.querySelector('.close-sources-btn')?.addEventListener('click', () => sourcesSidebar?.classList.remove('is-open'));
  document.querySelector('[data-logout]')?.addEventListener('click', () => { localStorage.removeItem('tutordesk_token'); window.location.assign('/'); });

  // Initial Data Fetch
  fetch(`${apiBase}/me`, { headers }).then((res) => res.ok ? res.json() : null).then((user) => {
    if (user && document.querySelector('.user-email')) document.querySelector('.user-email').textContent = user.email;
  });

  refreshDocuments();
  updateMaterialsBadge();
})();

// ── Theme Switcher ───────────────────────────────────────────────────
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
