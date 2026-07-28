// dashboard/src/BrandingConfig.ts
// PYPY Grid — Brand Configuration & Design Tokens V11.9

export const BRAND = {
  name: 'PYPY Grid',
  tagline: 'Protect Your Power, Protect Yourself',
  shortName: 'PYPY',
  version: '11.9',

  domain: 'pypygrid.com',
  appUrl: 'https://app.pypygrid.com',
  apiUrl: 'https://api.pypygrid.com',

  support_email: 'support@pypygrid.com',
  billing_email: 'billing@pypygrid.com',
  legal_email: 'legal@pypygrid.com',
  admin_email: 'admin@pypygrid.com',

  colors: {
    // Core brand
    primary: '#6366f1',       // Indigo
    primaryDark: '#4f46e5',
    primaryLight: '#818cf8',
    secondary: '#8b5cf6',     // Violet
    secondaryDark: '#7c3aed',
    accent: '#06b6d4',        // Cyan
    accentDark: '#0891b2',

    // Backgrounds
    bg: '#0a0e1a',
    bgDeep: '#050810',
    surface: '#111827',
    surfaceAlt: '#1e293b',
    surfaceBorder: '#334155',
    glass: 'rgba(17, 24, 39, 0.85)',

    // Text
    text: '#f8fafc',
    textSub: '#e2e8f0',
    textMuted: '#94a3b8',
    textDim: '#64748b',

    // Status
    success: '#10b981',
    successBg: 'rgba(16, 185, 129, 0.1)',
    warning: '#f59e0b',
    warningBg: 'rgba(245, 158, 11, 0.1)',
    danger: '#ef4444',
    dangerBg: 'rgba(239, 68, 68, 0.1)',
    info: '#3b82f6',
    infoBg: 'rgba(59, 130, 246, 0.1)',

    // Gradients
    gradientHero: 'linear-gradient(135deg, #1a1040 0%, #0f172a 50%, #0a0e1a 100%)',
    gradientCard: 'linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.05) 100%)',
    gradientPrimary: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    gradientAccent: 'linear-gradient(135deg, #06b6d4, #6366f1)',
  },

  fonts: {
    sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
    display: "'Inter', sans-serif",
  },

  borderRadius: {
    sm: '6px',
    md: '10px',
    lg: '16px',
    xl: '24px',
    full: '9999px',
  },

  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '40px',
    xxl: '64px',
  },

  shadows: {
    sm: '0 1px 3px rgba(0,0,0,0.4)',
    md: '0 4px 16px rgba(0,0,0,0.4)',
    lg: '0 8px 32px rgba(0,0,0,0.5)',
    glow: '0 0 30px rgba(99,102,241,0.3)',
    glowAccent: '0 0 30px rgba(6,182,212,0.2)',
  },

  pricing: {
    free: { amount: 0, currency: 'RM', label: 'Free', tier: 'free' },
    academic_premium: { amount: 19, currency: 'RM', label: 'Academic Premium', tier: 'academic_premium' },
    research_lab: { amount: 49, currency: 'RM', label: 'Research Lab', tier: 'research_lab' },
    enterprise: { amount: null, currency: 'RM', label: 'Enterprise', tier: 'enterprise' },
  },

  nav: {
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Pricing', href: '#pricing' },
      { label: 'FAQ', href: '#faq' },
      { label: 'Docs', href: 'https://docs.pypygrid.com' },
    ],
  },

  social: {
    github: 'https://github.com/pypygrid',
    linkedin: 'https://linkedin.com/company/pypygrid',
    twitter: 'https://twitter.com/pypygrid',
  },

  stats: {
    scenarios: '500+',
    uptime: '99.9%',
    institutions: '50+',
    buses: '4',
  },
} as const;

export type BrandColors = typeof BRAND.colors;
export type PricingTier = keyof typeof BRAND.pricing;

export default BRAND;
