# Official sources by region

A starting point for the `compliance` and `decide` skills, checked in November 2026. Laws, numbers and agencies
change: open the official site and check the current text and its date before citing anything. This is not legal
advice. Read only the rows of the project's jurisdictions (CLAUDE.md, section 2).

## How to use it
1. List every jurisdiction that applies: where the owner is, where the users are, where the data is stored and
   processed, where the hosting provider is established.
2. For each one, read the primary text on the official legislation site, then the regulator's guidance.
3. When rules from two jurisdictions differ, follow the stricter one where possible and open a question (`Q-nn`)
   for an expert where it is not.

## Privacy, data, AI and online services

| Region | Texts to check first | Primary texts | Regulators and official guidance |
|---|---|---|---|
| European Union | GDPR (Regulation (EU) 2016/679), AI Act (Regulation (EU) 2024/1689), Digital Services Act (Regulation (EU) 2022/2065), Cyber Resilience Act (Regulation (EU) 2024/2847), NIS2 (Directive (EU) 2022/2555), ePrivacy Directive (2002/58/EC), European Accessibility Act (Directive (EU) 2019/882) | eur-lex.europa.eu | EDPB (edpb.europa.eu, lists every national authority), ENISA (enisa.europa.eu), European Commission (digital-strategy.ec.europa.eu) |
| France | Loi Informatique et Libertés (loi n° 78-17), LCEN, RGAA for accessibility | legifrance.gouv.fr | CNIL (cnil.fr), ANSSI (cyber.gouv.fr), Arcom (arcom.fr), accessibilite.numerique.gouv.fr |
| United Kingdom | UK GDPR and Data Protection Act 2018, PECR, Online Safety Act 2023 | legislation.gov.uk | ICO (ico.org.uk), Ofcom (ofcom.org.uk) |
| Switzerland | Federal Act on Data Protection (FADP) | fedlex.admin.ch | FDPIC (edoeb.admin.ch) |
| United States | No general federal privacy law: FTC Act section 5, COPPA, HIPAA (health), GLBA (finance), state laws such as California's CCPA/CPRA; NIST AI RMF and Cybersecurity Framework (voluntary) | congress.gov, ecfr.gov, each state legislature | FTC (ftc.gov), California Privacy Protection Agency (cppa.ca.gov), state attorneys general, NIST (nist.gov) |
| Canada | PIPEDA, Quebec Law 25, provincial laws | laws-lois.justice.gc.ca | OPC (priv.gc.ca), Commission d'accès à l'information du Québec (cai.gouv.qc.ca) |
| Brazil | LGPD (Lei nº 13.709/2018) | planalto.gov.br | ANPD (gov.br/anpd) |
| Japan | Act on the Protection of Personal Information (APPI) | elaws.e-gov.go.jp | Personal Information Protection Commission (ppc.go.jp) |
| South Korea | Personal Information Protection Act (PIPA) | law.go.kr | PIPC (pipc.go.kr) |
| China | Personal Information Protection Law, Data Security Law, Cybersecurity Law | npc.gov.cn | Cyberspace Administration of China (cac.gov.cn) |
| India | Digital Personal Data Protection Act, 2023 | indiacode.nic.in | MeitY (meity.gov.in) |
| Singapore | Personal Data Protection Act 2012 | sso.agc.gov.sg | PDPC (pdpc.gov.sg) |
| Australia | Privacy Act 1988 | legislation.gov.au | OAIC (oaic.gov.au) |
| New Zealand | Privacy Act 2020 | legislation.govt.nz | Privacy Commissioner (privacy.org.nz) |
| South Africa | POPIA | gov.za | Information Regulator (inforegulator.org.za) |
| Nigeria | Nigeria Data Protection Act 2023 | official gazette | NDPC (ndpc.gov.ng) |
| Kenya | Data Protection Act 2019 | kenyalaw.org | ODPC (odpc.go.ke) |
| Anywhere else | The national data protection or consumer law | the country's official legislation site | the national data protection authority, found on an official government site |

## International standards (any region)
- Security and privacy management: ISO/IEC 27001, ISO/IEC 27701; AI management: ISO/IEC 42001.
- Application security: OWASP ASVS and OWASP Top 10 (owasp.org); NIST Secure Software Development Framework.
- Accessibility: WCAG 2.2 (w3.org/WAI).
- Software bill of materials: CycloneDX or SPDX.
- AI principles: OECD AI Principles (oecd.ai).

## The author's own references (EU and France, used daily on a privacy project)
- Law first-hand: EUR-Lex and Légifrance for the texts, CNIL guidance and official templates, EDPB guidelines,
  ENISA for vulnerability reporting under the Cyber Resilience Act.
- Engineering: CycloneDX SBOM per BSI TR-03183-2, WCAG 2.2 AA and RGAA, OWASP ASVS, Conventional Commits with DCO
  sign-off, SPDX license headers, license compatibility checks, the stack's dependency audit (`cargo audit` and
  `cargo deny` for Rust).
- Method: free official channels first (regulator guidance and templates), one single file of questions for
  lawyers, paid counsel last; every fact tagged ✅ 🟡 📣 🧠 ❓.
