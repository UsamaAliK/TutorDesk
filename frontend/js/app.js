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
    const responseText = await response.text().catch(() => '');
    let body = {};
    try { body = responseText ? JSON.parse(responseText) : {}; } catch { /* non-JSON server response */ }
    if (response.status === 401) {
      localStorage.removeItem('tutordesk_token');
      window.location.assign('/');
    }
    const detail = body.detail || body.message || responseText.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 300);
    return detail ? `${detail} (HTTP ${response.status})` : `Request failed (HTTP ${response.status}). Please try again.`;
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
    }
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
  const researchNote = document.querySelector('#research-note');
  const levelSelect = document.querySelector('#form-level');
  const sourceDocumentSelect = document.querySelector('#form-document-source');
  const sourcePdfInput = document.querySelector('#source-pdf-input');
  const uploadSourcePdfButton = document.querySelector('#upload-source-pdf');
  const sourceUploadStatus = document.querySelector('#source-upload-status');

  let activeGenerationType = 'lesson';
  let modalReturnFocus = null;

  function openGeneratorForm(type) {
    modalReturnFocus = document.activeElement;
    activeGenerationType = type;
    modal.hidden = false;
    sourceDocumentSelect.value = '';
    if (sourceUploadStatus) sourceUploadStatus.textContent = '';
    loadSourceDocuments();
    document.querySelector('#form-subject')?.focus();

    fieldsLesson.hidden = type !== 'lesson';
    fieldsQuiz.hidden = type !== 'quiz';
    fieldsAssignment.hidden = type !== 'assignment';
    if (researchNote) researchNote.hidden = levelSelect.value !== 'PhD / Research Mode';

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
    modalReturnFocus?.focus?.();
  }

  document.querySelectorAll('[data-open-form]').forEach((card) => {
    card.addEventListener('click', () => openGeneratorForm(card.dataset.openForm));
  });

  closeModalBtn?.addEventListener('click', closeGeneratorModal);
  cancelFormBtn?.addEventListener('click', closeGeneratorModal);
  levelSelect?.addEventListener('change', () => {
    if (researchNote) researchNote.hidden = levelSelect.value !== 'PhD / Research Mode';
  });
  modal?.addEventListener('click', (event) => {
    if (event.target === modal) closeGeneratorModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal && !modal.hidden) closeGeneratorModal();
  });

  // Duration Pills
  const durationPills = document.querySelectorAll('.duration-pill');
  const hiddenDuration = document.querySelector('#form-lesson-duration');
  durationPills.forEach((pill) => {
    pill.setAttribute('aria-pressed', String(pill.classList.contains('is-active')));
    pill.addEventListener('click', () => {
      durationPills.forEach((p) => p.classList.remove('is-active'));
      pill.classList.add('is-active');
      durationPills.forEach((p) => p.setAttribute('aria-pressed', String(p === pill)));
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
    const short = parseInt(quizShort.value, 10) || 0;
    const long = parseInt(quizLong.value, 10) || 0;
    const currentSum = short + long;

    const mcqCount = parseInt(quizMCQs.value, 10) || 0;
    if (currentSum === total && (total > 0 || mcqCount > 0)) {
      distStatus.textContent = `Written: ${total} / ${total} Balanced`;
      distStatus.classList.remove('error');
      distHint.textContent = '✓ Written question counts match. MCQs are counted separately.';
      submitGenBtn.disabled = false;
      return true;
    } else {
      const diff = total - currentSum;
      distStatus.textContent = `Written: ${currentSum} / ${total}`;
      distStatus.classList.add('error');
      distHint.textContent = diff > 0
        ? `⚠️ Please allocate ${diff} more written question${diff > 1 ? 's' : ''}.`
        : `⚠️ Written question count exceeds total by ${Math.abs(diff)}.`;
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
    const selected_document_id = Number(sourceDocumentSelect.value) || null;
    const additional_instructions = instructionsBox.value.trim() || null;

    if (['material_only', 'combined'].includes(source_mode) && !selected_document_id) {
      submitGenBtn.disabled = false;
      btnText.textContent = 'Generate Content';
      if (sourceUploadStatus) sourceUploadStatus.textContent = 'Choose or upload a PDF for the selected research source.';
      sourceDocumentSelect.focus();
      return;
    }

    let endpoint = '';
    let payload = { subject, topic, educational_level, source_mode, selected_document_id, additional_instructions };

    if (activeGenerationType === 'lesson') {
      endpoint = '/materials/lessons/generate';
      payload.duration_minutes = parseInt(hiddenDuration.value, 10) || 45;
      payload.teaching_style = document.querySelector('#form-lesson-style').value.trim() || null;
      payload.learning_objectives = document.querySelector('#form-lesson-objectives').value.trim() || null;
    } else if (activeGenerationType === 'quiz') {
      endpoint = '/materials/quizzes/generate';
      payload.difficulty = document.querySelector('#form-quiz-difficulty').value;
      payload.total_written_questions = parseInt(quizTotal.value, 10);
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
      payload.num_mcqs = parseInt(document.querySelector('#form-assignment-mcqs').value, 10) || 0;
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
      const allQuestions = content.questions || [];
      const mcqs = content.mcq_section?.mcqs?.length
        ? content.mcq_section.mcqs
        : allQuestions.filter((q) => q.type === 'mcq' || q.options?.length);
      const writtenQuestions = content.questions_section?.questions?.length
        ? content.questions_section.questions
        : allQuestions.filter((q) => q.type !== 'mcq' && !q.options?.length);

      const renderQuizQuestions = (questions, label, regenType) => questions.forEach((q, idx) => {
        const isMcq = (q.type === 'mcq' || q.options?.length) && q.options?.length;
        html += `
          <div class="doc-section-card" data-q-id="${q.id || idx + 1}">
            <div class="doc-section-header">
              <h3 class="doc-section-title">${label} ${idx + 1} (${q.marks || 1} pt)</h3>
              <button class="item-regen-btn" type="button" data-regen-type="${regenType}" data-item-id="${q.id || idx + 1}">🔄 Regenerate ${label}</button>
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

      if (mcqs.length) {
        html += '<h3 class="doc-section-title">Section A: Multiple Choice Questions</h3>';
        renderQuizQuestions(mcqs, 'MCQ', 'mcq');
      }
      if (writtenQuestions.length) {
        html += '<h3 class="doc-section-title">Section B: Written Questions</h3>';
        renderQuizQuestions(writtenQuestions, 'Question', 'question');
      }
    } else if (mtype === 'assignment') {
      html += `
        <div class="doc-section-card">
          <p class="doc-section-body">${content.instructions_for_students || 'Complete the following tasks.'}</p>
        </div>
      `;
      const assignmentMcqs = content.mcq_section?.mcqs || [];
      if (assignmentMcqs.length) {
        html += '<h3 class="doc-section-title">Section A: Multiple Choice Questions</h3>';
        assignmentMcqs.forEach((q, idx) => {
          html += `
            <div class="doc-section-card" data-q-id="${q.id || idx + 1}">
              <div class="doc-section-header">
                <h3 class="doc-section-title">MCQ ${idx + 1} (${q.marks || 1} pt)</h3>
                <button class="item-regen-btn" type="button" data-regen-type="mcq" data-item-id="${q.id || idx + 1}">🔄 Regenerate MCQ</button>
              </div>
              <div class="doc-section-body">
                <p contenteditable="true">${q.prompt || ''}</p>
                <ul class="quiz-options-list">
                  ${(q.options || []).map((opt) => {
                    const isCorrect = isTeacher && (opt === q.correct_answer || opt.startsWith(q.correct_answer?.slice(0, 2)));
                    return `<li class="quiz-opt-item ${isCorrect ? 'is-correct' : ''}">${opt}</li>`;
                  }).join('')}
                </ul>
                ${isTeacher ? `<div class="doc-teacher-box"><strong>Teacher Answer Key:</strong> ${q.correct_answer || 'See criteria'}${q.explanation ? `<br><strong>Explanation:</strong> ${q.explanation}` : ''}</div>` : ''}
              </div>
            </div>
          `;
        });
      }
      html += '<h3 class="doc-section-title">Section B: Tasks / Problems</h3>';
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
  async function downloadMaterial(materialId, format, audience = 'teacher') {
    try {
      const response = await fetch(`${apiBase}/materials/${materialId}/export?format=${encodeURIComponent(format)}&audience=${encodeURIComponent(audience)}`, {
        headers: authHeaders({ Accept: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      const file = await response.blob();
      if (!file.size) throw new Error('The server returned an empty file. Please try exporting again.');
      const extension = format === 'pdf' ? 'pdf' : 'docx';
      const disposition = response.headers.get('Content-Disposition') || '';
      const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `tutordesk-material.${extension}`;
      const url = URL.createObjectURL(file);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      alert(`Download failed: ${error.message}`);
    }
  }

  btnExportPdf?.addEventListener('click', () => {
    if (activeMaterial) downloadMaterial(activeMaterial.id, 'pdf', currentAudience);
  });

  btnExportDocx?.addEventListener('click', () => {
    if (activeMaterial) downloadMaterial(activeMaterial.id, 'docx', currentAudience);
  });

  // ── Materials Library Controller ────────────────────────────────────
  const libraryGrid = document.querySelector('#library-grid');
  const libraryFilters = document.querySelectorAll('.lib-filter-pill');
  let currentFilter = 'all';

  function displayDate(value) {
    if (!value) return 'Date unavailable';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Date unavailable';
    return new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
  }

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
        btn.addEventListener('click', () => downloadMaterial(btn.dataset.exportId, 'pdf', 'teacher'));
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
        renderRecentMaterials(list);
      }
    } catch (e) { /* ignore */ }
  }

  function renderRecentMaterials(materials) {
    const recentList = document.querySelector('#recent-materials-list');
    if (!recentList) return;
    const recent = materials.slice(0, 3);
    if (!recent.length) {
      recentList.innerHTML = '<p class="recent-empty">Your saved lessons, quizzes, and assignments will appear here.</p>';
      return;
    }
    recentList.replaceChildren(...recent.map((material) => {
      const card = document.createElement('article');
      card.className = 'recent-material';
      const type = document.createElement('span');
      type.className = `library-type-badge badge-${material.type}`;
      type.textContent = material.type;
      const title = document.createElement('h3');
      title.textContent = material.title || 'Untitled material';
      const meta = document.createElement('p');
      meta.textContent = `${material.subject || 'Untitled subject'} · ${material.educational_level || ''}`;
      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'recent-open';
      open.textContent = 'Open material →';
      open.addEventListener('click', async () => {
        try {
          const response = await fetch(`${apiBase}/materials/${material.id}`, { headers });
          if (!response.ok) throw new Error(await apiError(response));
          openContentWorkspace(await response.json());
        } catch (error) {
          alert(`Unable to open material: ${error.message}`);
        }
      });
      card.append(type, title, meta, open);
      return card;
    }));
  }

  // ── Material-specific PDF selection and upload ─────────────────────
  async function loadSourceDocuments(selectedId = '') {
    if (!sourceDocumentSelect) return;
    try {
      const response = await fetch(`${apiBase}/uploads`, { headers });
      if (!response.ok) throw new Error(await apiError(response));
      const documents = await response.json();
      sourceDocumentSelect.replaceChildren(new Option('No PDF selected', ''));
      documents.forEach((document) => sourceDocumentSelect.add(new Option(document.filename, String(document.id))));
      if (selectedId) sourceDocumentSelect.value = String(selectedId);
    } catch (error) {
      if (sourceUploadStatus) sourceUploadStatus.textContent = error.message || 'Could not load your PDFs.';
    }
  }

  uploadSourcePdfButton?.addEventListener('click', () => sourcePdfInput?.click());
  sourceDocumentSelect?.addEventListener('change', () => {
    const sourceMode = document.querySelector('#form-source-mode');
    if (sourceDocumentSelect.value && sourceMode.value === 'web_search') sourceMode.value = 'material_only';
    if (sourceUploadStatus) sourceUploadStatus.textContent = '';
  });
  sourcePdfInput?.addEventListener('change', async () => {
    const file = sourcePdfInput.files[0];
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      sourceUploadStatus.textContent = 'Choose a PDF file.';
      sourcePdfInput.value = '';
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      sourceUploadStatus.textContent = 'PDFs must be 20 MB or smaller.';
      sourcePdfInput.value = '';
      return;
    }
    sourceUploadStatus.textContent = `Uploading ${file.name}…`;
    uploadSourcePdfButton.disabled = true;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${apiBase}/upload`, { method: 'POST', headers: authHeaders(), body: formData });
      if (!response.ok) throw new Error(await apiError(response));
      const uploaded = await response.json();
      await loadSourceDocuments(uploaded.id);
      document.querySelector('#form-source-mode').value = 'material_only';
      sourceUploadStatus.textContent = `${file.name} is ready for this material.`;
    } catch (error) {
      sourceUploadStatus.textContent = error.message || 'Upload failed. Please try again.';
    } finally {
      sourcePdfInput.value = '';
      uploadSourcePdfButton.disabled = false;
    }
  });

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

  // Sources drawer and account controls
  const sourcesSidebar = document.querySelector('.sources-sidebar');
  const sourcesScrim = document.querySelector('.sources-scrim');
  const sourcesToggle = document.querySelector('.sources-toggle');
  function setSourcesOpen(isOpen) {
    sourcesSidebar?.classList.toggle('is-open', isOpen);
    sourcesScrim?.classList.toggle('is-visible', isOpen);
    sourcesToggle?.setAttribute('aria-expanded', String(isOpen));
  }
  sourcesToggle?.addEventListener('click', () => setSourcesOpen(!sourcesSidebar?.classList.contains('is-open')));
  sourcesScrim?.addEventListener('click', () => setSourcesOpen(false));
  document.querySelector('.close-sources-btn')?.addEventListener('click', () => setSourcesOpen(false));
  document.querySelector('[data-logout]')?.addEventListener('click', () => { localStorage.removeItem('tutordesk_token'); window.location.assign('/'); });

  // Initial Data Fetch
  fetch(`${apiBase}/me`, { headers }).then((res) => res.ok ? res.json() : null).then((user) => {
    if (user && document.querySelector('.user-email')) document.querySelector('.user-email').textContent = user.email;
  });

  loadSourceDocuments();
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
