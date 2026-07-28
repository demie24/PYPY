# Privacy Policy

**PYPY Grid — Smart Grid Cybersecurity Research Platform**
**Effective Date:** 1 July 2026
**Last Updated:** 1 July 2026
**Version:** 3.1

---

## 1. Introduction and Identity of the Data Controller

Welcome to PYPY Grid, the Smart Grid Cybersecurity Research Platform operated by **PYPY Grid Sdn. Bhd.** ("we", "us", "our", or "the Company"), a company incorporated under the laws of Malaysia. Our registered address is available upon request at legal@pypygrid.com.

PYPY Grid is accessible at **https://pypygrid.com** and its subdomains, including **https://app.pypygrid.com** and **https://api.pypygrid.com** (collectively, the "Platform"). This Privacy Policy governs how we collect, use, disclose, store, and protect personal data in connection with your use of the Platform.

By accessing or using PYPY Grid, you acknowledge that you have read, understood, and agree to the practices described in this Privacy Policy. If you do not agree with any part of this Policy, you must discontinue use of the Platform immediately.

This Privacy Policy is drafted in compliance with:
- Malaysia's **Personal Data Protection Act 2010 (PDPA 2010)** and its subsidiary regulations;
- The European Union's **General Data Protection Regulation (EU) 2016/679 (GDPR)**;
- The **UK GDPR** (for users in the United Kingdom); and
- All other applicable privacy and data protection laws in jurisdictions where we operate.

---

## 2. Data We Collect

We collect personal data through various means when you interact with the Platform. The categories of personal data we process include:

### 2.1 Account and Identity Data
- Full name
- Email address
- Username (handle)
- Password (stored in hashed, salted form using bcrypt — never in plaintext)
- Profile picture (if uploaded)
- Institutional or organisational affiliation (for Academic and Research Lab plans)
- Country of residence
- Role/job title (optional, for research profiling)

### 2.2 Subscription and Billing Data
- Subscription plan (Free, Academic Premium, Research Lab, or Enterprise)
- Payment method type (e.g., credit card last 4 digits, FPX bank selection)
- Billing address
- Invoice history and transaction identifiers
- Payment processor tokens (handled by Stripe or ToyyibPay — we do not store raw card details)

### 2.3 Research and Usage Data
- Experiments created, including topology selection, attack scenario configuration, and simulation parameters
- Simulation run history, results, resilience scores, and AI-generated analysis
- Saved research workspaces and scenario configurations
- Downloaded reports and exported datasets
- AI Copilot queries and conversation history
- Scenario Marketplace interactions (published, purchased, or downloaded scenarios)

### 2.4 Technical and Device Data
- IP address
- Browser type and version
- Operating system
- Device type and screen resolution
- Session tokens and cookies
- Referral URL
- Timestamps of access and actions
- API access logs (endpoint, method, response code, latency)

### 2.5 Communication Data
- Support ticket content and correspondence
- Email communications with the PYPY Grid team
- Notification preferences

### 2.6 Cookies and Tracking Data
Please refer to our separate **Cookie Policy** for detailed information on the types of cookies we use, their purpose, and how you can control them.

---

## 3. How We Collect Personal Data

We collect personal data through:

- **Direct collection:** Information you provide during registration, subscription checkout, profile updates, experiment configuration, and support requests.
- **Automated collection:** Server logs, cookies, and analytics tools that automatically capture technical data when you use the Platform.
- **Third-party sources:** Identity verification information from OAuth providers (Google SSO) if you choose social login; payment status updates from Stripe or ToyyibPay.
- **Institutional onboarding:** For Enterprise and Academic Institution accounts, your institution's administrator may provide your account details to us.

---

## 4. Purposes and Legal Basis for Processing

We process your personal data for the following purposes, each supported by a lawful basis under GDPR and PDPA 2010:

| Purpose | Legal Basis (GDPR) | PDPA Basis |
|---|---|---|
| Account creation and authentication | Performance of contract | Consent / Contractual necessity |
| Providing simulation and research services | Performance of contract | Contractual necessity |
| Processing subscription payments | Performance of contract | Contractual necessity |
| Sending transactional emails (receipts, alerts) | Performance of contract | Contractual necessity |
| Platform security and fraud prevention | Legitimate interests | Security purposes |
| Product improvement and analytics | Legitimate interests | Legitimate purposes |
| Marketing communications (opt-in only) | Consent | Consent |
| Responding to support queries | Performance of contract / Legitimate interests | Contractual necessity |
| Compliance with legal obligations | Legal obligation | Legal obligation |
| Academic research partnership management | Legitimate interests | Consent |

You may withdraw consent for marketing communications at any time by clicking "Unsubscribe" in any marketing email or by updating your notification preferences in Account Settings.

---

## 5. Data Retention

We retain personal data only for as long as necessary to fulfil the purposes for which it was collected, or as required by applicable law:

- **Active account data:** Retained throughout the duration of your account and subscription.
- **Simulation data and research outputs:** Retained for 24 months from the date of creation for Free plan users; indefinitely (or as configured) for paying subscribers.
- **Billing and financial records:** Retained for **7 years** in accordance with Malaysian financial record-keeping requirements.
- **Server and access logs:** Retained for **90 days** for security auditing purposes.
- **AI Copilot conversation history:** Retained for **12 months** from last interaction, after which it is anonymised or deleted.
- **Deleted accounts:** Upon account deletion request, personal data is anonymised or purged within **30 days**, subject to legal hold obligations.
- **Support tickets:** Retained for **3 years** from ticket resolution.

---

## 6. Disclosure of Personal Data to Third Parties

We do not sell, rent, or trade your personal data. We disclose data to third parties only under the following circumstances:

### 6.1 Service Providers (Data Processors)
We engage trusted third-party processors who handle data strictly on our behalf and under contractual data processing agreements:

- **Stripe, Inc.** (United States) — Payment processing for international subscriptions. Stripe is PCI-DSS Level 1 certified. Stripe's Privacy Policy: https://stripe.com/privacy
- **ToyyibPay Sdn. Bhd.** (Malaysia) — Payment processing for Malaysian subscribers (FPX, online banking). ToyyibPay's Privacy Policy: https://toyyibpay.com/privacy
- **SendGrid (Twilio Inc.)** (United States) — Transactional and marketing email delivery. SendGrid's Privacy Policy: https://www.twilio.com/en-us/legal/privacy
- **Redis Cloud / Upstash** — Session caching and real-time data streaming.
- **PostgreSQL hosting provider** — Database hosting on secure, encrypted servers.
- **Grafana Labs** — Internal platform monitoring (no customer PII is shared).

### 6.2 Academic and Institutional Partners
If you access PYPY Grid under an institutional licence, your institution's designated administrators may have access to your account status, simulation activity reports, and billing information relevant to the institutional account.

### 6.3 Legal and Regulatory Disclosures
We may disclose personal data to law enforcement agencies, regulators, courts, or other authorities when:
- Required by Malaysian law (e.g., under the PDPA 2010, Communications and Multimedia Act 1998, or court order);
- Required by applicable EU or international law;
- Necessary to protect the rights, property, or safety of PYPY Grid, its users, or the public.

### 6.4 Business Transfers
In the event of a merger, acquisition, sale of assets, or restructuring, personal data may be transferred to the successor entity, provided that the successor is bound by equivalent data protection obligations. We will notify affected users prior to such a transfer.

---

## 7. International Data Transfers

PYPY Grid is headquartered in Malaysia. Some of our third-party processors are located in the United States or European Union. When personal data is transferred outside of Malaysia or the European Economic Area (EEA), we ensure that appropriate safeguards are in place, including:

- **Standard Contractual Clauses (SCCs)** approved by the European Commission;
- **Adequacy decisions** from the European Commission where applicable;
- **Data Processing Agreements (DPAs)** with all processors containing appropriate transfer mechanisms.

Users in the EU/EEA may request a copy of the applicable transfer safeguards by contacting us at legal@pypygrid.com.

---

## 8. Data Security

We implement appropriate technical and organisational measures to protect your personal data against unauthorised access, disclosure, alteration, or destruction. These measures include:

- **Encryption at rest:** All database data is encrypted using AES-256.
- **Encryption in transit:** All communications use TLS 1.2 or TLS 1.3.
- **Authentication security:** Passwords are hashed using bcrypt with a minimum cost factor of 12; multi-factor authentication (MFA) is available.
- **Access controls:** Role-based access control (RBAC) ensures only authorised personnel access personal data.
- **Infrastructure security:** Firewalled server environments, regular security patching, and intrusion detection.
- **Regular security audits:** Annual penetration testing and quarterly vulnerability assessments.
- **Incident response plan:** We maintain a documented incident response procedure. In the event of a data breach that poses high risk to users, we will notify affected users and relevant authorities within **72 hours** as required under GDPR.

No system is 100% secure. We encourage users to use strong, unique passwords and to enable MFA.

---

## 9. Your Rights as a Data Subject

### 9.1 Rights Under GDPR (EU/EEA Users)
If you are in the European Economic Area, you have the following rights:
- **Right of access (Art. 15):** Request a copy of your personal data.
- **Right to rectification (Art. 16):** Correct inaccurate or incomplete data.
- **Right to erasure / "Right to be Forgotten" (Art. 17):** Request deletion of your personal data (subject to legal retention obligations).
- **Right to restriction of processing (Art. 18):** Limit how we use your data in certain circumstances.
- **Right to data portability (Art. 20):** Receive your data in a structured, machine-readable format.
- **Right to object (Art. 21):** Object to processing based on legitimate interests or direct marketing.
- **Rights regarding automated decision-making (Art. 22):** Not to be subject to solely automated decisions with legal effects.
- **Right to withdraw consent:** At any time, where processing is based on consent.

### 9.2 Rights Under PDPA 2010 (Malaysian Users)
Under Malaysia's PDPA 2010, you have the right to:
- **Access** personal data we hold about you;
- **Correct** inaccurate, incomplete, misleading, or out-of-date personal data;
- **Withdraw consent** to the processing of your personal data;
- **Opt out** of receiving direct marketing communications.

### 9.3 How to Exercise Your Rights
Submit requests to: **legal@pypygrid.com**
We will respond within **30 days** (extendable to 60 days for complex requests with notice).
Identity verification may be required before processing sensitive requests.

---

## 10. Cookies

We use cookies and similar tracking technologies on the Platform. For detailed information, see our **[Cookie Policy](cookie_policy.md)**.

---

## 11. Children's Privacy

PYPY Grid is not directed at children under the age of 18. We do not knowingly collect personal data from individuals under 18. If you believe a minor has provided personal data to us, contact us at legal@pypygrid.com and we will promptly delete it.

---

## 12. Links to Third-Party Websites

The Platform may contain links to external websites. We are not responsible for the privacy practices of third-party websites. We encourage you to review the privacy policies of any external sites you visit.

---

## 13. Changes to This Privacy Policy

We may update this Privacy Policy from time to time to reflect changes in our practices, technology, legal requirements, or other factors. We will:
- Notify registered users by email of material changes at least **14 days** before they take effect;
- Post the updated Policy on the Platform with a revised "Last Updated" date;
- For significant changes, request renewed consent where required by applicable law.

Continued use of the Platform after the effective date of any change constitutes your acceptance of the updated Policy.

---

## 14. Data Protection Officer and Contact Information

For any questions, concerns, or requests regarding this Privacy Policy or our data processing practices, please contact:

**PYPY Grid — Data Protection Officer**
Email: **legal@pypygrid.com**
Website: **https://pypygrid.com/privacy**

For EU/EEA users, if you believe we have not adequately addressed your concern, you have the right to lodge a complaint with your local data protection supervisory authority (e.g., the Information Commissioner's Office in the UK, or the relevant national DPA in your EU member state).

For Malaysian users, complaints may be directed to the **Department of Personal Data Protection Malaysia (JPDP)**: https://www.pdp.gov.my/

---

## 15. Governing Law

This Privacy Policy is governed by and construed in accordance with the laws of **Malaysia**, including the Personal Data Protection Act 2010, without prejudice to your statutory rights under GDPR if you are an EU/EEA resident.

---

*PYPY Grid Sdn. Bhd. | pypygrid.com | legal@pypygrid.com*
*© 2026 PYPY Grid Sdn. Bhd. All rights reserved.*
