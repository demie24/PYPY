"""
core/services/email/templates.py
PYPY V11.9 — Production Email Templates

All templates return: (subject: str, html: str, text: str)
Branded with PYPY Grid dark theme: #0a0e1a bg, #6366f1 accent, #e2e8f0 text.
"""

from typing import Tuple


# ─── Shared Layout ─────────────────────────────────────────────────────────────

def _base_email(title: str, content_html: str, preheader: str = "") -> Tuple[str, str, str]:
    """Wrap content in the standard PYPY Grid branded email shell."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
  <style>
    body {{ margin: 0; padding: 0; background-color: #0a0e1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    .email-wrapper {{ background-color: #0a0e1a; padding: 40px 20px; }}
    .email-container {{ max-width: 600px; margin: 0 auto; background: #111827; border-radius: 16px; overflow: hidden; border: 1px solid #1e293b; }}
    .email-header {{ background: linear-gradient(135deg, #1a1040 0%, #0f172a 50%, #0a0e1a 100%); padding: 32px 40px; text-align: center; border-bottom: 1px solid #6366f1; }}
    .brand-logo {{ font-size: 28px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }}
    .brand-logo span {{ color: #6366f1; }}
    .brand-tagline {{ font-size: 11px; color: #8b5cf6; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }}
    .email-body {{ padding: 40px; color: #e2e8f0; }}
    .email-title {{ font-size: 24px; font-weight: 700; color: #f8fafc; margin: 0 0 16px; line-height: 1.3; }}
    .email-text {{ font-size: 15px; color: #94a3b8; line-height: 1.7; margin: 0 0 20px; }}
    .cta-button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff !important; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 15px; font-weight: 600; margin: 16px 0; }}
    .info-box {{ background: #1e293b; border-left: 3px solid #6366f1; border-radius: 8px; padding: 16px 20px; margin: 20px 0; }}
    .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; font-size: 14px; }}
    .info-label {{ color: #64748b; }}
    .info-value {{ color: #e2e8f0; font-weight: 500; }}
    .divider {{ height: 1px; background: #1e293b; margin: 24px 0; }}
    .email-footer {{ background: #0d1117; padding: 24px 40px; text-align: center; border-top: 1px solid #1e293b; }}
    .footer-text {{ font-size: 12px; color: #475569; line-height: 1.6; }}
    .footer-links {{ margin: 8px 0; }}
    .footer-links a {{ color: #6366f1; text-decoration: none; margin: 0 8px; font-size: 12px; }}
    .badge {{ display: inline-block; background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; border: 1px solid rgba(99, 102, 241, 0.3); }}
  </style>
</head>
<body>
  <div class="email-wrapper">
    <div class="email-container">
      <div class="email-header">
        <div class="brand-logo">PYPY <span>Grid</span></div>
        <div class="brand-tagline">Protect Your Power, Protect Yourself</div>
      </div>
      <div class="email-body">
        {content_html}
      </div>
      <div class="email-footer">
        <div class="footer-links">
          <a href="https://pypygrid.com">Home</a>
          <a href="https://pypygrid.com/dashboard">Dashboard</a>
          <a href="https://pypygrid.com/legal/privacy">Privacy</a>
          <a href="https://pypygrid.com/legal/terms">Terms</a>
        </div>
        <div class="footer-text">
          &copy; 2026 PYPY Grid. All rights reserved.<br>
          Smart Grid Cybersecurity Research Platform &mdash; Malaysia &amp; Global<br>
          <a href="https://pypygrid.com/unsubscribe" style="color: #475569;">Unsubscribe</a>
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""
    return html


# ─── 1. Welcome Email ──────────────────────────────────────────────────────────

def welcome_email(first_name: str, platform_url: str) -> Tuple[str, str, str]:
    """Sent immediately after successful registration and email verification."""
    subject = f"Welcome to PYPY Grid, {first_name}! Your research platform is ready."
    content = f"""
      <h1 class="email-title">Welcome to PYPY Grid, {first_name}! 🎉</h1>
      <p class="email-text">
        Your account is ready. You now have access to the world's most advanced
        smart grid cybersecurity research and simulation platform.
      </p>
      <div class="info-box">
        <strong style="color:#e2e8f0; font-size: 14px;">What you can do now:</strong>
        <ul style="color: #94a3b8; margin: 12px 0 0; padding-left: 20px; line-height: 2;">
          <li>Launch IEEE 14/39/57/118-bus grid simulations</li>
          <li>Test 500+ cyberattack scenarios (MITRE ATT&CK ICS)</li>
          <li>Analyze resilience scores and system verdicts</li>
          <li>Use the AI Copilot for research assistance</li>
          <li>Collaborate with your institution on the Research Workspace</li>
        </ul>
      </div>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{platform_url}" class="cta-button">Launch PYPY Grid Dashboard &rarr;</a>
      </p>
      <p class="email-text" style="font-size: 13px;">
        Need help getting started? Read our
        <a href="https://pypygrid.com/docs/user-guide" style="color: #6366f1;">User Guide</a>
        or reach out at
        <a href="mailto:support@pypygrid.com" style="color: #6366f1;">support@pypygrid.com</a>.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Welcome to PYPY Grid, {first_name}!\n\n"
        "Your account is ready. Launch your dashboard at:\n"
        f"{platform_url}\n\n"
        "What you can do now:\n"
        "- Launch IEEE 14/39/57/118-bus grid simulations\n"
        "- Test 500+ cyberattack scenarios\n"
        "- Use the AI Copilot for research\n\n"
        "Support: support@pypygrid.com\n"
        "PYPY Grid — Protect Your Power, Protect Yourself"
    )
    return subject, html, text


# ─── 2. Verify Email ───────────────────────────────────────────────────────────

def verify_email(first_name: str, verify_url: str) -> Tuple[str, str, str]:
    """Sent when user registers — requires email verification before login."""
    subject = "Verify your PYPY Grid email address"
    content = f"""
      <h1 class="email-title">Verify your email address</h1>
      <p class="email-text">
        Hi {first_name}, thank you for registering with PYPY Grid.
        Please verify your email address to activate your account and start your research.
      </p>
      <p class="email-text">
        Click the button below. This verification link expires in <strong style="color: #f8fafc;">24 hours</strong>.
      </p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{verify_url}" class="cta-button">Verify Email Address &rarr;</a>
      </p>
      <div class="info-box">
        <p style="margin: 0; font-size: 13px; color: #64748b;">
          If you can't click the button, copy and paste this URL into your browser:<br>
          <span style="color: #6366f1; word-break: break-all;">{verify_url}</span>
        </p>
      </div>
      <p class="email-text" style="font-size: 13px;">
        If you didn't create a PYPY Grid account, please ignore this email.
        No account will be created without verification.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        "Please verify your PYPY Grid email address by visiting:\n"
        f"{verify_url}\n\n"
        "This link expires in 24 hours.\n\n"
        "If you didn't register, please ignore this email.\n"
        "PYPY Grid — support@pypygrid.com"
    )
    return subject, html, text


# ─── 3. Reset Password ─────────────────────────────────────────────────────────

def reset_password(first_name: str, reset_url: str) -> Tuple[str, str, str]:
    """Sent when user requests a password reset."""
    subject = "Reset your PYPY Grid password"
    content = f"""
      <h1 class="email-title">Password Reset Request</h1>
      <p class="email-text">
        Hi {first_name}, we received a request to reset the password for your PYPY Grid account.
        Click the button below to create a new password.
      </p>
      <p class="email-text">
        This reset link expires in <strong style="color: #f8fafc;">2 hours</strong>.
      </p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" class="cta-button">Reset Password &rarr;</a>
      </p>
      <div class="info-box">
        <p style="margin: 0; font-size: 13px; color: #64748b;">
          Copy this URL if the button doesn't work:<br>
          <span style="color: #6366f1; word-break: break-all;">{reset_url}</span>
        </p>
      </div>
      <p class="email-text" style="font-size: 13px; color: #ef4444;">
        ⚠️ If you did not request a password reset, please ignore this email.
        Your password will not change. Consider securing your account if you believe
        someone may have access to your email.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        "You requested a password reset for your PYPY Grid account.\n\n"
        "Reset your password here:\n"
        f"{reset_url}\n\n"
        "This link expires in 2 hours.\n\n"
        "If you did not request this, please ignore this email.\n"
        "PYPY Grid — support@pypygrid.com"
    )
    return subject, html, text


# ─── 4. Subscription Activated ────────────────────────────────────────────────

def subscription_activated(first_name: str, plan_name: str, expires_at: str) -> Tuple[str, str, str]:
    """Sent when a subscription payment is confirmed and plan is activated."""
    subject = f"Your PYPY Grid {plan_name} subscription is now active!"
    content = f"""
      <h1 class="email-title">Subscription Activated! 🚀</h1>
      <p class="email-text">
        Hi {first_name}, your <strong style="color: #818cf8;">{plan_name}</strong> subscription
        has been successfully activated. You now have full access to all features in your plan.
      </p>
      <div class="info-box">
        <div class="info-row">
          <span class="info-label">Plan</span>
          <span class="info-value"><span class="badge">{plan_name}</span></span>
        </div>
        <div class="info-row">
          <span class="info-label">Status</span>
          <span class="info-value" style="color: #10b981;">&#10003; Active</span>
        </div>
        <div class="info-row" style="border-bottom: none;">
          <span class="info-label">Valid Until</span>
          <span class="info-value">{expires_at}</span>
        </div>
      </div>
      <p style="text-align: center; margin: 32px 0;">
        <a href="https://pypygrid.com/dashboard" class="cta-button">Go to Dashboard &rarr;</a>
      </p>
      <p class="email-text" style="font-size: 13px;">
        For billing questions, contact
        <a href="mailto:billing@pypygrid.com" style="color: #6366f1;">billing@pypygrid.com</a>.
        Your invoice is available in the dashboard under Settings &rarr; Billing.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        f"Your PYPY Grid {plan_name} subscription is now ACTIVE.\n\n"
        f"Valid Until: {expires_at}\n\n"
        "Access your dashboard at: https://pypygrid.com/dashboard\n\n"
        "Billing questions: billing@pypygrid.com\n"
        "PYPY Grid — Protect Your Power, Protect Yourself"
    )
    return subject, html, text


# ─── 5. Subscription Expiring ─────────────────────────────────────────────────

def subscription_expiring(
    first_name: str, plan_name: str, days_remaining: int, renew_url: str
) -> Tuple[str, str, str]:
    """Sent 7 days and 1 day before subscription expires."""
    urgency = "⚠️ Urgent: " if days_remaining <= 1 else ""
    subject = f"{urgency}Your PYPY Grid {plan_name} subscription expires in {days_remaining} day{'s' if days_remaining > 1 else ''}"
    accent_color = "#ef4444" if days_remaining <= 1 else "#f59e0b"
    content = f"""
      <h1 class="email-title">Your subscription expires soon</h1>
      <p class="email-text">
        Hi {first_name}, your <strong style="color: #818cf8;">{plan_name}</strong> subscription
        will expire in <strong style="color: {accent_color};">{days_remaining} day{'s' if days_remaining > 1 else ''}</strong>.
      </p>
      <p class="email-text">
        Renew now to keep uninterrupted access to your simulations, experiments, and research data.
        Your data will be preserved for 30 days after expiry before archival.
      </p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{renew_url}" class="cta-button">Renew Subscription &rarr;</a>
      </p>
      <div class="info-box">
        <p style="margin: 0; font-size: 13px; color: #94a3b8;">
          If you choose not to renew, your account will revert to the Free tier.
          Active experiments will be archived and accessible for 30 days.
        </p>
      </div>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        f"Your PYPY Grid {plan_name} subscription expires in {days_remaining} day(s).\n\n"
        f"Renew at: {renew_url}\n\n"
        "Your data is preserved for 30 days after expiry.\n"
        "PYPY Grid — support@pypygrid.com"
    )
    return subject, html, text


# ─── 6. Invoice Email ─────────────────────────────────────────────────────────

def invoice_email(
    first_name: str,
    invoice_id: str,
    amount: float,
    plan_name: str,
    period: str,
    pay_date: str,
) -> Tuple[str, str, str]:
    """Sent after successful payment with invoice details."""
    subject = f"PYPY Grid Invoice {invoice_id} — RM {amount:.2f}"
    content = f"""
      <h1 class="email-title">Payment Invoice</h1>
      <p class="email-text">Hi {first_name}, thank you for your payment. Your invoice is below.</p>
      <div class="info-box">
        <div class="info-row">
          <span class="info-label">Invoice Number</span>
          <span class="info-value" style="font-family: monospace;">{invoice_id}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Plan</span>
          <span class="info-value"><span class="badge">{plan_name}</span></span>
        </div>
        <div class="info-row">
          <span class="info-label">Billing Period</span>
          <span class="info-value">{period}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Payment Date</span>
          <span class="info-value">{pay_date}</span>
        </div>
        <div class="info-row" style="border-bottom: none; padding-top: 12px; margin-top: 4px; border-top: 1px solid #334155;">
          <span class="info-label" style="font-weight: 600; color: #e2e8f0; font-size: 15px;">Total Paid</span>
          <span class="info-value" style="font-size: 18px; font-weight: 700; color: #10b981;">RM {amount:.2f}</span>
        </div>
      </div>
      <p style="text-align: center; margin: 32px 0;">
        <a href="https://pypygrid.com/settings/billing" class="cta-button">View Billing History &rarr;</a>
      </p>
      <p class="email-text" style="font-size: 13px;">
        This invoice is for your records. For tax purposes, please retain this email.
        Questions? Contact <a href="mailto:billing@pypygrid.com" style="color: #6366f1;">billing@pypygrid.com</a>.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        f"PYPY Grid Invoice: {invoice_id}\n"
        f"Plan: {plan_name}\n"
        f"Period: {period}\n"
        f"Date: {pay_date}\n"
        f"Amount: RM {amount:.2f}\n\n"
        "View billing history: https://pypygrid.com/settings/billing\n"
        "Questions: billing@pypygrid.com\n"
        "PYPY Grid"
    )
    return subject, html, text


# ─── 7. Backup Completed ──────────────────────────────────────────────────────

def backup_completed(
    first_name: str, backup_filename: str, size_mb: float, backup_date: str
) -> Tuple[str, str, str]:
    """Sent after automated backup completes successfully."""
    subject = f"[PYPY Grid] Backup completed — {backup_date}"
    content = f"""
      <h1 class="email-title">✅ Backup Completed Successfully</h1>
      <p class="email-text">
        Hi {first_name}, your scheduled PYPY Grid data backup has completed successfully.
        Your research data is safely archived.
      </p>
      <div class="info-box">
        <div class="info-row">
          <span class="info-label">Backup File</span>
          <span class="info-value" style="font-family: monospace; font-size: 12px;">{backup_filename}</span>
        </div>
        <div class="info-row">
          <span class="info-label">File Size</span>
          <span class="info-value">{size_mb:.1f} MB</span>
        </div>
        <div class="info-row" style="border-bottom: none;">
          <span class="info-label">Backup Date</span>
          <span class="info-value">{backup_date}</span>
        </div>
      </div>
      <p style="text-align: center; margin: 32px 0;">
        <a href="https://pypygrid.com/admin/operations" class="cta-button">View Operations Center &rarr;</a>
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        "PYPY Grid Backup Completed:\n"
        f"File: {backup_filename}\n"
        f"Size: {size_mb:.1f} MB\n"
        f"Date: {backup_date}\n\n"
        "View at: https://pypygrid.com/admin/operations\n"
        "PYPY Grid"
    )
    return subject, html, text


# ─── 8. Simulation Finished ───────────────────────────────────────────────────

def simulation_finished(
    first_name: str,
    scenario_name: str,
    verdict: str,
    resilience_score: float,
    run_id: str,
) -> Tuple[str, str, str]:
    """Sent when a long-running simulation completes."""
    verdict_colors = {
        "NOMINAL": "#10b981",
        "DEGRADED": "#f59e0b",
        "CRITICAL": "#ef4444",
        "FAILED": "#dc2626",
    }
    color = verdict_colors.get(verdict.upper(), "#6366f1")
    emoji = {"NOMINAL": "✅", "DEGRADED": "⚠️", "CRITICAL": "🔴", "FAILED": "❌"}.get(verdict.upper(), "🔬")
    subject = f"[PYPY Grid] Simulation complete — {scenario_name} | Score: {resilience_score:.1f}"
    content = f"""
      <h1 class="email-title">{emoji} Simulation Complete</h1>
      <p class="email-text">
        Hi {first_name}, your grid simulation has finished. Here are the results:
      </p>
      <div class="info-box">
        <div class="info-row">
          <span class="info-label">Scenario</span>
          <span class="info-value">{scenario_name}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Resilience Score</span>
          <span class="info-value" style="font-size: 20px; font-weight: 700; color: {color};">{resilience_score:.1f}<span style="font-size: 13px; color: #64748b;">/100</span></span>
        </div>
        <div class="info-row">
          <span class="info-label">System Verdict</span>
          <span class="info-value" style="color: {color}; font-weight: 700;">{verdict}</span>
        </div>
        <div class="info-row" style="border-bottom: none;">
          <span class="info-label">Run ID</span>
          <span class="info-value" style="font-family: monospace; font-size: 12px;">{run_id}</span>
        </div>
      </div>
      <p style="text-align: center; margin: 32px 0;">
        <a href="https://pypygrid.com/dashboard?run={run_id}" class="cta-button">View Full Results &rarr;</a>
      </p>
      <p class="email-text" style="font-size: 13px;">
        Use the AI Copilot to analyze these results and generate a research summary automatically.
      </p>
    """
    html = _base_email(subject, content)
    text = (
        f"Hi {first_name},\n\n"
        "Your PYPY Grid simulation is complete:\n"
        f"Scenario: {scenario_name}\n"
        f"Resilience Score: {resilience_score:.1f}/100\n"
        f"Verdict: {verdict}\n"
        f"Run ID: {run_id}\n\n"
        f"View results: https://pypygrid.com/dashboard?run={run_id}\n"
        "PYPY Grid"
    )
    return subject, html, text
