import React, { useState, useEffect } from 'react';

type AuthMode = 'login' | 'register' | 'forgot_password' | 'reset_password' | 'verify_email' | 'resend_verification';

interface AuthPagesProps {
  mode: AuthMode;
  onNavigate: (page: string) => void;
  onAuthSuccess?: (token: string, user: Record<string, unknown>) => void;
}

const API = '';

function Logo() {
  return (
    <div style={{ textAlign: 'center', marginBottom: 32 }}>
      <div style={{ fontSize: 28, fontWeight: 900, color: '#fff', letterSpacing: '-0.5px' }}>
        PYPY <span style={{ color: '#6366f1' }}>Grid</span>
      </div>
      <div style={{ fontSize: 10, color: '#8b5cf6', letterSpacing: '2px', textTransform: 'uppercase', marginTop: 2 }}>
        Protect Your Power, Protect Yourself
      </div>
    </div>
  );
}

function Alert({ type, msg }: { type: 'error' | 'success' | 'info'; msg: string }) {
  const colors = { error: '#ef4444', success: '#10b981', info: '#6366f1' };
  const bgs = { error: 'rgba(239,68,68,0.1)', success: 'rgba(16,185,129,0.1)', info: 'rgba(99,102,241,0.1)' };
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 8, marginBottom: 16,
      background: bgs[type], border: `1px solid ${colors[type]}33`,
      color: colors[type], fontSize: 14, lineHeight: 1.5,
    }}>
      {msg}
    </div>
  );
}

function Input({
  label, type = 'text', value, onChange, placeholder, required = false, autoComplete,
}: {
  label: string; type?: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; autoComplete?: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 6 }}>
        {label}{required && <span style={{ color: '#ef4444' }}> *</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        autoComplete={autoComplete}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: '100%', padding: '12px 16px', borderRadius: 10, fontSize: 15,
          background: '#1e293b', color: '#f8fafc', outline: 'none', boxSizing: 'border-box',
          border: `1px solid ${focused ? '#6366f1' : '#334155'}`,
          boxShadow: focused ? '0 0 0 3px rgba(99,102,241,0.15)' : 'none',
          transition: 'all 0.2s',
        }}
      />
    </div>
  );
}

function SubmitButton({ label, loading }: { label: string; loading: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading}
      style={{
        width: '100%', padding: '13px', borderRadius: 10, fontSize: 15, fontWeight: 700, cursor: loading ? 'wait' : 'pointer',
        background: loading ? '#374151' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        color: '#fff', border: 'none', boxShadow: loading ? 'none' : '0 0 24px rgba(99,102,241,0.4)',
        transition: 'all 0.2s', marginTop: 8,
      }}
    >
      {loading ? '⏳ Please wait...' : label}
    </button>
  );
}

const card: React.CSSProperties = {
  background: 'rgba(17,24,39,0.9)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(99,102,241,0.2)',
  borderRadius: 20,
  padding: '40px 36px',
  width: '100%',
  maxWidth: 440,
  boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
};

const page: React.CSSProperties = {
  minHeight: '100vh',
  background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99,102,241,0.12) 0%, #0a0e1a 60%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '40px 20px',
  fontFamily: "'Inter', system-ui, sans-serif",
};

// ─── Login Form ───────────────────────────────────────────────────────────────

function LoginForm({ onNavigate, onAuthSuccess }: { onNavigate: (p: string) => void; onAuthSuccess?: AuthPagesProps['onAuthSuccess'] }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      if (onAuthSuccess) onAuthSuccess(data.access_token, data.user || {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={page}>
      <div style={card}>
        <Logo />
        <h1 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Welcome back</h1>
        <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Sign in to your PYPY Grid account</p>
        {error && <Alert type="error" msg={error} />}
        <form onSubmit={handleSubmit}>
          <Input label="Email address" type="email" value={email} onChange={setEmail} placeholder="researcher@university.edu" required autoComplete="email" />
          <Input label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" required autoComplete="current-password" />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, color: '#94a3b8', cursor: 'pointer' }}>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember me
            </label>
            <button type="button" style={{ fontSize: 13, color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => onNavigate('forgot_password')}>
              Forgot password?
            </button>
          </div>
          <SubmitButton label="Sign In" loading={loading} />
        </form>
        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: '#64748b' }}>
          Don't have an account?{' '}
          <button style={{ color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }} onClick={() => onNavigate('register')}>
            Create account
          </button>
        </p>
        <div style={{ marginTop: 24, padding: '12px 16px', background: 'rgba(99,102,241,0.06)', borderRadius: 8, border: '1px solid rgba(99,102,241,0.15)', textAlign: 'center' }}>
          <p style={{ fontSize: 12, color: '#475569', margin: 0 }}>
            🔒 Protected by PYPY Grid security. JWT-secured with brute-force detection.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Register Form ────────────────────────────────────────────────────────────

function RegisterForm({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirm: '', institution: '', plan: 'free', agreedToTos: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const set = (k: keyof typeof form) => (v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) { setError('Passwords do not match.'); return; }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (!form.agreedToTos) { setError('Please accept the Terms of Service.'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          first_name: form.firstName,
          last_name: form.lastName,
          organization_name: form.institution || `${form.firstName}'s Lab`,
          plan_tier: form.plan,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Registration failed');
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  if (success) return (
    <div style={page}>
      <div style={{ ...card, textAlign: 'center' }}>
        <Logo />
        <div style={{ fontSize: 48, marginBottom: 16 }}>📧</div>
        <h2 style={{ color: '#fff', marginBottom: 12 }}>Check your inbox!</h2>
        <p style={{ color: '#64748b', fontSize: 14, lineHeight: 1.7 }}>
          We've sent a verification link to <strong style={{ color: '#818cf8' }}>{form.email}</strong>.<br />
          Please verify your email before logging in.
        </p>
        <button style={{ marginTop: 24, padding: '11px 24px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('login')}>
          Back to Sign In
        </button>
      </div>
    </div>
  );

  return (
    <div style={{ ...page, alignItems: 'flex-start', paddingTop: 60 }}>
      <div style={{ ...card, maxWidth: 480 }}>
        <Logo />
        <h1 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Create your account</h1>
        <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Start your free PYPY Grid account — no credit card required.</p>
        {error && <Alert type="error" msg={error} />}
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <Input label="First Name" value={form.firstName} onChange={set('firstName')} placeholder="Aminah" required />
            </div>
            <div>
              <Input label="Last Name" value={form.lastName} onChange={set('lastName')} placeholder="Binti Ahmad" required />
            </div>
          </div>
          <Input label="Institution Email" type="email" value={form.email} onChange={set('email')} placeholder="researcher@utm.my" required autoComplete="email" />
          <Input label="Password" type="password" value={form.password} onChange={set('password')} placeholder="Min. 8 characters" required autoComplete="new-password" />
          <Input label="Confirm Password" type="password" value={form.confirm} onChange={set('confirm')} placeholder="Re-enter password" required autoComplete="new-password" />
          <Input label="Institution / Organization" value={form.institution} onChange={set('institution')} placeholder="Universiti Teknologi Malaysia" />
          <div style={{ marginBottom: 18 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 6, display: 'block' }}>Starting Plan</label>
            <select
              value={form.plan}
              onChange={(e) => set('plan')(e.target.value)}
              style={{ width: '100%', padding: '12px 16px', borderRadius: 10, background: '#1e293b', color: '#f8fafc', border: '1px solid #334155', fontSize: 14, outline: 'none', boxSizing: 'border-box' }}
            >
              <option value="free">Free — RM 0/month (Forever)</option>
              <option value="academic_premium">Academic Premium — RM 19/month</option>
            </select>
          </div>
          <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, color: '#64748b', cursor: 'pointer', marginBottom: 20 }}>
            <input type="checkbox" checked={form.agreedToTos} onChange={(e) => set('agreedToTos')(e.target.checked)} style={{ marginTop: 2 }} />
            <span>I agree to the{' '}
              <a href="/legal/terms" style={{ color: '#6366f1' }}>Terms of Service</a>,{' '}
              <a href="/legal/privacy" style={{ color: '#6366f1' }}>Privacy Policy</a>, and{' '}
              <a href="/legal/aup" style={{ color: '#6366f1' }}>Acceptable Use Policy</a>.
            </span>
          </label>
          <SubmitButton label="Create Account" loading={loading} />
        </form>
        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: '#64748b' }}>
          Already have an account?{' '}
          <button style={{ color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }} onClick={() => onNavigate('login')}>
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}

// ─── Forgot Password Form ─────────────────────────────────────────────────────

function ForgotPasswordForm({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={page}>
      <div style={card}>
        <Logo />
        {sent ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📬</div>
            <h2 style={{ color: '#fff', marginBottom: 12 }}>Reset email sent</h2>
            <p style={{ color: '#64748b', fontSize: 14, lineHeight: 1.7 }}>
              If <strong style={{ color: '#818cf8' }}>{email}</strong> is registered, you'll receive a reset link in the next few minutes.
            </p>
            <button style={{ marginTop: 24, padding: '11px 24px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('login')}>
              Back to Sign In
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Forgot your password?</h1>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Enter your email and we'll send you a reset link.</p>
            {error && <Alert type="error" msg={error} />}
            <form onSubmit={handleSubmit}>
              <Input label="Email address" type="email" value={email} onChange={setEmail} placeholder="your@email.com" required autoComplete="email" />
              <SubmitButton label="Send Reset Link" loading={loading} />
            </form>
            <p style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: '#64748b' }}>
              <button style={{ color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => onNavigate('login')}>← Back to Sign In</button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Reset Password Form ──────────────────────────────────────────────────────

function ResetPasswordForm({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const token = new URLSearchParams(window.location.search).get('token') || '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (!token) { setError('Invalid reset link. Please request a new one.'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={page}>
      <div style={card}>
        <Logo />
        {success ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <h2 style={{ color: '#fff', marginBottom: 12 }}>Password reset!</h2>
            <p style={{ color: '#64748b', fontSize: 14 }}>Your password has been changed successfully.</p>
            <button style={{ marginTop: 24, padding: '13px 32px', borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 15 }} onClick={() => onNavigate('login')}>
              Sign In Now
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Set new password</h1>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Choose a strong password for your PYPY Grid account.</p>
            {error && <Alert type="error" msg={error} />}
            {!token && <Alert type="error" msg="Reset token missing. Please use the link from your email." />}
            <form onSubmit={handleSubmit}>
              <Input label="New Password" type="password" value={password} onChange={setPassword} placeholder="Min. 8 characters" required autoComplete="new-password" />
              <Input label="Confirm New Password" type="password" value={confirm} onChange={setConfirm} placeholder="Re-enter password" required autoComplete="new-password" />
              <SubmitButton label="Reset Password" loading={loading} />
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Verify Email Page ────────────────────────────────────────────────────────

function VerifyEmailPage({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [status, setStatus] = useState<'pending' | 'verifying' | 'success' | 'error'>('pending');
  const [error, setError] = useState('');

  const token = new URLSearchParams(window.location.search).get('token') || '';

  useEffect(() => {
    if (token) {
      setStatus('verifying');
      fetch(`${API}/api/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      }).then(async (res) => {
        if (res.ok) { setStatus('success'); }
        else { const d = await res.json(); setError(d.detail || 'Verification failed.'); setStatus('error'); }
      }).catch(() => { setError('Network error. Please try again.'); setStatus('error'); });
    }
  }, [token]);

  return (
    <div style={page}>
      <div style={{ ...card, textAlign: 'center' }}>
        <Logo />
        {status === 'verifying' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⏳</div>
            <h2 style={{ color: '#fff' }}>Verifying your email...</h2>
          </>
        )}
        {status === 'pending' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📧</div>
            <h2 style={{ color: '#fff', marginBottom: 12 }}>Check your inbox</h2>
            <p style={{ color: '#64748b', fontSize: 14, lineHeight: 1.7 }}>
              We sent a verification link to your email address.<br />Click the link to activate your account.
            </p>
            <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <button style={{ padding: '11px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('resend_verification')}>
                Resend verification email
              </button>
              <button style={{ padding: '11px', borderRadius: 8, background: 'transparent', border: '1px solid #1e293b', color: '#64748b', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('login')}>
                Back to Sign In
              </button>
            </div>
          </>
        )}
        {status === 'success' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
            <h2 style={{ color: '#fff', marginBottom: 12 }}>Email verified!</h2>
            <p style={{ color: '#64748b', fontSize: 14, marginBottom: 24 }}>Your account is now active. Welcome to PYPY Grid!</p>
            <button style={{ padding: '13px 32px', borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 15 }} onClick={() => onNavigate('login')}>
              Sign In to Dashboard
            </button>
          </>
        )}
        {status === 'error' && (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>❌</div>
            <h2 style={{ color: '#ef4444', marginBottom: 12 }}>Verification failed</h2>
            <p style={{ color: '#64748b', fontSize: 14, marginBottom: 16 }}>{error}</p>
            <button style={{ padding: '11px 24px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('resend_verification')}>
              Request new verification link
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Resend Verification Form ─────────────────────────────────────────────────

function ResendVerificationForm({ onNavigate }: { onNavigate: (p: string) => void }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/api/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to resend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={page}>
      <div style={card}>
        <Logo />
        {sent ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📬</div>
            <h2 style={{ color: '#fff', marginBottom: 12 }}>Verification email sent!</h2>
            <p style={{ color: '#64748b', fontSize: 14 }}>Please check your inbox and spam folder.</p>
            <button style={{ marginTop: 24, padding: '11px 24px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', cursor: 'pointer', fontSize: 14 }} onClick={() => onNavigate('login')}>
              Back to Sign In
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Resend verification</h1>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Enter your email to receive a new verification link.</p>
            {error && <Alert type="error" msg={error} />}
            <form onSubmit={handleSubmit}>
              <Input label="Email address" type="email" value={email} onChange={setEmail} placeholder="your@email.com" required autoComplete="email" />
              <SubmitButton label="Resend Verification Email" loading={loading} />
            </form>
            <p style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: '#64748b' }}>
              <button style={{ color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => onNavigate('login')}>← Back to Sign In</button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main Export ──────────────────────────────────────────────────────────────

export default function AuthPages({ mode, onNavigate, onAuthSuccess }: AuthPagesProps) {
  switch (mode) {
    case 'login': return <LoginForm onNavigate={onNavigate} onAuthSuccess={onAuthSuccess} />;
    case 'register': return <RegisterForm onNavigate={onNavigate} />;
    case 'forgot_password': return <ForgotPasswordForm onNavigate={onNavigate} />;
    case 'reset_password': return <ResetPasswordForm onNavigate={onNavigate} />;
    case 'verify_email': return <VerifyEmailPage onNavigate={onNavigate} />;
    case 'resend_verification': return <ResendVerificationForm onNavigate={onNavigate} />;
    default: return <LoginForm onNavigate={onNavigate} onAuthSuccess={onAuthSuccess} />;
  }
}
