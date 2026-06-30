"""
GastroCare AI - Production Backend Server v1.0
Gastroenterology Health Intelligence Platform
==============================================
DISCLAIMER: All AI output is for research/education only.
Not medical advice. Always consult a qualified gastroenterologist.
GI EMERGENCY: Haematemesis, severe abdominal pain, signs of peritonitis,
acute liver failure, melaena - Call 112 (India) / 999 (UK) / 911 (US).
"""

import os
import sys
import json
import uuid
import time
import hashlib
import logging
import datetime
import argparse
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    FLASK_OK = True
except ImportError:
    print("[FATAL] Flask not installed. Run REPAIR_AND_RECOVER.bat")
    sys.exit(1)

try:
    import requests as req_lib
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import fitz
    FITZ_OK = True
except ImportError:
    FITZ_OK = False

# Multi-provider AI module
sys.path.insert(0, str(Path(__file__).parent / "modules"))
try:
    import ai_providers
    AI_PROVIDERS_OK = True
except ImportError:
    AI_PROVIDERS_OK = False

# Configuration
BASE_DIR    = Path(__file__).parent.resolve()
UPLOAD_DIR  = BASE_DIR / "uploads"
LOGS_DIR    = BASE_DIR / "logs"
DATA_DIR    = BASE_DIR / "data"
STATIC_DIR  = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports_db"

for d in [UPLOAD_DIR, LOGS_DIR, DATA_DIR, STATIC_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PORT    = int(os.environ.get("GASTROCARE_PORT", 5075))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEFAULT_PROVIDER_KEYS = ai_providers.get_env_keys() if AI_PROVIDERS_OK else {}
VERSION = "1.0.0"

DISCLAIMER = (
    "WARNING - AI RESEARCH DISCLAIMER: All output is AI-generated from published "
    "gastroenterology literature (BSG, ACG, EASL, NICE, WHO, PubMed). This is for "
    "educational research only. NOT a medical diagnosis or prescription. ALWAYS consult "
    "a qualified gastroenterologist before any health decision. GI EMERGENCY (vomiting "
    "blood, black/tarry stools, severe abdominal pain, jaundice with fever, signs of "
    "perforation): Call 112 (India) / 999 (UK) / 911 (US) immediately."
)

# Logging
log_file = LOGS_DIR / f"server_{datetime.date.today()}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("GastroCareAI")

app = Flask(__name__, static_folder=str(STATIC_DIR))
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
CORS(app, origins="*")

# Security: rate limiting & input sanitisation
_RATE_STORE = {}
_RATE_LIMIT  = 30
_RATE_WINDOW = 60

def _get_client_id():
    ip = request.remote_addr or '127.0.0.1'
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

def rate_limit_check():
    cid = _get_client_id()
    now = time.time()
    if cid not in _RATE_STORE:
        _RATE_STORE[cid] = []
    _RATE_STORE[cid] = [t for t in _RATE_STORE[cid] if now - t < _RATE_WINDOW]
    if len(_RATE_STORE[cid]) >= _RATE_LIMIT:
        return False
    _RATE_STORE[cid].append(now)
    return True

def sanitise_api_key(key):
    if not key or not isinstance(key, str):
        return ''
    key = key.strip()
    if len(key) > 512:
        return ''
    sanitised = ''.join(c for c in key if 0x21 <= ord(c) <= 0x7E)
    return sanitised if len(sanitised) >= 10 else ''

def validate_provider(provider):
    allowed = {'anthropic', 'openai', 'gemini', 'grok', 'deepseek'}
    if not provider or provider.lower() not in allowed:
        return 'anthropic'
    return provider.lower()

# =====================================================================
# OFFLINE GASTROENTEROLOGY KNOWLEDGE BASE
# =====================================================================
KNOWLEDGE = {
    "gerd": {
        "name": "GERD / Acid Reflux (Gastro-Oesophageal Reflux Disease)",
        "definition": "Condition where stomach acid frequently flows back into the oesophagus, irritating the lining. Most common GI condition worldwide - affects approximately 20% of Western populations. Heartburn is the cardinal symptom but atypical presentations include chronic cough, laryngitis, chest pain.",
        "symptoms": "Heartburn (burning sensation behind breastbone, worse after eating/lying down), regurgitation, dysphagia (difficulty swallowing), waterbrash (mouth filling with saliva), atypical: chronic cough, hoarseness, sore throat, chest pain mimicking cardiac disease.",
        "alarm_features": "Dysphagia or odynophagia (pain on swallowing), weight loss, anaemia, haematemesis (vomiting blood), melaena (black tarry stools), new onset symptoms over 55 years - URGENT endoscopy required.",
        "investigations": ["Upper GI endoscopy (OGD): gold-standard. Visualises oesophagitis, Barrett's oesophagus. Mandatory if alarm features.", "24-hour pH monitoring / pH-impedance study: measures acid exposure time. Gold-standard for confirming acid reflux.", "Oesophageal manometry: assesses lower oesophageal sphincter pressure and oesophageal motility.", "Barium swallow: limited role, sometimes used for structural assessment."],
        "management": ["Lifestyle: elevate head of bed, avoid eating 2-3 hours before lying down, weight loss, reduce alcohol/coffee/chocolate/fatty foods/citrus, stop smoking.", "PPIs (proton pump inhibitors): omeprazole 20mg OD, lansoprazole 30mg OD, esomeprazole 40mg OD - mainstay of treatment. Take 30 minutes before breakfast.", "H2 receptor antagonists: ranitidine (now largely withdrawn), famotidine - second-line or PPI add-on.", "Antacids: immediate relief for occasional symptoms.", "Surgical: Laparoscopic Nissen fundoplication - for refractory GERD or patients wishing to stop PPIs. Good long-term outcomes."],
        "barretts": "Barrett's oesophagus: metaplastic change of oesophageal lining to columnar epithelium due to chronic acid exposure. Pre-malignant. Risk of progression to oesophageal adenocarcinoma (~0.3% per year). Requires endoscopic surveillance every 2-5 years. Dysplasia treated with endoscopic mucosal resection (EMR) or radiofrequency ablation (RFA).",
    },
    "peptic_ulcer": {
        "name": "Peptic Ulcer Disease",
        "definition": "Ulceration of stomach (gastric ulcer) or duodenum (duodenal ulcer). Causes: H. pylori infection (~70% of duodenal ulcers), NSAIDs/aspirin, rarely Zollinger-Ellison syndrome (gastrinoma). H. pylori is a class 1 carcinogen for gastric cancer.",
        "symptoms": "Epigastric pain: gnawing/burning. Duodenal ulcer: pain relieved by food, worse 2-3 hours after eating, wakes patient at night. Gastric ulcer: pain worse with food. Nausea, vomiting, bloating.",
        "complications": "Upper GI bleeding (haematemesis/melaena): most common complication, EMERGENCY. Perforation: sudden severe abdominal pain, peritonism, surgical emergency. Gastric outlet obstruction: persistent vomiting, weight loss.",
        "investigations": ["H. pylori testing: urea breath test (gold-standard non-invasive), stool antigen test, serology (not used to confirm eradication). Endoscopy biopsy CLO test.", "Upper GI endoscopy: confirms ulcer, biopsies gastric ulcers to exclude malignancy, CLO test for H. pylori.", "FBC, U&E, LFTs: baseline. Group and save if bleeding."],
        "h_pylori_eradication": "First-line triple therapy (UK/India): Clarithromycin-based 7-14 days: PPI + clarithromycin 500mg + amoxicillin 1g, all twice daily for 7-14 days. Second-line (if clarithromycin failure): bismuth quadruple therapy. Test for eradication with urea breath test at least 4 weeks after completing antibiotics and 2 weeks after stopping PPI.",
        "management": "Stop NSAIDs if possible. PPI therapy 4-8 weeks (gastric ulcer 8 weeks, confirm healing with repeat endoscopy as gastric ulcers can be malignant). H. pylori eradication heals most ulcers and prevents recurrence. Long-term PPI if continuing NSAIDs.",
    },
    "ibd": {
        "name": "Inflammatory Bowel Disease (IBD)",
        "definition": "Chronic relapsing inflammatory conditions of the GI tract. Two main types: Ulcerative Colitis (UC) - affects colon/rectum only, continuous mucosal inflammation from rectum. Crohn's Disease (CD) - can affect any part of GI tract (mouth to anus), transmural inflammation, skip lesions, granulomas.",
        "symptoms_uc": "Bloody diarrhoea (pathognomonic of UC), urgency, tenesmus, crampy abdominal pain. Severity: mild (under 4 stools/day, no systemic features), moderate (4-6/day, minimal systemic), severe (over 6 bloody stools/day, systemic: fever, tachycardia, anaemia, raised CRP/ESR) - HOSPITAL ADMISSION required for severe UC.",
        "symptoms_cd": "Diarrhoea (may not be bloody), abdominal pain (right iliac fossa most common - terminal ileum involvement), weight loss, fatigue, fever. Perianal disease: fistulae, abscesses, skin tags. Extra-intestinal: uveitis, episcleritis, primary sclerosing cholangitis (UC), arthropathy, erythema nodosum, pyoderma gangrenosum.",
        "investigations": ["Faecal calprotectin: non-invasive marker of intestinal inflammation. Elevated in IBD (over 200 mcg/g), helps distinguish from IBS.", "Colonoscopy with biopsies: gold-standard for diagnosis, classification, dysplasia surveillance.", "CT or MRI enterography: Crohn's small bowel disease extent, complications (strictures, fistulae, abscesses).", "MRI pelvis: perianal Crohn's disease assessment.", "Blood: FBC (anaemia), CRP/ESR (inflammation), albumin, LFTs (PSC), iron studies, B12/folate (Crohn's)."],
        "medications": ["5-ASA agents (mesalazine): UC first-line for mild-moderate. Rectal/oral formulations.", "Corticosteroids: acute flare induction - prednisolone orally, IV hydrocortisone for severe UC. Not maintenance.", "Thiopurines (azathioprine, mercaptopurine): maintenance therapy. Check TPMT enzyme activity before starting. Regular FBC monitoring.", "Methotrexate: Crohn's maintenance, useful in thiopurine intolerance.", "Anti-TNF biologics (infliximab, adalimumab): moderate-severe IBD refractory to conventional therapy. TB screening before starting.", "Vedolizumab (anti-integrin): gut-selective biologic, particularly UC. Good safety profile.", "Ustekinumab (anti-IL12/23): Crohn's disease. Used after anti-TNF failure.", "JAK inhibitors (tofacitinib, filgotinib, upadacitinib): oral targeted agents for moderate-severe UC."],
        "surgery": "UC: colectomy curative (unlike Crohn's). Indications: medically refractory, dysplasia/cancer, acute severe UC not responding to IV steroids (rescue therapy with ciclosporin/infliximab first). Crohn's: bowel resection for complications (obstruction, fistula, abscess) - not curative, high recurrence rate. Strictureplasty for fibrostenotic disease.",
    },
    "ibs": {
        "name": "Irritable Bowel Syndrome (IBS)",
        "definition": "Functional bowel disorder characterised by abdominal pain associated with altered bowel habit (diarrhoea, constipation, or mixed) in the absence of structural or biochemical abnormality. Affects 10-15% of population. Rome IV diagnostic criteria: recurrent abdominal pain at least 1 day per week for 3 months, associated with 2+ of: related to defecation, change in stool frequency, change in stool form.",
        "subtypes": "IBS-D (diarrhoea predominant), IBS-C (constipation predominant), IBS-M (mixed), IBS-U (unsubtyped).",
        "red_flags": "Age over 50 with new symptoms, rectal bleeding, unexplained weight loss, family history of colorectal cancer/IBD/coeliac, nocturnal symptoms waking from sleep, raised inflammatory markers, anaemia - require investigation to exclude organic pathology.",
        "investigations": "Diagnosis of exclusion. Minimum investigations: FBC, ESR/CRP, coeliac serology (anti-TTG), thyroid function, faecal calprotectin (to exclude IBD). Colonoscopy if red flags or age over 50. Not needed if typical history and investigations normal.",
        "management": ["Explanation and reassurance: the gut-brain connection, not imaginary, lifestyle factors.", "Dietary modifications: Low-FODMAP diet (fermentable oligosaccharides, disaccharides, monosaccharides and polyols) - evidence-based, supervised by dietitian, 70% response rate in IBS-D. Regular meals, avoid trigger foods, adequate fluid.", "IBS-D: loperamide for diarrhoea control, rifaximin (antibiotic - evidence for IBS-D), mebeverine (antispasmodic), peppermint oil capsules.", "IBS-C: ispaghula husk (psyllium), osmotic laxatives (macrogol), linaclotide (secretagogue).", "Psychological therapies: CBT, gut-directed hypnotherapy - strong evidence for chronic refractory IBS.", "Low-dose tricyclic antidepressants (amitriptyline 10-30mg at night): modulate gut-brain axis, good evidence for pain and diarrhoea."],
    },
    "liver_disease": {
        "name": "Liver Disease and Cirrhosis",
        "nafld": "NAFLD (Non-Alcoholic Fatty Liver Disease) / MASLD: Most common liver disease in Western world. Spectrum: simple steatosis (fat accumulation, benign) to NASH/MASH (steatohepatitis with inflammation) to fibrosis to cirrhosis to HCC. Associated with obesity, T2DM, metabolic syndrome. Management: weight loss (even 5-10% improves histology), treat metabolic risk factors, avoid alcohol. New therapy: semaglutide, resmetirom (THR-beta agonist - first FDA-approved treatment for MASH with fibrosis).",
        "alcohol_liver": "Alcoholic liver disease spectrum: fatty liver (reversible), alcoholic hepatitis (jaundice, fever, hepatomegaly - can be severe with 30-day mortality 30-40% in severe cases - Maddrey DF over 32), cirrhosis. Treatment: abstinence is most important, prednisolone for severe alcoholic hepatitis (Maddrey DF over 32), nutritional support, Bactrim/cipro for SBP prophylaxis.",
        "cirrhosis_complications": ["Ascites: first-line spironolactone +/- furosemide, sodium restriction, therapeutic paracentesis for tense ascites + albumin.", "SBP (Spontaneous Bacterial Peritonitis): diagnostic tap (PMN over 250/mm3), IV cefotaxime/tazobactam, albumin infusion, long-term norfloxacin prophylaxis.", "Hepatic encephalopathy: lactulose, rifaximin, treat precipitants (infection, bleeding, constipation, electrolyte imbalance).", "Varices: non-selective beta-blockers (propranolol/carvedilol) for primary/secondary prophylaxis. Acute variceal bleeding: EMERGENCY - terlipressin/somatostatin, endoscopic banding, Sengstaken tube if refractory, TIPSS.", "Hepatorenal syndrome: terlipressin + albumin infusion.", "HCC surveillance: 6-monthly USS + AFP in all cirrhotic patients."],
        "viral_hepatitis": "Hepatitis B: antiviral therapy (tenofovir, entecavir) suppresses viral replication, prevents progression. HBsAg+ screen contacts, vaccinate. Hepatitis C: direct-acting antivirals (DAAs) - sofosbuvir-based regimens - 95%+ cure rate, 8-12 week treatment, minimal side effects. Pan-genotypic regimens now standard.",
        "liver_investigations": ["LFTs: ALT/AST (hepatocellular damage), ALP/GGT (cholestatic), bilirubin, albumin, PT (synthetic function).", "Viral serology: HBsAg, HBcAb, HCV Ab, HDV Ab.", "Autoimmune: ANA, ASMA, AMA (PBC), ANCA.", "Fibroscan (transient elastography): non-invasive liver fibrosis assessment.", "CT/MRI liver: cirrhosis features, HCC screening.", "Liver biopsy: gold-standard fibrosis staging, but increasingly replaced by non-invasive tests."],
    },
    "colorectal_cancer": {
        "name": "Colorectal Cancer and Polyps",
        "definition": "Third most common cancer worldwide. 90% are adenocarcinomas. Majority arise from adenomatous polyps (adenoma-carcinoma sequence). Risk factors: age (over 50), family history (Lynch syndrome, FAP), IBD (especially extensive UC), red/processed meat, obesity, smoking, alcohol, diabetes.",
        "bowel_screening": "NHS Bowel Screening Programme (UK): FIT (faecal immunochemical test) offered every 2 years age 50-74. Positive FIT → colonoscopy. India: currently no national programme, high-risk individuals screened at tertiary centres.",
        "warning_signs": "Rectal bleeding (especially mixed with stool, in those over 40-50), change in bowel habit lasting over 6 weeks, unexplained weight loss, anaemia with GI symptoms, palpable abdominal/rectal mass, tenesmus. Any of these: URGENT GP/hospital referral for 2-week-wait colonoscopy.",
        "polyp_management": "Hyperplastic polyps: low-risk, surveillance interval depends on number/size. Adenomas: low-risk (1-2, under 10mm, tubular, low-grade dysplasia), high-risk (3-4 adenomas, any over 10mm, villous features, high-grade dysplasia). Endoscopic polypectomy. Post-polypectomy surveillance colonoscopy intervals per BSG/ACG guidelines.",
        "staging": "Duke's/TNM staging: I (confined to mucosa/submucosa), II (penetrates bowel wall, no nodes), III (regional lymph node involvement), IV (distant metastases). Surgery: curative resection (right/left hemicolectomy, anterior resection, APR) + adjuvant chemotherapy for stage III (FOLFOX/CAPOX). Stage IV: chemotherapy (FOLFOX + bevacizumab or cetuximab/panitumumab if RAS wild-type), liver metastasectomy if resectable.",
        "lynch_syndrome": "Lynch syndrome (HNPCC): autosomal dominant, mutations in DNA mismatch repair genes (MLH1, MSH2, MSH6, PMS2). Lifetime CRC risk 40-80%. Annual/biennial colonoscopy from age 25. Also associated with endometrial, ovarian, gastric, urological cancers. All CRC specimens should have MMR immunohistochemistry (universal MMR testing).",
    },
    "gi_bleeding": {
        "name": "Gastrointestinal Bleeding",
        "upper_gi_bleeding": "Haematemesis (vomiting red blood or coffee-grounds) or melaena (black tarry stools). Causes: peptic ulcer (most common, approximately 50%), oesophageal/gastric varices, Mallory-Weiss tear, oesophagitis, gastric cancer, Dieulafoy lesion.",
        "ugib_emergency": "EMERGENCY MANAGEMENT: IV access x2, FBC/clotting/group and save/crossmatch. Resuscitate with IV fluids/blood (target Hb over 70-80 g/L, over 100 in cardiovascular disease). Terlipressin if suspected varices. IV PPI (omeprazole 80mg bolus then infusion). Risk stratify with Glasgow-Blatchford Score (GBS): GBS 0 = low risk, discharge and outpatient scope. Urgent endoscopy within 24 hours (within 12 hours for variceal suspected/haemodynamically unstable). Adrenaline injection + clip/thermal for peptic ulcer bleeding. Band ligation for oesophageal varices.",
        "lower_gi_bleeding": "Fresh rectal bleeding (haematochezia). Causes: diverticular disease (most common), haemorrhoids, colonic polyps/cancer, angiodysplasia, colitis (IBD, ischaemic, infectious). Massive lower GI bleed: resuscitate, CT angiography (identifies source if active bleeding), colonoscopy, interventional radiology (embolisation), surgery as last resort.",
        "occult_bleeding": "Iron-deficiency anaemia without obvious source. Faecal immunochemical test (FIT). Bidirectional endoscopy (gastroscopy + colonoscopy). Capsule endoscopy for small bowel source if both negative. Device-assisted enteroscopy for therapeutic access to small bowel lesions.",
        "rockall_score": "Rockall score: post-endoscopy risk stratification for UGIB rebleeding and mortality. Score 0-2: low risk (outpatient). Score over 8: high risk (rebleeding/mortality). Components: age, shock, comorbidity, endoscopic diagnosis, stigmata of recent haemorrhage.",
    },
    "pancreatitis": {
        "name": "Pancreatitis",
        "acute_pancreatitis": "Acute inflammation of the pancreas. Causes: gallstones (most common, approximately 45%), alcohol (approximately 35%), hypertriglyceridaemia, hypercalcaemia, ERCP, drugs, idiopathic. Severity: mild (interstitial oedematous, self-limiting), moderate (local complications, no organ failure), severe (persistent organ failure over 48 hours - ICU care).",
        "ap_symptoms": "Severe epigastric pain radiating to the back ('boring' quality), worse lying flat, better leaning forward. Nausea, vomiting, abdominal tenderness, fever. Grey-Turner sign (flank bruising), Cullen sign (periumbilical bruising) - indicate haemorrhagic pancreatitis.",
        "ap_investigations": "Serum amylase (over 3x upper limit of normal) or lipase (more sensitive and specific). FBC, CRP (severity marker - over 150 at 48 hours suggests severe). LFTs (if gallstone cause), calcium, triglycerides. USS abdomen: gallstones, CBD dilation. CT abdomen (Balthazar/CTSI scoring): severity, complications (necrosis, pseudocyst) - not needed for mild AP, perform at 48-72 hours if uncertain severity or not improving.",
        "ap_management": "Fluid resuscitation (Hartmann's preferred), analgesia (IV morphine/pethidine), NBM initially then early enteral feeding (nasojejunal or oral if tolerated - better than TPN). Antibiotics only if infected necrosis (CT-guided FNA). ERCP within 72 hours if CBD stones with cholangitis. Cholecystectomy during same admission or within 2 weeks for gallstone AP (prevents recurrence).",
        "chronic_pancreatitis": "Progressive irreversible destruction of pancreatic parenchyma. Causes: alcohol (most common), smoking, idiopathic, genetic (PRSS1, SPINK1, CFTR mutations), autoimmune. Triad: pain (epigastric, chronic), exocrine insufficiency (steatorrhoea, malabsorption, weight loss), endocrine insufficiency (diabetes). Management: abstinence from alcohol, smoking cessation, pain management (analgesics, pancreatic enzyme replacement improves pain), CREON (pancreatic enzyme replacement therapy) for exocrine insufficiency, insulin for diabetes. Endoscopic/surgical drainage procedures for refractory pain (pancreatic duct strictures/stones).",
    },
    "coeliac": {
        "name": "Coeliac Disease and Malabsorption",
        "definition": "Autoimmune enteropathy triggered by dietary gluten (wheat, barley, rye) in genetically susceptible individuals (HLA-DQ2/DQ8). Villous atrophy of small intestinal mucosa. Affects approximately 1% of population. Often under-diagnosed.",
        "symptoms": "Classic (less common): diarrhoea, steatorrhoea, bloating, weight loss, failure to thrive (children). Atypical (more common): iron-deficiency anaemia, fatigue, osteoporosis, infertility, peripheral neuropathy, dermatitis herpetiformis (intensely itchy blistering skin rash on extensor surfaces), aphthous ulcers. Incidentally found elevated liver enzymes.",
        "investigations": "Serology (on gluten-containing diet): anti-TTG IgA (anti-tissue transglutaminase) - most sensitive/specific. Total IgA level (IgA deficiency causes false negative TTG). Anti-endomysial antibody (EMA). Duodenal biopsies (OGD with multiple biopsies from duodenum including bulb): Marsh classification - villous atrophy (Marsh 3) confirmatory.",
        "management": "Strict lifelong gluten-free diet (GFD): main treatment. Improves symptoms, reverses villous atrophy, reduces cancer risk (small bowel T-cell lymphoma, enteropathy-associated T-cell lymphoma - EATL). Iron, folate, B12, calcium, vitamin D supplementation for deficiencies. Annual review with dietitian. Dual-energy X-ray absorptiometry (DEXA) scan: bone density. Repeat biopsy at 1-2 years to confirm mucosal healing. Refractory coeliac disease (RCD): symptoms/villous atrophy despite strict GFD - specialist management, high lymphoma risk.",
        "malabsorption": "Causes: coeliac disease, Crohn's disease, tropical sprue, Whipple's disease, short bowel syndrome, bacterial overgrowth. Assessment: faecal elastase (exocrine pancreatic insufficiency), glucose hydrogen breath test (SIBO), D-xylose test, small bowel biopsy.",
    },
    "gi_emergency": {
        "name": "GI Emergencies",
        "haematemesis": "Vomiting fresh red blood or 'coffee grounds' (digested blood). MEDICAL EMERGENCY. Call 999/112/911. Large-bore IV access, blood tests, resuscitation. Urgent endoscopy. Upper GI bleeding with haemodynamic instability: immediate resuscitation, terlipressin if varices suspected.",
        "melaena": "Black tarry foul-smelling stools = digested blood from upper GI source. Often more insidious than haematemesis but equally serious. Urgent same-day endoscopy after resuscitation.",
        "perforation": "Sudden onset severe generalised abdominal pain, board-like rigidity, absent bowel sounds, peritonism. Causes: perforated peptic ulcer (most common), perforated diverticulitis, perforated colon cancer. SURGICAL EMERGENCY. Erect CXR (free air under diaphragm), CT abdomen. Emergency surgery or conservative management (selected cases).",
        "acute_liver_failure": "Rapid onset jaundice + coagulopathy (PT prolonged) + hepatic encephalopathy in previously normal liver. Causes: paracetamol overdose (most common UK), viral hepatitis (HAV, HBE), autoimmune, Wilson's disease, Budd-Chiari. MEDICAL EMERGENCY. Intensive care. N-acetylcysteine for paracetamol. Liver transplantation assessment. King's College criteria for transplant listing.",
        "acute_cholangitis": "Charcot's triad: fever + jaundice + right upper quadrant pain. Reynold's pentad adds: hypotension + altered consciousness (severe cholangitis). Caused by biliary obstruction (gallstones, strictures) + bacterial infection. IV antibiotics + urgent ERCP for biliary decompression.",
        "bowel_obstruction": "Mechanical small bowel obstruction: abdominal distension, colicky pain, vomiting, constipation. Causes: adhesions (most common post-surgical), hernia, cancer. AXR/CT abdomen. Drip and suck (IV fluids + NG tube decompression). Surgery if complete obstruction, strangulation suspected, or failure to resolve. Large bowel obstruction: colorectal cancer, volvulus (sigmoid - flatus tube, endoscopic decompression, surgery if ischaemia).",
        "toxic_megacolon": "Life-threatening complication of UC (or C. difficile colitis). Colonic dilatation (transverse colon over 6cm) + systemic toxicity (fever, tachycardia, hypotension, impaired consciousness). MEDICAL EMERGENCY. ICU care, IV steroids, antibiotics (metronidazole + vancomycin enema for C. diff), surgical consultation. Emergency colectomy if no improvement in 24-72 hours.",
    },
}

def save_knowledge():
    with open(DATA_DIR / "gastro_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(KNOWLEDGE, f, indent=2, ensure_ascii=False)

def load_sessions():
    sf = DATA_DIR / "sessions.json"
    if sf.exists():
        with open(sf, "r") as f:
            return json.load(f)
    return {}

def save_session(sid, data):
    sessions = load_sessions()
    sessions[sid] = {**data, "updated": datetime.datetime.now().isoformat()}
    with open(DATA_DIR / "sessions.json", "w") as f:
        json.dump(sessions, f, indent=2)

def is_online():
    if not REQUESTS_OK:
        return False
    try:
        req_lib.get("https://8.8.8.8", timeout=3)
        return True
    except Exception:
        return False

def extract_pdf_text(filepath):
    if not FITZ_OK:
        return "[PDF extraction unavailable]"
    try:
        doc = fitz.open(str(filepath))
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text[:8000]
    except Exception as e:
        return f"[PDF extraction error: {e}]"

DEFAULT_SYSTEM_PROMPT = (
    "You are GastroCare AI, a gastroenterology health research assistant. You help patients understand "
    "GI conditions, medications, endoscopic procedures, and lifestyle from published gastroenterology literature. "
    "ALWAYS begin with a brief disclaimer that this is AI research. "
    "Provide thorough, evidence-based information referencing BSG, ACG, EASL, NICE guidelines. "
    "ALWAYS end with a reminder to consult a qualified gastroenterologist. "
    "For GI emergencies (haematemesis, perforation, acute liver failure, melaena), "
    "advise calling 112 India / 999 UK / 911 US immediately. "
    "Be specific with clinical details. Never refuse educational information."
)

def call_ai(prompt, system_prompt=None, max_tokens=2500, provider=None, api_key=None):
    if not AI_PROVIDERS_OK:
        return None, "ai_providers_module_missing"
    provider = validate_provider(provider or "anthropic")
    effective_key = sanitise_api_key(api_key) or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider == "anthropic" else "")
    if not effective_key or not REQUESTS_OK or not is_online():
        return None, "offline_or_no_key"
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT
    text, mode = ai_providers.call_ai(provider, effective_key, prompt, system_prompt, max_tokens)
    if text is None:
        log.error(f"{provider} API error: {mode}")
        return None, mode
    return text, "live_ai"

def build_offline_response(topic, details="", patient_info=None):
    topic_l = topic.lower()
    kb_key = None
    for key in KNOWLEDGE:
        kb_name = KNOWLEDGE[key].get("name", "").lower()
        if key.replace("_"," ") in topic_l or topic_l in key.replace("_"," ") or topic_l in kb_name:
            kb_key = key
            break

    lines = [
        "# GastroCare AI Research Report",
        f"**Topic:** {topic}",
        "**Mode:** Offline Research (Embedded Gastroenterology Knowledge Base)",
        "",
        "> WARNING - DISCLAIMER: AI-generated educational information from published gastroenterology "
        "literature (BSG, ACG, EASL, NICE, WHO). NOT a medical diagnosis or prescription. "
        "ALWAYS consult a qualified gastroenterologist. "
        "GI EMERGENCY: Call 112 (India) / 999 (UK) / 911 (US) immediately.",
        "",
        "---",
        ""
    ]

    if kb_key:
        kb = KNOWLEDGE[kb_key]
        lines.append(f"## {kb.get('name', topic)}")
        lines.append("")
        for field, value in kb.items():
            if field == "name":
                continue
            if isinstance(value, str):
                lines.append(f"**{field.replace('_',' ').title()}:** {value}")
                lines.append("")
            elif isinstance(value, list):
                lines.append(f"### {field.replace('_',' ').title()}")
                for item in value:
                    lines.append(f"- {item}")
                lines.append("")
    else:
        lines += [
            f"## Research Overview: {topic}",
            "",
            f"Gastroenterology research from BSG, ACG, EASL, NICE, WHO guidelines for {topic}.",
            "",
            "Enable live AI in Settings for detailed research, or consult your gastroenterologist.",
            ""
        ]

    lines += [
        "---",
        "## India GI Resources",
        "- **ISG:** Indian Society of Gastroenterology (isge.in)",
        "- **AIIMS GI, New Delhi:** aiims.edu",
        "- **Apollo Hospitals (Gastroenterology):** apollohospitals.com",
        "- **SGPGI, Lucknow:** sgpgi.ac.in",
        "- **Emergency:** 112",
        "",
        f"WARNING - {DISCLAIMER}"
    ]
    return "\n".join(lines)

# Routes
@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(STATIC_DIR), filename)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": VERSION, "online": is_online(),
                    "pdf_extract": FITZ_OK, "timestamp": datetime.datetime.now().isoformat()})

@app.route("/api/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files"}), 400
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        safe = f"{uuid.uuid4().hex}{ext}"
        dest = session_dir / safe
        f.save(str(dest))
        ftype = "pdf" if ext == ".pdf" else ("image" if ext in [".jpg",".jpeg",".png"] else "text")
        extracted = extract_pdf_text(dest) if ext == ".pdf" else ""
        results.append({"original": f.filename, "saved": safe, "type": ftype,
                        "size_kb": round(dest.stat().st_size/1024, 1), "has_content": bool(extracted)})
    existing = load_sessions().get(session_id, {})
    save_session(session_id, {"session_id": session_id, "files": existing.get("files",[]) + results})
    return jsonify({"success": True, "session_id": session_id, "uploaded": len(results), "files": results, "disclaimer": DISCLAIMER})

@app.route("/api/analyse", methods=["POST"])
def analyse():
    data = request.json or {}
    if not rate_limit_check():
        return jsonify({"error": "Rate limit exceeded. Please wait before making another request.", "mode": "rate_limited"}), 429
    topic        = data.get("topic", "General Gastroenterology")
    condition    = data.get("condition", "")
    patient_info = data.get("patient_info", {})
    section      = data.get("section", "general")
    session_id   = data.get("session_id", "")
    provider     = validate_provider(data.get("provider", "anthropic"))
    api_key_from_client = sanitise_api_key(data.get("api_key", ""))
    effective_key = api_key_from_client or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider=="anthropic" else "")

    log.info(f"Analysis: topic={topic} section={section} provider={provider}")

    file_context = ""
    if session_id:
        sessions = load_sessions()
        if session_id in sessions:
            files = sessions[session_id].get("files", [])
            if files:
                file_context = f"\n\nUploaded Reports ({len(files)} files):\n"
                for fi in files[:10]:
                    file_context += f"- {fi['original']} ({fi['type']}, {fi['size_kb']} KB)\n"

    prompt = f"""
Gastroenterology Health Research Request:
Topic/Condition: {topic}
Specific Condition: {condition}
Patient Age: {patient_info.get('age','Not specified')}
Symptoms: {patient_info.get('symptoms','Not specified')}
Current Medications: {patient_info.get('medications','None specified')}
Other Conditions: {patient_info.get('conditions','None specified')}
Section Requested: {section}
{file_context}

Please provide comprehensive gastroenterology research covering:
1. Overview and clinical context
2. Diagnosis criteria and investigations (endoscopy, imaging, blood tests)
3. Evidence-based treatment options (medical, endoscopic, surgical)
4. Relevant medications with dosing from BSG/ACG/EASL/NICE guidelines
5. Diet and lifestyle recommendations
6. When to seek emergency care (red flags)
7. India-specific resources and hospitals
8. Questions to ask their gastroenterologist
9. Recent developments and clinical trial evidence

Reference BSG, ACG, EASL, NICE guidelines. Be specific and clear about emergency warning signs.
"""
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key) if (effective_key and is_online()) else (None, "offline")
    if not result:
        result = build_offline_response(topic, condition, patient_info)
        mode = "offline"
    return jsonify({"success": True, "mode": mode, "analysis": result, "topic": topic, "disclaimer": DISCLAIMER, "timestamp": datetime.datetime.now().isoformat()})

@app.route("/api/condition/<condition_name>", methods=["GET"])
def condition_detail(condition_name):
    cn = condition_name.lower().replace("-","_").replace(" ","_")
    if cn in KNOWLEDGE:
        return jsonify({"success": True, "mode": "offline_kb", "condition": KNOWLEDGE[cn], "disclaimer": DISCLAIMER})
    provider = validate_provider(request.args.get("provider", "anthropic"))
    api_key  = sanitise_api_key(request.args.get("api_key", ""))
    effective_key = api_key or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider=="anthropic" else "")
    prompt = f"Provide comprehensive clinical research about {condition_name} in gastroenterology. Include: definition, prevalence, causes, symptoms, diagnosis criteria (with specific investigations), evidence-based treatment options (medical, endoscopic, surgical), prognosis, and management guidelines from BSG, ACG, EASL, NICE."
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key)
    if not result:
        result = build_offline_response(condition_name)
        mode = "offline"
    return jsonify({"success": True, "mode": mode, "content": result, "disclaimer": DISCLAIMER})

@app.route("/api/endoscopy/interpret", methods=["POST"])
def interpret_endoscopy():
    data = request.json or {}
    procedure = data.get("procedure", "OGD/Endoscopy")
    findings  = data.get("findings", "")
    context   = data.get("context", "")
    provider = validate_provider(data.get("provider", "anthropic"))
    api_key  = sanitise_api_key(data.get("api_key", ""))
    effective_key = api_key or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider=="anthropic" else "")
    prompt = f"""
Endoscopy / GI Procedure Report Interpretation Research:
Procedure: {procedure}
Reported Findings: {findings}
Clinical Context: {context}

Please research what these findings may indicate:
1. Explanation of each finding in plain English
2. Clinical significance and what follow-up is typically recommended
3. Grading/classification systems relevant to these findings
4. Treatment options associated with these findings
5. Questions to ask the reporting gastroenterologist
6. Whether findings require urgent follow-up

IMPORTANT: Research only. Actual interpretation by qualified gastroenterologist required.
"""
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key)
    if not result:
        result = f"Endoscopy interpretation research for {procedure}: '{findings}'. Requires clinical correlation by your gastroenterologist. Enable live AI in Settings for detailed research."
        mode = "offline"
    return jsonify({"success": True, "mode": mode, "content": result, "disclaimer": DISCLAIMER})

@app.route("/api/chat/send", methods=["POST"])
def chat_send():
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400
    provider = validate_provider(data.get("provider", "anthropic"))
    api_key  = sanitise_api_key(data.get("api_key", ""))
    effective_key = api_key or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider=="anthropic" else "")
    if data.get("request_ai", False) and is_online() and effective_key:
        prompt = f"A gastroenterology health question from a patient: '{message}'\n\nProvide a compassionate, research-based response (3-4 paragraphs). Always end with reminder to consult their gastroenterologist, and for GI emergencies (vomiting blood, severe abdominal pain, black stools) to call 112/999/911."
        result, _ = call_ai(prompt, max_tokens=800, provider=provider, api_key=effective_key)
    else:
        result = None
    return jsonify({"success": True, "ai_response": result, "disclaimer": "Not medical advice. Consult your gastroenterologist."})

@app.route("/api/report/generate", methods=["POST"])
def generate_report():
    data = request.json or {}
    topic   = data.get("topic", "General GI")
    patient = data.get("patient_info", {})
    provider = validate_provider(data.get("provider", "anthropic"))
    api_key  = sanitise_api_key(data.get("api_key", ""))
    effective_key = api_key or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider=="anthropic" else "")
    content = build_offline_response(topic, patient_info=patient)
    if effective_key and is_online():
        ai_content, _ = call_ai(f"Generate a comprehensive gastroenterology research report for: {topic}. Patient: {patient}. Cover diagnosis, treatment options, medications, diet, endoscopic procedures, and follow-up recommendations.", max_tokens=3500, provider=provider, api_key=effective_key)
        if ai_content:
            content = ai_content
    report_id = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    report = {"report_id": report_id, "generated": datetime.datetime.now().isoformat(), "topic": topic, "patient": patient, "content": content, "disclaimer": DISCLAIMER}
    with open(REPORTS_DIR / f"{report_id}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return jsonify(report)

@app.route("/api/providers", methods=["GET"])
def list_providers():
    if not AI_PROVIDERS_OK:
        return jsonify({"providers": [], "error": "ai_providers module not available"})
    providers = []
    for key, cfg in ai_providers.PROVIDERS.items():
        providers.append({"id": key, "label": cfg["label"], "default_model": cfg["default_model"],
                          "key_prefix": cfg["key_prefix"], "get_key_url": cfg["get_key_url"],
                          "server_default_configured": bool(DEFAULT_PROVIDER_KEYS.get(key))})
    return jsonify({"providers": providers, "online": is_online()})

@app.route("/api/status", methods=["GET"])
def status():
    any_key = bool(API_KEY) or any(DEFAULT_PROVIDER_KEYS.values())
    return jsonify({
        "server": "running", "version": VERSION, "online": is_online(),
        "mode": "live_ai" if (any_key and is_online()) else "offline_research",
        "capabilities": {"pdf": FITZ_OK, "images": PIL_OK, "live_ai": bool(any_key and is_online()),
                         "offline": True, "multi_provider": AI_PROVIDERS_OK, "rate_limiting": True, "aes256_frontend": True},
        "knowledge_base": list(KNOWLEDGE.keys()),
        "providers": list(ai_providers.PROVIDERS.keys()) if AI_PROVIDERS_OK else [],
        "disclaimer": DISCLAIMER
    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GastroCare AI Server")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    save_knowledge()
    log.info("=" * 60)
    log.info(f"  GastroCare AI Server v{VERSION} - Port {args.port}")
    log.info(f"  Online: {is_online()}")
    log.info(f"  URL: http://localhost:{args.port}")
    log.info("=" * 60)
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True, use_reloader=False)
