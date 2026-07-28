import React, { useState } from 'react';

interface WorkspaceSetupWizardProps {
  token: string;
  user: { first_name?: string; email?: string };
  onComplete: () => void;
}

type Step = 'welcome' | 'profile' | 'institution' | 'preferences' | 'first_sim' | 'done';

const STEPS: { id: Step; label: string; icon: string }[] = [
  { id: 'welcome', label: 'Welcome', icon: '👋' },
  { id: 'profile', label: 'Profile', icon: '👤' },
  { id: 'institution', label: 'Institution', icon: '🏛️' },
  { id: 'preferences', label: 'Preferences', icon: '⚙️' },
  { id: 'first_sim', label: 'First Sim', icon: '⚡' },
  { id: 'done', label: 'Done', icon: '🎉' },
];

const API = '';

const card: React.CSSProperties = {
  background: 'rgba(17,24,39,0.95)',
  backdropFilter: 'blur(24px)',
  border: '1px solid rgba(99,102,241,0.2)',
  borderRadius: 24,
  padding: '48px 44px',
  width: '100%',
  maxWidth: 560,
  boxShadow: '0 32px 80px rgba(0,0,0,0.6)',
};

const page: React.CSSProperties = {
  minHeight: '100vh',
  background: 'radial-gradient(ellipse 100% 80% at 50% 0%, rgba(99,102,241,0.12) 0%, #0a0e1a 70%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '40px 20px',
  fontFamily: "'Inter', system-ui, sans-serif",
  color: '#e2e8f0',
};

function Input({ label, type = 'text', value, onChange, placeholder, hint }: {
  label: string; type?: string; value: string; onChange: (v: string) => void; placeholder?: string; hint?: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 6 }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
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
      {hint && <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 6 }}>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%', padding: '12px 16px', borderRadius: 10, background: '#1e293b', color: '#f8fafc', border: '1px solid #334155', fontSize: 14, outline: 'none', boxSizing: 'border-box' }}
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function CheckCard({ icon, label, desc, selected, onClick }: { icon: string; label: string; desc: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 16px', borderRadius: 12, width: '100%',
        background: selected ? 'rgba(99,102,241,0.12)' : 'rgba(17,24,39,0.6)',
        border: `1px solid ${selected ? 'rgba(99,102,241,0.5)' : '#1e293b'}`,
        cursor: 'pointer', textAlign: 'left', marginBottom: 10, transition: 'all 0.2s',
      }}
    >
      <span style={{ fontSize: 22, marginTop: 2 }}>{icon}</span>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: selected ? '#818cf8' : '#e2e8f0' }}>{label}</div>
        <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{desc}</div>
      </div>
      {selected && <span style={{ marginLeft: 'auto', color: '#10b981', fontSize: 18 }}>✓</span>}
    </button>
  );
}

function StepIndicator({ steps, currentStep }: { steps: typeof STEPS; currentStep: Step }) {
  const currentIdx = steps.findIndex((s) => s.id === currentStep);
  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: 0, marginBottom: 40 }}>
      {steps.map((step, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <React.Fragment key={step.id}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: done ? '#10b981' : active ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : '#1e293b',
                border: `2px solid ${done ? '#10b981' : active ? '#6366f1' : '#334155'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: done ? 14 : 15, fontWeight: 700, color: done || active ? '#fff' : '#475569',
                boxShadow: active ? '0 0 20px rgba(99,102,241,0.4)' : 'none',
                transition: 'all 0.3s',
              }}>
                {done ? '✓' : step.icon}
              </div>
              <div style={{ fontSize: 10, color: active ? '#818cf8' : done ? '#10b981' : '#475569', fontWeight: active ? 600 : 400, textAlign: 'center' }}>
                {step.label}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div style={{ width: 32, height: 2, background: i < currentIdx ? '#10b981' : '#1e293b', alignSelf: 'center', marginBottom: 18, transition: 'background 0.3s' }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

const WorkspaceSetupWizard: React.FC<WorkspaceSetupWizardProps> = ({ token, user, onComplete }) => {
  const [step, setStep] = useState<Step>('welcome');

  const [profile, setProfile] = useState({
    title: '',
    bio: '',
    research_focus: 'cybersecurity',
  });
  const [institution, setInstitution] = useState({
    name: '',
    department: '',
    country: 'Malaysia',
    website: '',
  });
  const [prefs, setPrefs] = useState({
    preferred_topology: 'ieee14',
    notifications_email: true,
    ai_copilot_enabled: true,
    research_areas: [] as string[],
  });
  const [firstSim, setFirstSim] = useState({
    topology: 'ieee14',
    scenario: 'fdia_basic',
    launchNow: false,
  });

  const goNext = () => {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1].id);
  };

  const goBack = () => {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx > 0) setStep(STEPS[idx - 1].id);
  };

  const handleFinish = async () => {
    try {
      await fetch(`${API}/api/auth/workspace/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          display_name: `${user.first_name}'s Workspace`,
          institution_name: institution.name,
          department: institution.department,
          country: institution.country,
          research_focus: profile.research_focus,
          preferred_topology: prefs.preferred_topology,
          notifications_email: prefs.notifications_email,
        }),
      });
    } catch (e) { /* best effort */ }
    setStep('done');
  };

  const btnNext = (label = 'Continue →', onPress?: () => void, primary = true) => (
    <button
      onClick={onPress || goNext}
      style={{
        width: '100%', padding: '13px', borderRadius: 10, fontSize: 15, fontWeight: 700, cursor: 'pointer',
        background: primary ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : 'transparent',
        color: primary ? '#fff' : '#818cf8',
        border: primary ? 'none' : '1px solid rgba(99,102,241,0.3)',
        boxShadow: primary ? '0 0 24px rgba(99,102,241,0.4)' : 'none',
        marginTop: 8,
      }}
    >{label}</button>
  );

  const btnBack = () => (
    <button onClick={goBack} style={{ width: '100%', padding: '11px', borderRadius: 10, fontSize: 14, fontWeight: 500, cursor: 'pointer', background: 'transparent', color: '#64748b', border: '1px solid #1e293b', marginTop: 8 }}>
      ← Back
    </button>
  );

  const toggleArea = (area: string) => {
    setPrefs((p) => ({
      ...p,
      research_areas: p.research_areas.includes(area)
        ? p.research_areas.filter((a) => a !== area)
        : [...p.research_areas, area],
    }));
  };

  return (
    <div style={page}>
      <div style={card}>
        <StepIndicator steps={STEPS} currentStep={step} />

        {/* Welcome */}
        {step === 'welcome' && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 60, marginBottom: 20 }}>⚡</div>
            <h1 style={{ fontSize: 28, fontWeight: 900, color: '#fff', marginBottom: 12, lineHeight: 1.2 }}>
              Welcome to<br /><span style={{ color: '#6366f1' }}>PYPY Grid</span>
            </h1>
            <p style={{ fontSize: 15, color: '#64748b', lineHeight: 1.7, marginBottom: 32 }}>
              Hi {user.first_name || 'there'}! Let's set up your research workspace in about 2 minutes.
              You can always change these settings later.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left', background: 'rgba(99,102,241,0.06)', borderRadius: 12, padding: '20px 24px', marginBottom: 28 }}>
              {[
                ['👤', 'Set up your researcher profile'],
                ['🏛️', 'Add your institution details'],
                ['⚙️', 'Choose your research preferences'],
                ['⚡', 'Configure your first simulation'],
              ].map(([icon, text]) => (
                <div key={text} style={{ display: 'flex', gap: 12, alignItems: 'center', fontSize: 14, color: '#94a3b8' }}>
                  <span>{icon}</span> {text}
                </div>
              ))}
            </div>
            {btnNext("Let's Get Started →")}
          </div>
        )}

        {/* Profile */}
        {step === 'profile' && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Your Researcher Profile</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 28 }}>Tell us about your research background</p>
            <Select label="Title" value={profile.title} onChange={(v) => setProfile((p) => ({ ...p, title: v }))} options={[
              { value: '', label: 'Select title' },
              { value: 'Dr', label: 'Dr.' },
              { value: 'Prof', label: 'Prof.' },
              { value: 'Assoc Prof', label: 'Assoc. Prof.' },
              { value: 'Mr', label: 'Mr.' },
              { value: 'Ms', label: 'Ms.' },
              { value: 'Student', label: 'Student Researcher' },
            ]} />
            <Select label="Primary Research Focus" value={profile.research_focus} onChange={(v) => setProfile((p) => ({ ...p, research_focus: v }))} options={[
              { value: 'cybersecurity', label: 'Grid Cybersecurity' },
              { value: 'power_systems', label: 'Power Systems Engineering' },
              { value: 'iot_scada', label: 'IoT & SCADA Security' },
              { value: 'ml_ai', label: 'ML/AI for Grid Defense' },
              { value: 'policy', label: 'Critical Infrastructure Policy' },
              { value: 'other', label: 'Other' },
            ]} />
            <Input label="Short Bio (optional)" value={profile.bio} onChange={(v) => setProfile((p) => ({ ...p, bio: v }))} placeholder="e.g. PhD candidate studying FDIA detection in IEEE-118 grids..." hint="This helps personalize your AI Copilot responses." />
            {btnNext()}
            {btnBack()}
          </div>
        )}

        {/* Institution */}
        {step === 'institution' && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Your Institution</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 28 }}>We use this for academic licensing and collaboration features.</p>
            <Input label="Institution / Organization Name" value={institution.name} onChange={(v) => setInstitution((p) => ({ ...p, name: v }))} placeholder="Universiti Teknologi Malaysia" />
            <Input label="Department / Faculty" value={institution.department} onChange={(v) => setInstitution((p) => ({ ...p, department: v }))} placeholder="Faculty of Electrical Engineering" />
            <Select label="Country" value={institution.country} onChange={(v) => setInstitution((p) => ({ ...p, country: v }))} options={[
              { value: 'Malaysia', label: '🇲🇾 Malaysia' },
              { value: 'Singapore', label: '🇸🇬 Singapore' },
              { value: 'Indonesia', label: '🇮🇩 Indonesia' },
              { value: 'Thailand', label: '🇹🇭 Thailand' },
              { value: 'United Kingdom', label: '🇬🇧 United Kingdom' },
              { value: 'United States', label: '🇺🇸 United States' },
              { value: 'Other', label: '🌍 Other' },
            ]} />
            <Input label="Institution Website (optional)" type="url" value={institution.website} onChange={(v) => setInstitution((p) => ({ ...p, website: v }))} placeholder="https://utm.my" />
            {btnNext()}
            {btnBack()}
          </div>
        )}

        {/* Preferences */}
        {step === 'preferences' && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Research Preferences</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Choose your areas of interest for personalized recommendations.</p>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 12 }}>Research Areas (select all that apply)</div>
            {[
              ['⚔️', 'FDIA', 'False Data Injection Attacks'],
              ['🔌', 'Relay Attacks', 'Protection relay manipulation'],
              ['📡', 'SCADA Security', 'Industrial control systems'],
              ['🤖', 'ML Defense', 'Machine learning for anomaly detection'],
              ['🔗', 'Blockchain', 'Tamper-proof telemetry'],
              ['🛡️', 'Resilience', 'Grid recovery and fault tolerance'],
            ].map(([icon, key, desc]) => (
              <CheckCard
                key={key}
                icon={icon}
                label={key}
                desc={desc}
                selected={prefs.research_areas.includes(key)}
                onClick={() => toggleArea(key)}
              />
            ))}
            <Select label="Preferred Default Topology" value={prefs.preferred_topology} onChange={(v) => setPrefs((p) => ({ ...p, preferred_topology: v }))} options={[
              { value: 'ieee14', label: 'IEEE 14-Bus (Standard intro)' },
              { value: 'ieee39', label: 'IEEE 39-Bus (New England)' },
              { value: 'ieee57', label: 'IEEE 57-Bus (Mid-size)' },
              { value: 'ieee118', label: 'IEEE 118-Bus (Large-scale)' },
            ]} />
            {btnNext()}
            {btnBack()}
          </div>
        )}

        {/* First Simulation */}
        {step === 'first_sim' && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 6 }}>Your First Simulation</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>Configure your first experiment. You can change these any time.</p>

            <div style={{ fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 10 }}>Grid Topology</div>
            {[
              { value: 'ieee14', label: 'IEEE 14-Bus', desc: 'Recommended for beginners', icon: '🔌' },
              { value: 'ieee39', label: 'IEEE 39-Bus', desc: 'New England test system', icon: '⚡' },
              { value: 'ieee118', label: 'IEEE 118-Bus', desc: 'Large-scale simulation', icon: '🏭' },
            ].map((t) => (
              <CheckCard key={t.value} icon={t.icon} label={t.label} desc={t.desc} selected={firstSim.topology === t.value} onClick={() => setFirstSim((p) => ({ ...p, topology: t.value }))} />
            ))}

            <div style={{ fontSize: 13, fontWeight: 500, color: '#94a3b8', marginBottom: 10, marginTop: 20 }}>Attack Scenario</div>
            {[
              { value: 'fdia_basic', label: 'Basic FDIA Attack', desc: 'False data injection on sensor readings', icon: '🎯' },
              { value: 'replay', label: 'Replay Attack', desc: 'Replay captured SCADA commands', icon: '🔁' },
              { value: 'coordinated_trip', label: 'Coordinated Line Trip', desc: 'Multi-relay simultaneous attack', icon: '⚠️' },
            ].map((sc) => (
              <CheckCard key={sc.value} icon={sc.icon} label={sc.label} desc={sc.desc} selected={firstSim.scenario === sc.value} onClick={() => setFirstSim((p) => ({ ...p, scenario: sc.value }))} />
            ))}

            {btnNext("Save & Complete Setup", handleFinish)}
            {btnBack()}
          </div>
        )}

        {/* Done */}
        {step === 'done' && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 64, marginBottom: 20 }}>🎉</div>
            <h2 style={{ fontSize: 26, fontWeight: 900, color: '#fff', marginBottom: 12 }}>You're all set!</h2>
            <p style={{ fontSize: 15, color: '#64748b', lineHeight: 1.7, marginBottom: 32 }}>
              Your research workspace is configured. Your first simulation scenario is queued and ready to launch.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                onClick={onComplete}
                style={{ padding: '14px', borderRadius: 12, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 16, fontWeight: 700, boxShadow: '0 0 30px rgba(99,102,241,0.4)' }}
              >
                🚀 Go to Dashboard
              </button>
              <button
                style={{ padding: '12px', borderRadius: 12, background: 'transparent', border: '1px solid rgba(6,182,212,0.3)', color: '#06b6d4', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
              >
                ⚡ Launch First Simulation Now
              </button>
            </div>
            <div style={{ marginTop: 24, padding: '16px', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: 10, fontSize: 13, color: '#10b981', lineHeight: 1.6 }}>
              🎓 Academic tip: Check out our{' '}
              <a href="https://docs.pypygrid.com/quick-start" style={{ color: '#6366f1' }}>5-minute quickstart guide</a>{' '}
              to get your first resilience score in minutes.
            </div>
          </div>
        )}

        {/* Progress indicator */}
        <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: '#475569' }}>Step {STEPS.findIndex((s) => s.id === step) + 1} of {STEPS.length}</span>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceSetupWizard;
