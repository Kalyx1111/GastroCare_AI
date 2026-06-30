# GastroCare AI v1.0
## Gastroenterology Health Intelligence Platform

---

## IMPORTANT MEDICAL DISCLAIMER

**THIS IS AN AI-POWERED RESEARCH AND INFORMATION TOOL ONLY.**

- All content is AI-generated from published gastroenterology literature (BSG, ACG, EASL, NICE, WHO, PubMed)
- This is **NOT** a medical diagnosis, prescription, or clinical recommendation
- **ALWAYS** consult a qualified gastroenterologist before any health decision
- **GI EMERGENCY** — Call **112 (India) / 999 (UK) / 911 (US)** IMMEDIATELY for:
  - Vomiting blood (haematemesis) or coffee-ground vomit
  - Black tarry foul-smelling stools (melaena)
  - Sudden severe abdominal pain with a rigid, board-like abdomen (perforation)
  - Jaundice with fever and rigors (cholangitis)
  - Signs of acute liver failure (confusion + jaundice + bruising)
- The creators accept **no liability** for health decisions made without professional gastroenterological consultation

---

## Quick Start (Windows)

1. Extract the ZIP to any folder (e.g., `C:\GastroCareAI\`)
2. Double-click **`START_GastroCare_AI.bat`**
3. Everything installs automatically (2-5 minutes first time)
4. Browser opens at `http://localhost:5075`
5. Accept disclaimer and begin

---

## Security — AES-256-GCM Key Encryption

Your AI provider API keys are protected with:
- **AES-256-GCM encryption** before storage in your browser
- **PBKDF2 key derivation** (100,000 iterations) from a device fingerprint
- Keys **never leave your browser** except going directly to the chosen AI provider's API
- Keys are **never logged** by the backend server
- Backend includes rate limiting (30 requests/60s) and strict provider whitelisting

---

## Choose Your AI Provider (5 Options)

Without any API key, the platform works in **offline research mode** using the embedded gastroenterology knowledge base.

| Provider | Model Used | Get a Free Key |
|----------|-----------|----------------|
| **Claude** (Anthropic) | claude-sonnet-4 | console.anthropic.com |
| **ChatGPT** (OpenAI) | gpt-4o | platform.openai.com/api-keys |
| **Gemini** (Google) | gemini-2.0-flash | aistudio.google.com/apikey |
| **Grok** (xAI) | grok-2-latest | console.x.ai |
| **DeepSeek** | deepseek-chat | platform.deepseek.com/api_keys |

---

## File Structure

```
GastroCareAI/
├── START_GastroCare_AI.bat        <- MAIN LAUNCHER
├── DIAGNOSTIC.bat                 <- System health checker
├── REPAIR_AND_RECOVER.bat         <- Fix problems
├── DOWNLOAD_OFFLINE_PACKAGES.bat  <- Save packages for offline use
├── UPDATE.bat                     <- Update packages
├── STOP_SERVER.bat                <- Stop the server
├── server.py                      <- Python Flask backend
├── README.md                      <- This file
├── modules/
│   └── ai_providers.py            <- Multi-provider AI module
├── static/
│   └── index.html                 <- Full web application
├── uploads/                       <- Your uploaded reports
├── offline_packages/              <- Cached Python packages
├── venv/                          <- Python environment (auto-created)
├── logs/                          <- Server and diagnostic logs
├── data/                          <- Knowledge base and sessions
└── reports_db/                    <- Generated AI reports
```

---

## What's Covered (10 Sections)

### GI Conditions (35+)
GERD/acid reflux, Barrett's oesophagus, peptic ulcer disease, H. pylori, gastritis, achalasia, ulcerative colitis, Crohn's disease, IBS, coeliac disease, colorectal cancer/polyps, diverticular disease, NAFLD/MASH, alcoholic liver disease, hepatitis B/C, cirrhosis, autoimmune hepatitis, PBC/PSC, gallstones, acute/chronic pancreatitis, pancreatic cancer, GI bleeding (upper/lower), constipation, dysphagia, and more via live AI.

### GI Medicines (6 Categories)
Acid suppressants (PPIs, H2 blockers, H. pylori eradication regimens), IBD medications (5-ASA, steroids, thiopurines, methotrexate, ciclosporin), liver medications (UDCA, diuretics, lactulose, terlipressin, beta-blockers, NAC), bowel agents (antispasmodics, laxatives, linaclotide, rifaximin), GI biologics (anti-TNF, vedolizumab, ustekinumab, JAK inhibitors), antivirals for Hepatitis B/C (tenofovir, entecavir, DAAs).

### Endoscopy and Procedures (5 Categories)
OGD/gastroscopy, colonoscopy (with polyp classification and surveillance intervals), ERCP, therapeutic endoscopy (polypectomy, variceal banding, RFA, APC, PEG), capsule endoscopy and EUS.

### Investigations
Imaging modalities table (USS, CT, MRI, MRCP, Fibroscan, CT colonography), key blood tests (LFTs, faecal calprotectin, anti-TTG, tumour markers, AFP), specialist tests (pH monitoring, faecal elastase, urea breath test, SIBO testing).

### GI Emergencies
Upper GI bleeding, perforation, acute cholangitis (Charcot's triad/Reynold's pentad), acute liver failure, toxic megacolon, bowel obstruction, mesenteric ischaemia — all with immediate action steps.

### GI Diet and Nutrition (5 Protocols)
Low-FODMAP diet for IBS (full food lists, 3-phase protocol), gluten-free diet for coeliac disease (India-specific food guidance), GERD diet, liver/cirrhosis diet (including correcting outdated protein restriction myths), IBD nutrition (enteral feeding, micronutrient deficiencies).

### Liver Health
Cirrhosis complications (ascites, SBP, varices, hepatic encephalopathy, HRS), NAFLD/MASLD/MASH with new resmetirom therapy.

### Cancer Screening
Colorectal cancer screening (FIT, Lynch syndrome, FAP), Barrett's oesophagus surveillance, H. pylori and gastric cancer (Correa cascade), HCC surveillance (LIRADS, BCLC staging).

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| RAM | 4 GB | 8 GB |
| Storage | 2 GB free | 5 GB free |
| Internet | For first setup | For live AI |
| Python | Auto-installed | 3.10-3.12 |

---

## India-Specific Resources

| Resource | Website |
|----------|---------|
| ISG — Indian Society of Gastroenterology | isge.in |
| AIIMS Gastroenterology, New Delhi | aiims.edu |
| Apollo Hospitals Gastroenterology | apollohospitals.com |
| SGPGI, Lucknow | sgpgi.ac.in |
| **Emergency** | **112** |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Double-click does nothing | Right-click → Run as Administrator |
| Python not found | Launcher downloads it automatically (needs internet) |
| Browser doesn't open | Go to http://localhost:5075 manually |
| Port in use | Run STOP_SERVER.bat, then START again |
| Package install fails | Run REPAIR_AND_RECOVER.bat → Option 6 |
| Works offline | Run DOWNLOAD_OFFLINE_PACKAGES.bat once while online |

---

## Clinical Sources

- **BSG** — British Society of Gastroenterology (bsg.org.uk)
- **ACG** — American College of Gastroenterology (acg.gi.org)
- **EASL** — European Association for the Study of the Liver (easl.eu)
- **NICE** — National Institute for Health and Care Excellence, UK
- **WHO** — World Health Organization
- **PubMed** — National Library of Medicine Research Database

---

## Legal Notice

This software is provided for research and educational purposes only. The creators make no representations about medical accuracy, completeness, or fitness for clinical use. Use of this tool does not constitute a medical consultation. The creators are not liable for any health outcomes arising from use of this platform. By using this software you confirm you have read and accepted the full medical disclaimer.

**GI EMERGENCY: Call 112 (India) / 999 (UK) / 911 (US) immediately. Do not rely on this software in an emergency.**

---

*GastroCare AI v1.0 — Gastroenterology Health Intelligence Platform*
*Research informs. Your gastroenterologist heals. Use both.*
