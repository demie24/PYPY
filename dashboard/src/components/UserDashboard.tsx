import React, { useState, useEffect } from 'react';

interface UserDashboardProps {
  token: string;
  user: {
    id?: string;
    email?: string;
    first_name?: string;
    last_name?: string;
    role?: string;
  };
  onLogout: () => void;
  onNavigate: (page: string) => void;
}

type Tab = 'overview' | 'workspace' | 'subscription' | 'usage' | 'experiments' | 'notifications' | 'settings';

const API = '';

const s: Record<string, React.CSSProperties> = {
  layout: { display: 'flex', minHeight: '100vh', background: '#0a0e1a', fontFamily: "'Inter', system-ui, sans-serif", color: '#e2e8f0' },
  sidebar: { width: 240, background: '#0d1117', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', position: 'fixed', top: 0, bottom: 0, left: 0, zIndex: 100 },
  sidebarLogo: { padding: '24px 20px', borderBottom: '1px solid #1e293b' },
  logoText: { fontSize: 20, fontWeight: 900, color: '#fff' },
  logoAccent: { color: '#6366f1' },
  logoTag: { fontSize: 9, color: '#8b5cf6', letterSpacing: '2px', textTransform: 'uppercase' as const, marginTop: 2 },
  navSection: { padding: '16px 12px 8px' },
  navLabel: { fontSize: 10, color: '#475569', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase' as const, padding: '0 8px', marginBottom: 4 },
  main: { marginLeft: 240, flex: 1, display: 'flex', flexDirection: 'column' as const },
  topbar: { background: 'rgba(13,17,23,0.9)', backdropFilter: 'blur(20px)', borderBottom: '1px solid #1e293b', padding: '0 32px', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 90 },
  content: { padding: '32px', flex: 1 },
  card: { background: '#111827', border: '1px solid #1e293b', borderRadius: 14, padding: 24 },
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, marginBottom: 24 },
  grid4: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 },
  metricCard: { background: '#111827', border: '1px solid #1e293b', borderRadius: 14, padding: 20 },
  metricNum: { fontSize: 32, fontWeight: 800, color: '#fff', lineHeight: 1 },
  metricLabel: { fontSize: 12, color: '#64748b', textTransform: 'uppercase' as const, letterSpacing: '1px', marginTop: 6 },
  metricChange: { fontSize: 12, marginTop: 8 },
  badge: { display: 'inline-flex', padding: '3px 10px', borderRadius: 99, fontSize: 11, fontWeight: 700 },
  sectionTitle: { fontSize: 18, fontWeight: 700, color: '#f8fafc', marginBottom: 16 },
  tableHeader: { display: 'grid', padding: '10px 16px', background: 'rgba(99,102,241,0.08)', borderRadius: '8px 8px 0 0', fontSize: 11, fontWeight: 600, color: '#64748b', letterSpacing: '1px', textTransform: 'uppercase' as const },
  tableRow: { display: 'grid', padding: '14px 16px', borderBottom: '1px solid #1e293b', fontSize: 13, color: '#94a3b8', alignItems: 'center' },
  progressBar: { height: 6, borderRadius: 3, background: '#1e293b', overflow: 'hidden', marginTop: 8 },
  progressFill: { height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, #6366f1, #8b5cf6)', transition: 'width 0.4s ease' },
};

function NavItem({ icon, label, active, onClick, badge }: { icon: string; label: string; active: boolean; onClick: () => void; badge?: number }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '9px 12px', borderRadius: 8,
        background: active ? 'rgba(99,102,241,0.15)' : 'transparent',
        border: active ? '1px solid rgba(99,102,241,0.25)' : '1px solid transparent',
        color: active ? '#818cf8' : '#64748b', cursor: 'pointer', fontSize: 13, fontWeight: active ? 600 : 400,
        textAlign: 'left', marginBottom: 2, transition: 'all 0.15s',
      }}
    >
      <span style={{ fontSize: 16, width: 20, textAlign: 'center' }}>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {badge ? <span style={{ background: '#6366f1', color: '#fff', borderRadius: 99, fontSize: 10, padding: '1px 6px', fontWeight: 700 }}>{badge}</span> : null}
    </button>
  );
}

function MetricCard({ num, label, change, changeType, icon }: { num: string | number; label: string; change?: string; changeType?: 'up' | 'down' | 'neutral'; icon: string }) {
  const changeColor = changeType === 'up' ? '#10b981' : changeType === 'down' ? '#ef4444' : '#64748b';
  return (
    <div style={s.metricCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
      </div>
      <div style={s.metricNum}>{num}</div>
      <div style={s.metricLabel}>{label}</div>
      {change && <div style={{ ...s.metricChange, color: changeColor }}>{change}</div>}
    </div>
  );
}

function OverviewTab({ user, token }: { user: UserDashboardProps['user']; token: string }) {
  const [stats, setStats] = useState({ totalExperiments: 0, activeSimulations: 0, aiPrompts: 0, storageUsedMb: 0 });
  const [recentExps, setRecentExps] = useState<{ id: string; name: string; status: string; created_at: string; scenario_name?: string }[]>([]);

  useEffect(() => {
    fetch(`${API}/api/experiments?page=1&per_page=5`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => { if (d.experiments) { setRecentExps(d.experiments); setStats((p) => ({ ...p, totalExperiments: d.total || d.experiments.length })); } })
      .catch(() => {});
  }, [token]);

  const verdictColor: Record<string, string> = { NOMINAL: '#10b981', DEGRADED: '#f59e0b', CRITICAL: '#ef4444', FAILED: '#dc2626', running: '#3b82f6' };

  return (
    <>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', marginBottom: 4 }}>
          Good day, {user.first_name || 'Researcher'} 👋
        </h1>
        <p style={{ fontSize: 14, color: '#64748b' }}>Here's your PYPY Grid research overview</p>
      </div>

      <div style={s.grid4}>
        <MetricCard icon="🧪" num={stats.totalExperiments} label="Total Experiments" change="+2 this week" changeType="up" />
        <MetricCard icon="⚡" num={stats.activeSimulations} label="Active Simulations" />
        <MetricCard icon="🤖" num={stats.aiPrompts} label="AI Prompts Used" />
        <MetricCard icon="💾" num={`${(stats.storageUsedMb / 1024).toFixed(1)} GB`} label="Storage Used" />
      </div>

      <div style={s.grid2}>
        <div style={s.card}>
          <div style={s.sectionTitle}>Recent Experiments</div>
          {recentExps.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#475569' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔬</div>
              <p>No experiments yet</p>
              <p style={{ fontSize: 13 }}>Launch your first simulation from the Workspace tab</p>
            </div>
          ) : (
            recentExps.map((exp) => (
              <div key={exp.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #1e293b' }}>
                <div>
                  <div style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 500 }}>{exp.name || exp.scenario_name || 'Experiment'}</div>
                  <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>{new Date(exp.created_at).toLocaleDateString()}</div>
                </div>
                <span style={{ ...s.badge, background: `${verdictColor[exp.status] || '#64748b'}22`, color: verdictColor[exp.status] || '#64748b', border: `1px solid ${verdictColor[exp.status] || '#64748b'}33` }}>
                  {exp.status}
                </span>
              </div>
            ))
          )}
        </div>

        <div style={s.card}>
          <div style={s.sectionTitle}>Quick Launch</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { label: '🔌 IEEE-14 Bus Simulation', desc: 'Basic grid, 5 generators', color: '#6366f1' },
              { label: '⚡ IEEE-39 Bus Attack Test', desc: 'New England test system', color: '#8b5cf6' },
              { label: '📡 FDIA Detection Scenario', desc: 'False data injection test', color: '#06b6d4' },
              { label: '🤖 AI Copilot Research', desc: 'Ask the AI for help', color: '#10b981' },
            ].map((item) => (
              <button key={item.label} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderRadius: 10,
                background: `${item.color}11`, border: `1px solid ${item.color}33`,
                cursor: 'pointer', textAlign: 'left', width: '100%', transition: 'all 0.2s',
              }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: item.color }}>{item.label}</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{item.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function SubscriptionTab({ token }: { token: string }) {
  const [sub, setSub] = useState<{ plan_name?: string; status?: string; expires_at?: string; amount?: number; payment_provider?: string } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/billing/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => setSub(d))
      .catch(() => {});
  }, [token]);

  const planColor: Record<string, string> = { free: '#64748b', academic_premium: '#6366f1', research_lab: '#8b5cf6', enterprise: '#06b6d4' };
  const planName = sub?.plan_name || 'free';
  const color = planColor[planName] || '#6366f1';
  const expiryDate = sub?.expires_at ? new Date(sub.expires_at).toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A';

  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 4 }}>Subscription & Billing</h2>
        <p style={{ fontSize: 14, color: '#64748b' }}>Manage your PYPY Grid subscription plan</p>
      </div>
      <div style={{ ...s.card, marginBottom: 20, borderColor: `${color}33` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, color: '#64748b', marginBottom: 4 }}>Current Plan</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#fff', marginBottom: 8 }}>
              <span style={{ color }}>{planName.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
            </div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ ...s.badge, background: '#10b98122', color: '#10b981', border: '1px solid #10b98133' }}>✓ {sub?.status || 'Active'}</span>
              <span style={{ ...s.badge, background: '#1e293b', color: '#64748b' }}>Expires: {expiryDate}</span>
              {sub?.payment_provider && <span style={{ ...s.badge, background: '#1e293b', color: '#64748b' }}>{sub.payment_provider}</span>}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#fff' }}>
              {sub?.amount == null || sub.amount === 0 ? 'Free' : `RM ${sub.amount}`}
            </div>
            <div style={{ fontSize: 13, color: '#64748b' }}>per month</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {[
          { tier: 'free', name: 'Free', price: 0, features: ['1 topology', '5 scenarios/month', 'Community support'] },
          { tier: 'academic_premium', name: 'Academic Premium', price: 19, features: ['All IEEE topologies', 'Unlimited scenarios', 'AI Copilot', 'Email support'] },
          { tier: 'research_lab', name: 'Research Lab', price: 49, features: ['Everything in Academic', 'Unlimited AI Copilot', 'API access', 'Priority support'] },
          { tier: 'enterprise', name: 'Enterprise', price: null, features: ['Dedicated compute', 'On-premise option', 'Custom integrations', 'Dedicated manager'] },
        ].map((plan) => (
          <div key={plan.tier} style={{
            ...s.card,
            borderColor: plan.tier === planName ? `${planColor[plan.tier]}66` : '#1e293b',
            position: 'relative',
          }}>
            {plan.tier === planName && (
              <div style={{ position: 'absolute', top: 12, right: 12, ...s.badge, background: `${color}22`, color, border: `1px solid ${color}44` }}>Current</div>
            )}
            <div style={{ fontSize: 15, fontWeight: 700, color: planColor[plan.tier], marginBottom: 6 }}>{plan.name}</div>
            <div style={{ fontSize: 24, fontWeight: 900, color: '#fff', marginBottom: 12 }}>
              {plan.price === null ? 'Custom' : plan.price === 0 ? 'Free' : `RM ${plan.price}`}
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px', fontSize: 13, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {plan.features.map((f) => <li key={f}>✓ {f}</li>)}
            </ul>
            {plan.tier !== planName && (
              <button style={{
                width: '100%', padding: '10px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                background: planColor[plan.tier] + '22', border: `1px solid ${planColor[plan.tier]}44`,
                color: planColor[plan.tier], transition: 'all 0.2s',
              }}>
                {plan.tier === 'enterprise' ? 'Contact Sales' : 'Upgrade'}
              </button>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

function UsageTab() {
  const [usage] = useState({
    simulations: { used: 23, limit: 50 },
    aiPrompts: { used: 156, limit: 500 },
    scenarios: { used: 8, limit: -1 },
    storage: { usedMb: 512, limitMb: 5000 },
    apiCalls: { used: 1240, limit: 10000 },
  });

  const pct = (used: number, limit: number) => limit < 0 ? 0 : Math.min(100, (used / limit) * 100);
  const color = (p: number) => p > 90 ? '#ef4444' : p > 70 ? '#f59e0b' : '#10b981';

  const items = [
    { label: 'Simulations', icon: '⚡', used: usage.simulations.used, limit: usage.simulations.limit, unit: '' },
    { label: 'AI Copilot Prompts', icon: '🤖', used: usage.aiPrompts.used, limit: usage.aiPrompts.limit, unit: '' },
    { label: 'Scenarios', icon: '⚔️', used: usage.scenarios.used, limit: usage.scenarios.limit, unit: '' },
    { label: 'Storage', icon: '💾', used: usage.storage.usedMb, limit: usage.storage.limitMb, unit: ' MB' },
    { label: 'API Calls (daily)', icon: '📡', used: usage.apiCalls.used, limit: usage.apiCalls.limit, unit: '' },
  ];

  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 4 }}>Usage & Limits</h2>
        <p style={{ fontSize: 14, color: '#64748b' }}>Monitor your monthly usage across all platform features</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {items.map((item) => {
          const p = pct(item.used, item.limit);
          return (
            <div key={item.label} style={s.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 20 }}>{item.icon}</span>
                  <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>{item.label}</span>
                </div>
                <div style={{ fontSize: 13, color: '#94a3b8', textAlign: 'right' }}>
                  <span style={{ fontWeight: 700, color: '#fff' }}>{item.used.toLocaleString()}{item.unit}</span>
                  {item.limit > 0 && <span style={{ color: '#475569' }}> / {item.limit.toLocaleString()}{item.unit}</span>}
                  {item.limit < 0 && <span style={{ color: '#10b981' }}> / Unlimited</span>}
                </div>
              </div>
              {item.limit > 0 && (
                <>
                  <div style={s.progressBar}>
                    <div style={{ ...s.progressFill, width: `${p}%`, background: `linear-gradient(90deg, ${color(p)}, ${color(p)}88)` }} />
                  </div>
                  <div style={{ fontSize: 11, color: '#475569', marginTop: 6 }}>{p.toFixed(0)}% used</div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

function NotificationsTab({ token }: { token: string }) {
  const [notifs, setNotifs] = useState<{ id: string; message: string; type: string; is_read: boolean; created_at: string }[]>([]);

  useEffect(() => {
    fetch(`${API}/api/auth/notifications`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((d) => { if (Array.isArray(d)) setNotifs(d); })
      .catch(() => {});
  }, [token]);

  const markRead = async (id: string) => {
    await fetch(`${API}/api/auth/notifications/${id}/read`, { method: 'PATCH', headers: { Authorization: `Bearer ${token}` } });
    setNotifs((ns) => ns.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  };

  const typeIcon: Record<string, string> = { info: 'ℹ️', warning: '⚠️', success: '✅', error: '❌', billing: '💳', simulation: '⚡' };
  const typeColor: Record<string, string> = { info: '#3b82f6', warning: '#f59e0b', success: '#10b981', error: '#ef4444', billing: '#8b5cf6', simulation: '#6366f1' };

  return (
    <>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 4 }}>Notifications</h2>
          <p style={{ fontSize: 14, color: '#64748b' }}>{notifs.filter((n) => !n.is_read).length} unread notifications</p>
        </div>
      </div>
      {notifs.length === 0 ? (
        <div style={{ ...s.card, textAlign: 'center', padding: '48px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔔</div>
          <div style={{ fontSize: 16, color: '#64748b' }}>No notifications yet</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {notifs.map((n) => (
            <div
              key={n.id}
              style={{
                ...s.card,
                display: 'flex', gap: 16, alignItems: 'flex-start',
                opacity: n.is_read ? 0.6 : 1,
                borderColor: n.is_read ? '#1e293b' : `${typeColor[n.type] || '#6366f1'}33`,
              }}
            >
              <span style={{ fontSize: 20, flexShrink: 0 }}>{typeIcon[n.type] || 'ℹ️'}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, color: '#e2e8f0', marginBottom: 4 }}>{n.message}</div>
                <div style={{ fontSize: 11, color: '#475569' }}>{new Date(n.created_at).toLocaleString()}</div>
              </div>
              {!n.is_read && (
                <button
                  onClick={() => markRead(n.id)}
                  style={{ fontSize: 12, color: '#6366f1', background: 'transparent', border: 'none', cursor: 'pointer', flexShrink: 0 }}
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

const UserDashboard: React.FC<UserDashboardProps> = ({ token, user, onLogout, onNavigate }) => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const navItems: { id: Tab; icon: string; label: string }[] = [
    { id: 'overview', icon: '🏠', label: 'Overview' },
    { id: 'workspace', icon: '⚡', label: 'Workspace' },
    { id: 'subscription', icon: '💳', label: 'Subscription' },
    { id: 'usage', icon: '📊', label: 'Usage' },
    { id: 'experiments', icon: '🧪', label: 'Experiments' },
    { id: 'notifications', icon: '🔔', label: 'Notifications' },
    { id: 'settings', icon: '⚙️', label: 'Settings' },
  ];

  return (
    <div style={s.layout}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.sidebarLogo}>
          <div style={s.logoText}>PYPY <span style={s.logoAccent}>Grid</span></div>
          <div style={s.logoTag}>Research Platform</div>
        </div>
        <div style={{ padding: '12px', flex: 1, overflowY: 'auto' }}>
          <div style={s.navSection}>
            <div style={s.navLabel}>Navigation</div>
            {navItems.map((item) => (
              <NavItem key={item.id} icon={item.icon} label={item.label} active={activeTab === item.id} onClick={() => setActiveTab(item.id)} />
            ))}
          </div>
          <div style={{ padding: '8px 12px' }}>
            <div style={s.navLabel}>Platform</div>
            <NavItem icon="🤖" label="AI Copilot" active={false} onClick={() => onNavigate('copilot')} />
            <NavItem icon="🛒" label="Marketplace" active={false} onClick={() => onNavigate('marketplace')} />
            <NavItem icon="📚" label="Docs" active={false} onClick={() => window.open('https://docs.pypygrid.com', '_blank')} />
          </div>
        </div>
        <div style={{ padding: '16px 12px', borderTop: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: '#1a2332', borderRadius: 10, marginBottom: 8 }}>
            <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color: '#fff' }}>
              {(user.first_name?.[0] || 'U').toUpperCase()}
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.first_name} {user.last_name}
              </div>
              <div style={{ fontSize: 11, color: '#475569', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.email}
              </div>
            </div>
          </div>
          <button onClick={onLogout} style={{ width: '100%', padding: '9px', borderRadius: 8, background: 'transparent', border: '1px solid #1e293b', color: '#64748b', cursor: 'pointer', fontSize: 12, transition: 'all 0.2s' }}>
            Sign Out
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={s.main}>
        <div style={s.topbar}>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e8f0' }}>
            {navItems.find((n) => n.id === activeTab)?.icon} {navItems.find((n) => n.id === activeTab)?.label}
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ ...s.badge, background: 'rgba(99,102,241,0.15)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', fontSize: 12 }}>
              {user.role || 'researcher'}
            </span>
            <button style={{ padding: '8px 16px', borderRadius: 8, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, boxShadow: '0 0 20px rgba(99,102,241,0.3)' }}>
              + New Experiment
            </button>
          </div>
        </div>

        <div style={s.content}>
          {activeTab === 'overview' && <OverviewTab user={user} token={token} />}
          {activeTab === 'subscription' && <SubscriptionTab token={token} />}
          {activeTab === 'usage' && <UsageTab />}
          {activeTab === 'notifications' && <NotificationsTab token={token} />}
          {activeTab === 'workspace' && (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>⚡</div>
              <h2 style={{ color: '#fff', marginBottom: 8 }}>Research Workspace</h2>
              <p style={{ color: '#64748b', fontSize: 14 }}>Launch and manage your grid simulations here.</p>
              <button style={{ marginTop: 20, padding: '12px 28px', borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 700 }}>
                + Launch New Simulation
              </button>
            </div>
          )}
          {activeTab === 'experiments' && (
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 16 }}>Experiments</h2>
              <div style={{ ...s.card, textAlign: 'center', padding: '48px' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🧪</div>
                <p style={{ color: '#64748b' }}>Your experiments will appear here.</p>
              </div>
            </div>
          )}
          {activeTab === 'settings' && (
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 16 }}>Account Settings</h2>
              <div style={s.card}>
                <div style={{ ...s.sectionTitle, marginBottom: 20 }}>Profile Information</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>First Name</label>
                    <input value={user.first_name || ''} readOnly style={{ width: '100%', padding: '10px 14px', borderRadius: 8, background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', fontSize: 14, boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>Last Name</label>
                    <input value={user.last_name || ''} readOnly style={{ width: '100%', padding: '10px 14px', borderRadius: 8, background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', fontSize: 14, boxSizing: 'border-box' }} />
                  </div>
                </div>
                <div style={{ marginTop: 16 }}>
                  <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>Email</label>
                  <input value={user.email || ''} readOnly style={{ width: '100%', padding: '10px 14px', borderRadius: 8, background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', fontSize: 14, boxSizing: 'border-box' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;
