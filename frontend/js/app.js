(() => {
  const form = document.querySelector('[data-auth-form]');
  if (!form) return;

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
