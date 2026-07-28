import React, { useState, useEffect, useRef } from 'react';

interface LandingPageProps {
  onNavigate: (page: string) => void;
}

const PLANS = [
  {
    name: 'Free',
    tier: 'free',
    price: 0,
    billing: 'forever',
    badge: null,
    color: '#64748b',
    features: [
      '1 IEEE-14 bus topology',
      '5 scenarios per month',
      '3 concurrent simulations',
      'Basic resilience scoring',
      'Community support',
    ],
    missing: ['AI Copilot', 'Research Workspace', 'IEEE-39/57/118', 'API access'],
    cta: 'Start Free',
    ctaAction: 'register',
  },
  {
    name: 'Academic Premium',
    tier: 'academic_premium',
    price: 19,
    billing: '/month',
    badge: 'Popular',
    color: '#6366f1',
    features: [
      'All IEEE topologies (14/39/57/118)',
      'Unlimited scenarios',
      '10 concurrent simulations',
      'AI Copilot (500 msgs/mo)',
      'Research Workspace',
      'Blockchain telemetry',
      'Export PDF reports',
      'Email support',
    ],
    missing: ['Dedicated compute', 'Custom scenarios', 'White-label'],
    cta: 'Start Academic',
    ctaAction: 'register',
  },
  {
    name: 'Research Lab',
    tier: 'research_lab',
    price: 49,
    billing: '/month',
    badge: 'Best Value',
    color: '#8b5cf6',
    features: [
      'Everything in Academic',
      'Unlimited concurrent simulations',
      'AI Copilot (unlimited)',
      'Scenario Marketplace access',
      'Advanced MITRE ATT&CK mapping',
      'Multi-tenant support',
      'API access (10,000 req/day)',
      'Priority support (24h SLA)',
    ],
    missing: ['Dedicated servers', 'On-premise option'],
    cta: 'Start Lab',
    ctaAction: 'register',
  },
  {
    name: 'Enterprise',
    tier: 'enterprise',
    price: null,
    billing: 'Custom',
    badge: 'Custom',
    color: '#06b6d4',
    features: [
      'Everything in Research Lab',
      'Dedicated compute cluster',
      'On-premise deployment',
      'Custom scenario development',
      'White-label branding',
      'Unlimited API access',
      'Dedicated account manager',
      'SLA 99.9% uptime guarantee',
      'Custom integration support',
    ],
    missing: [],
    cta: 'Book Enterprise Demo',
    ctaAction: 'enterprise_contact',
  },
];

const FEATURES = [
  {
    icon: '🔌',
    title: 'Digital Twin Simulation',
    desc: 'Physics-accurate IEEE grid models (14/39/57/118-bus). Simulate attack scenarios on a virtual replica of real power infrastructure without any risk.',
    accent: '#6366f1',
  },
  {
    icon: '⚔️',
    title: 'MITRE ATT&CK ICS',
    desc: '500+ cyber attack scenarios mapped to MITRE ATT&CK for ICS framework. Test coordinated tripping, FDIA, replay attacks, and zero-day simulations.',
    accent: '#8b5cf6',
  },
  {
    icon: '🤖',
    title: 'AI Copilot Research',
    desc: 'GPT-powered research assistant specialized in grid cybersecurity. Auto-generate research summaries, literature reviews, and scenario analyses.',
    accent: '#06b6d4',
  },
  {
    icon: '🔗',
    title: 'Blockchain Telemetry',
    desc: 'Tamper-proof measurement recording on a distributed ledger. Every SCADA reading, alarm event, and system state is immutably logged.',
    accent: '#10b981',
  },
  {
    icon: '📊',
    title: 'Multi-Bus Topology',
    desc: 'IEEE 14, 39, 57, and 118-bus systems. Configure load profiles, generation schedules, protection relay settings, and N-1 contingencies.',
    accent: '#f59e0b',
  },
  {
    icon: '📡',
    title: 'Real-time Monitoring',
    desc: 'Live WebSocket telemetry dashboard. Monitor voltage, frequency, power flow, and alarm states as simulations execute in real time.',
    accent: '#ef4444',
  },
];

const FAQS = [
  {
    q: 'What is PYPY Grid?',
    a: 'PYPY Grid is a cloud-based smart grid cybersecurity research platform. It provides digital twin simulations of IEEE power grid topologies so researchers can safely test cyberattack scenarios, measure resilience, and develop defensive strategies.',
  },
  {
    q: 'Who is PYPY Grid designed for?',
    a: 'Primarily for academic researchers, cybersecurity engineers, utility companies, national cybersecurity agencies, and postgraduate students studying critical infrastructure security. Our Academic Premium plan is specifically designed for university lab environments.',
  },
  {
    q: 'Do I need a powerful computer to run simulations?',
    a: 'No. All simulations run on PYPY Grid\'s cloud infrastructure. You only need a modern web browser. No software installation required.',
  },
  {
    q: 'How realistic are the simulations?',
    a: 'Highly realistic. Our grid models use IEEE standard parameters with physics-based power flow solvers (Newton-Raphson). Attack scenarios are modeled after documented real-world incidents and MITRE ATT&CK ICS techniques.',
  },
  {
    q: 'Is my research data kept private?',
    a: 'Yes. Each institution operates in a fully isolated tenant environment. Your experiments, scenarios, and results are never shared with other organizations. See our Privacy Policy for full details.',
  },
  {
    q: 'Can I publish research using PYPY Grid?',
    a: 'Absolutely. Academic and Research Lab subscribers are licensed to publish findings in journals and conferences. We ask that you cite PYPY Grid in your publications.',
  },
  {
    q: 'What billing methods are supported?',
    a: 'We accept credit/debit cards via Stripe, and Malaysian online banking via ToyyibPay (FPX). Enterprise customers may arrange invoice billing. All prices in RM (Malaysian Ringgit).',
  },
  {
    q: 'What happens to my data if I cancel?',
    a: 'Your experiments and results remain accessible for 30 days after subscription expiry. You can export all your data during this period. After 30 days, data is archived and retrievable upon resubscription.',
  },
];

const TESTIMONIALS = [
  {
    name: 'Dr. Sarah Chen',
    role: 'Associate Professor, Universiti Teknologi Malaysia',
    text: 'PYPY Grid has transformed how we teach grid cybersecurity. Our postgrads can now run FDIA experiments that would be impossible on real infrastructure. The MITRE ATT&CK mapping is exceptional.',
    initials: 'SC',
    color: '#6366f1',
  },
  {
    name: 'Ahmad Razif',
    role: 'Senior Engineer, TNB Research',
    text: 'We used PYPY Grid to validate our protection relay configurations against 200+ attack scenarios in a weekend. The resilience scoring gave us concrete metrics to present to management.',
    initials: 'AR',
    color: '#8b5cf6',
  },
  {
    name: 'Dr. Marcus Webb',
    role: 'PhD Researcher, ICS Security Lab',
    text: 'The blockchain telemetry feature is a game-changer for tamper-evident logging. I\'ve published two papers based on PYPY Grid simulation data. The AI Copilot is surprisingly useful for literature reviews.',
    initials: 'MW',
    color: '#06b6d4',
  },
];

// Animated grid nodes component
const AnimatedGrid: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    const nodes: { x: number; y: number; vx: number; vy: number; r: number; pulse: number }[] = [];
    for (let i = 0; i < 28; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 3 + 2,
        pulse: Math.random() * Math.PI * 2,
      });
    }

    let frame = 0;
    const animate = () => {
      ctx.fillStyle = 'rgba(10, 14, 26, 0.08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      frame++;

      nodes.forEach((n) => {
        n.x += n.vx;
        n.y += n.vy;
        n.pulse += 0.02;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      });

      // Draw connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 180) {
            const alpha = (1 - dist / 180) * 0.35;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      nodes.forEach((n) => {
        const glow = (Math.sin(n.pulse) + 1) / 2;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r + glow * 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99, 102, 241, ${0.4 + glow * 0.6})`;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = '#818cf8';
        ctx.fill();
      });

      requestAnimationFrame(animate);
    };
    const raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.7 }}
    />
  );
};

const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const [scrolled, setScrolled] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [email, setEmail] = useState('');

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  const s: Record<string, React.CSSProperties> = {
    page: { background: '#0a0e1a', color: '#e2e8f0', fontFamily: "'Inter', system-ui, sans-serif", overflowX: 'hidden' },
    nav: {
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
      background: scrolled ? 'rgba(10,14,26,0.95)' : 'transparent',
      backdropFilter: scrolled ? 'blur(20px)' : 'none',
      borderBottom: scrolled ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent',
      transition: 'all 0.3s ease',
      padding: '0 32px',
    },
    navInner: { maxWidth: 1200, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68 },
    logo: { display: 'flex', flexDirection: 'column', cursor: 'pointer' },
    logoText: { fontSize: 22, fontWeight: 800, color: '#fff', letterSpacing: '-0.5px', lineHeight: 1.1 },
    logoAccent: { color: '#6366f1' },
    logoTag: { fontSize: 9, color: '#8b5cf6', letterSpacing: '2px', textTransform: 'uppercase' as const },
    navLinks: { display: 'flex', gap: 32, alignItems: 'center' },
    navLink: { color: '#94a3b8', fontSize: 14, fontWeight: 500, cursor: 'pointer', transition: 'color 0.2s', background: 'none', border: 'none', padding: 0 },
    navCtas: { display: 'flex', gap: 12, alignItems: 'center' },
    btnOutline: { padding: '8px 20px', borderRadius: 8, border: '1px solid rgba(99,102,241,0.5)', color: '#818cf8', background: 'transparent', cursor: 'pointer', fontSize: 14, fontWeight: 500, transition: 'all 0.2s' },
    btnPrimary: { padding: '8px 20px', borderRadius: 8, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 600, transition: 'all 0.2s', boxShadow: '0 0 20px rgba(99,102,241,0.3)' },

    // Hero
    hero: { position: 'relative' as const, minHeight: '100vh', display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', textAlign: 'center' as const, padding: '120px 32px 80px', overflow: 'hidden' },
    heroBg: { position: 'absolute' as const, inset: 0, background: 'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(99,102,241,0.12) 0%, transparent 70%)', pointerEvents: 'none' as const },
    eyebrow: { display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 99, padding: '6px 16px', fontSize: 12, color: '#818cf8', fontWeight: 600, letterSpacing: '0.5px', marginBottom: 24, textTransform: 'uppercase' as const },
    heroTitle: { fontSize: 'clamp(36px, 6vw, 72px)', fontWeight: 900, color: '#fff', lineHeight: 1.1, marginBottom: 24, maxWidth: 900 },
    heroGradText: { background: 'linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' },
    heroSub: { fontSize: 18, color: '#94a3b8', lineHeight: 1.7, maxWidth: 640, marginBottom: 40 },
    heroCtas: { display: 'flex', gap: 16, flexWrap: 'wrap' as const, justifyContent: 'center' },
    btnLarge: { padding: '14px 32px', borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 16, fontWeight: 700, boxShadow: '0 0 30px rgba(99,102,241,0.4)', transition: 'all 0.2s' },
    btnLargeOutline: { padding: '14px 32px', borderRadius: 10, border: '1px solid rgba(99,102,241,0.4)', color: '#818cf8', background: 'transparent', cursor: 'pointer', fontSize: 16, fontWeight: 600, transition: 'all 0.2s' },

    // Stats bar
    stats: { display: 'flex', gap: 0, background: 'rgba(99,102,241,0.05)', borderTop: '1px solid rgba(99,102,241,0.15)', borderBottom: '1px solid rgba(99,102,241,0.15)', padding: '20px 0', flexWrap: 'wrap' as const, justifyContent: 'center' },
    stat: { textAlign: 'center' as const, padding: '0 40px', borderRight: '1px solid rgba(99,102,241,0.15)' },
    statNum: { fontSize: 28, fontWeight: 800, color: '#fff' },
    statLabel: { fontSize: 12, color: '#64748b', textTransform: 'uppercase' as const, letterSpacing: '1px', marginTop: 2 },

    section: { maxWidth: 1200, margin: '0 auto', padding: '80px 32px' },
    sectionTag: { fontSize: 12, color: '#6366f1', textTransform: 'uppercase' as const, letterSpacing: '2px', fontWeight: 700, marginBottom: 12 },
    sectionTitle: { fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800, color: '#fff', marginBottom: 16, lineHeight: 1.2 },
    sectionSub: { fontSize: 17, color: '#64748b', maxWidth: 600, lineHeight: 1.7 },

    // Features
    featureGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, marginTop: 48 },
    featureCard: { background: 'rgba(17,24,39,0.8)', border: '1px solid #1e293b', borderRadius: 16, padding: 28, transition: 'all 0.3s', cursor: 'default' },
    featureIcon: { fontSize: 36, marginBottom: 16 },
    featureTitle: { fontSize: 18, fontWeight: 700, color: '#fff', marginBottom: 10 },
    featureDesc: { fontSize: 14, color: '#64748b', lineHeight: 1.7 },

    // How it works
    steps: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 32, marginTop: 48 },
    step: { textAlign: 'center' as const },
    stepNum: { width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 800, color: '#fff', margin: '0 auto 20px', boxShadow: '0 0 24px rgba(99,102,241,0.4)' },
    stepTitle: { fontSize: 16, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 },
    stepDesc: { fontSize: 14, color: '#64748b', lineHeight: 1.6 },

    // Testimonials
    testimonialGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24, marginTop: 48 },
    testimonialCard: { background: 'rgba(17,24,39,0.8)', border: '1px solid #1e293b', borderRadius: 16, padding: 28 },
    quote: { fontSize: 15, color: '#94a3b8', lineHeight: 1.8, marginBottom: 24, fontStyle: 'italic' },
    author: { display: 'flex', alignItems: 'center', gap: 12 },
    avatar: { width: 44, height: 44, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#fff', flexShrink: 0 },
    authorName: { fontSize: 14, fontWeight: 700, color: '#e2e8f0' },
    authorRole: { fontSize: 12, color: '#64748b' },

    // Pricing
    planGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 24, marginTop: 48 },
    planCard: { borderRadius: 16, padding: 28, border: '1px solid #1e293b', background: 'rgba(17,24,39,0.9)', display: 'flex', flexDirection: 'column' as const, position: 'relative' as const, overflow: 'hidden' },
    planBadge: { position: 'absolute' as const, top: 16, right: 16, fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 99, letterSpacing: '0.5px' },
    planName: { fontSize: 18, fontWeight: 800, color: '#fff', marginBottom: 4 },
    planPrice: { fontSize: 40, fontWeight: 900, color: '#fff', lineHeight: 1, marginBottom: 4 },
    planBilling: { fontSize: 13, color: '#64748b', marginBottom: 24 },
    planFeatures: { listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column' as const, gap: 10, flex: 1 },
    planFeatureItem: { fontSize: 13, color: '#94a3b8', display: 'flex', gap: 8, alignItems: 'flex-start' },
    check: { color: '#10b981', flexShrink: 0 },

    // FAQ
    faqList: { marginTop: 48, display: 'flex', flexDirection: 'column' as const, gap: 12 },
    faqItem: { background: 'rgba(17,24,39,0.8)', border: '1px solid #1e293b', borderRadius: 12, overflow: 'hidden' },
    faqQ: { padding: '18px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', fontSize: 15, fontWeight: 600, color: '#e2e8f0' },
    faqA: { padding: '0 24px 18px', fontSize: 14, color: '#64748b', lineHeight: 1.7 },

    // CTA section
    ctaSection: { background: 'linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.05) 100%)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 24, padding: '64px 40px', textAlign: 'center' as const, margin: '0 32px 80px' },
    ctaTitle: { fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800, color: '#fff', marginBottom: 16 },
    ctaSub: { fontSize: 17, color: '#64748b', marginBottom: 32 },
    ctaForm: { display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' as const, maxWidth: 480, margin: '0 auto' },
    ctaInput: { flex: 1, minWidth: 240, padding: '12px 18px', borderRadius: 10, border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(17,24,39,0.8)', color: '#e2e8f0', fontSize: 15, outline: 'none' },

    // Footer
    footer: { background: '#050810', borderTop: '1px solid #111827', padding: '60px 32px 32px' },
    footerInner: { maxWidth: 1200, margin: '0 auto' },
    footerTop: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 40, marginBottom: 48 },
    footerBrand: { gridColumn: 'span 2' },
    footerTagline: { fontSize: 13, color: '#475569', lineHeight: 1.7, maxWidth: 260, marginTop: 8 },
    footerHeading: { fontSize: 12, fontWeight: 700, color: '#e2e8f0', textTransform: 'uppercase' as const, letterSpacing: '1px', marginBottom: 16 },
    footerLinks: { display: 'flex', flexDirection: 'column' as const, gap: 10 },
    footerLink: { fontSize: 13, color: '#64748b', cursor: 'pointer', transition: 'color 0.2s', background: 'none', border: 'none', textAlign: 'left' as const, padding: 0 },
    footerBottom: { borderTop: '1px solid #111827', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' as const, gap: 12 },
    footerCopy: { fontSize: 12, color: '#334155' },
  };

  return (
    <div style={s.page}>
      {/* Navbar */}
      <nav style={s.nav}>
        <div style={s.navInner}>
          <div style={s.logo} onClick={() => scrollTo('hero')}>
            <div style={s.logoText}>PYPY <span style={s.logoAccent}>Grid</span></div>
            <div style={s.logoTag}>Protect Your Power</div>
          </div>
          <div style={s.navLinks}>
            {['features', 'pricing', 'faq'].map((id) => (
              <button key={id} style={s.navLink} onClick={() => scrollTo(id)}>
                {id.charAt(0).toUpperCase() + id.slice(1)}
              </button>
            ))}
            <button style={s.navLink} onClick={() => window.open('https://docs.pypygrid.com', '_blank')}>Docs</button>
          </div>
          <div style={s.navCtas}>
            <button style={s.btnOutline} onClick={() => onNavigate('login')}>Sign In</button>
            <button style={s.btnPrimary} onClick={() => onNavigate('register')}>Start Free</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section id="hero" style={s.hero}>
        <AnimatedGrid />
        <div style={s.heroBg} />
        <div style={{ position: 'relative', zIndex: 1, maxWidth: 960 }}>
          <div style={s.eyebrow}>
            <span>⚡</span> IEEE-Based Smart Grid Research Platform
          </div>
          <h1 style={s.heroTitle}>
            <span style={s.heroGradText}>Protect Your Power,</span>
            <br />Protect Yourself.
          </h1>
          <p style={s.heroSub}>
            A cyber-physical digital twin platform for smart grid cybersecurity research, enabling realistic cyberattack simulation, resilience evaluation, and AI-assisted decision support.
          </p>
          <div style={s.heroCtas}>
            <button style={s.btnLarge} onClick={() => onNavigate('register')}>
              🚀 Start Free — No Credit Card
            </button>
            <button style={s.btnLargeOutline} onClick={() => onNavigate('demo')}>
              ▶ Watch Demo
            </button>
          </div>
          <p style={{ fontSize: 13, color: '#475569', marginTop: 24 }}>
            Developed for Smart Grid Cybersecurity Research
          </p>
        </div>
      </section>

      {/* Stats */}
      <div style={s.stats}>
        {[['500+', 'Attack Scenarios'], ['99.9%', 'Uptime SLA'], ['50+', 'Institutions'], ['IEEE', 'Certified']].map(([num, label]) => (
          <div key={label} style={s.stat}>
            <div style={s.statNum}>{num}</div>
            <div style={s.statLabel}>{label}</div>
          </div>
        ))}
      </div>

      {/* Features */}
      <section id="features" style={{ background: '#0a0e1a' }}>
        <div style={s.section}>
          <div style={s.sectionTag}>Platform Capabilities</div>
          <h2 style={s.sectionTitle}>Everything your research needs</h2>
          <p style={s.sectionSub}>
            Purpose-built for smart grid cybersecurity research. From digital twin simulation
            to blockchain-verified telemetry — all in one platform.
          </p>
          <div style={s.featureGrid}>
            {FEATURES.map((f) => (
              <div
                key={f.title}
                style={{ ...s.featureCard, borderColor: `rgba(${f.accent === '#6366f1' ? '99,102,241' : f.accent === '#8b5cf6' ? '139,92,246' : f.accent === '#06b6d4' ? '6,182,212' : f.accent === '#10b981' ? '16,185,129' : f.accent === '#f59e0b' ? '245,158,11' : '239,68,68'},0.15)` }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-4px)'; (e.currentTarget as HTMLElement).style.boxShadow = `0 12px 40px rgba(0,0,0,0.4)`; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = ''; (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
              >
                <div style={s.featureIcon}>{f.icon}</div>
                <div style={{ ...s.featureTitle, color: f.accent }}>{f.title}</div>
                <div style={s.featureDesc}>{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section style={{ background: 'rgba(99,102,241,0.04)', borderTop: '1px solid rgba(99,102,241,0.1)', borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
        <div style={s.section}>
          <div style={s.sectionTag}>Simple Workflow</div>
          <h2 style={s.sectionTitle}>From sign-up to simulation in minutes</h2>
          <div style={s.steps}>
            {[
              { num: '1', title: 'Create Account', desc: 'Register with your institution email. Verify and select your plan — Free plan requires no credit card.' },
              { num: '2', title: 'Configure Grid', desc: 'Choose IEEE topology (14/39/57/118-bus). Set load profiles, generation, and protection settings.' },
              { num: '3', title: 'Select Attack', desc: 'Browse 500+ MITRE ATT&CK scenarios or create custom attack sequences in the scenario editor.' },
              { num: '4', title: 'Analyze Results', desc: 'Review live telemetry, resilience score, system verdict, and AI-generated research insights.' },
            ].map((step) => (
              <div key={step.num} style={s.step}>
                <div style={s.stepNum}>{step.num}</div>
                <div style={s.stepTitle}>{step.title}</div>
                <div style={s.stepDesc}>{step.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section style={{ background: '#0a0e1a' }}>
        <div style={s.section}>
          <div style={s.sectionTag}>Testimonials</div>
          <h2 style={s.sectionTitle}>Trusted by grid security researchers</h2>
          <div style={s.testimonialGrid}>
            {TESTIMONIALS.map((t) => (
              <div key={t.name} style={s.testimonialCard}>
                <p style={s.quote}>"{t.text}"</p>
                <div style={s.author}>
                  <div style={{ ...s.avatar, background: `linear-gradient(135deg, ${t.color}, ${t.color}88)` }}>{t.initials}</div>
                  <div>
                    <div style={s.authorName}>{t.name}</div>
                    <div style={s.authorRole}>{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{ background: 'linear-gradient(180deg, #0a0e1a 0%, #0d1117 100%)' }}>
        <div style={s.section}>
          <div style={s.sectionTag}>Pricing</div>
          <h2 style={s.sectionTitle}>Transparent, research-first pricing</h2>
          <p style={s.sectionSub}>All prices in Malaysian Ringgit (RM). Cancel anytime.</p>
          <div style={s.planGrid}>
            {PLANS.map((plan) => (
              <div
                key={plan.tier}
                style={{
                  ...s.planCard,
                  border: plan.badge === 'Popular' ? '2px solid #6366f1' : plan.badge === 'Best Value' ? '2px solid #8b5cf6' : '1px solid #1e293b',
                  boxShadow: plan.badge === 'Popular' ? '0 0 40px rgba(99,102,241,0.2)' : 'none',
                }}
              >
                {plan.badge && (
                  <div style={{ ...s.planBadge, background: `${plan.color}22`, color: plan.color, border: `1px solid ${plan.color}44` }}>
                    {plan.badge}
                  </div>
                )}
                <div style={s.planName}>{plan.name}</div>
                <div style={s.planPrice}>
                  {plan.price === null ? (
                    <span style={{ fontSize: 28 }}>Custom</span>
                  ) : (
                    <>
                      {plan.price === 0 ? 'Free' : <>RM{plan.price}</>}
                    </>
                  )}
                </div>
                <div style={s.planBilling}>{plan.price === null ? 'Contact us' : plan.price === 0 ? 'No credit card' : plan.billing}</div>
                <ul style={s.planFeatures}>
                  {plan.features.map((f) => (
                    <li key={f} style={s.planFeatureItem}>
                      <span style={s.check}>✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button
                  style={{
                    padding: '12px', borderRadius: 10, width: '100%', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    background: plan.badge === 'Popular' ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : plan.badge === 'Best Value' ? 'linear-gradient(135deg, #8b5cf6, #6366f1)' : 'transparent',
                    color: plan.badge ? '#fff' : '#94a3b8',
                    border: plan.badge ? 'none' : '1px solid #1e293b',
                    transition: 'all 0.2s',
                  }}
                  onClick={() => {
                    if (plan.ctaAction === 'enterprise_contact') {
                      window.location.href = 'mailto:enterprise@pypygrid.com';
                    } else {
                      onNavigate('register');
                    }
                  }}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" style={{ background: '#0a0e1a' }}>
        <div style={s.section}>
          <div style={s.sectionTag}>FAQ</div>
          <h2 style={s.sectionTitle}>Frequently asked questions</h2>
          <div style={s.faqList}>
            {FAQS.map((faq, i) => (
              <div key={i} style={s.faqItem}>
                <div style={s.faqQ} onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                  <span>{faq.q}</span>
                  <span style={{ color: '#6366f1', transition: 'transform 0.2s', transform: openFaq === i ? 'rotate(45deg)' : 'none', fontSize: 20 }}>+</span>
                </div>
                {openFaq === i && <div style={s.faqA}>{faq.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <div style={{ padding: '0 32px' }}>
        <div style={s.ctaSection}>
          <h2 style={s.ctaTitle}>Ready to secure your grid?</h2>
          <p style={s.ctaSub}>Join 50+ institutions using PYPY Grid for critical infrastructure research.</p>
          <div style={s.ctaForm}>
            <input
              style={s.ctaInput}
              type="email"
              placeholder="Enter your institution email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button style={{ ...s.btnLarge, fontSize: 14, padding: '12px 24px' }} onClick={() => onNavigate('register')}>
              Start Free
            </button>
          </div>
          <p style={{ fontSize: 12, color: '#475569', marginTop: 16 }}>No credit card required · Free plan forever · Cancel anytime</p>
        </div>
      </div>

      {/* Footer */}
      <footer style={s.footer}>
        <div style={s.footerInner}>
          <div style={s.footerTop}>
            <div style={{ ...s.footerBrand }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#fff' }}>
                PYPY <span style={{ color: '#6366f1' }}>Grid</span>
              </div>
              <div style={s.footerTagline}>
                Protect Your Power, Protect Yourself. Smart grid cybersecurity research platform for the next generation of infrastructure defenders.
              </div>
            </div>
            {[
              { heading: 'Product', links: [['Features', 'features'], ['Pricing', 'pricing'], ['FAQ', 'faq'], ['Changelog', '#']] },
              { heading: 'Resources', links: [['User Guide', '#'], ['API Reference', '#'], ['Admin Guide', '#'], ['Research Papers', '#']] },
              { heading: 'Legal', links: [['Privacy Policy', '#'], ['Terms of Service', '#'], ['Cookie Policy', '#'], ['Academic License', '#']] },
              { heading: 'Company', links: [['About', '#'], ['Contact', '#'], ['GitHub', '#'], ['LinkedIn', '#']] },
            ].map((col) => (
              <div key={col.heading}>
                <div style={s.footerHeading}>{col.heading}</div>
                <div style={s.footerLinks}>
                  {col.links.map(([label, href]) => (
                    <button key={label} style={s.footerLink}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#818cf8'; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = '#64748b'; }}
                      onClick={() => href.startsWith('#') && href.length > 1 ? scrollTo(href.slice(1)) : null}
                    >{label}</button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div style={s.footerBottom}>
            <div style={s.footerCopy}>
              © 2026 PYPY Grid. All rights reserved. Made in Malaysia 🇲🇾
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              {['Privacy', 'Terms', 'Cookies'].map((l) => (
                <span key={l} style={{ fontSize: 12, color: '#334155', cursor: 'pointer' }}>{l}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
