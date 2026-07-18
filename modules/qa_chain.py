from groq import Groq
from dotenv import load_dotenv
import os
import re

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Extended lab reference table ─────────────────────────────────────────────
# Format: (name, regex, unit, low, high, low_suggests, high_suggests)
LAB_REFERENCE = [
    # CBC
    ("Hemoglobin",     r"h(?:a?e)?moglobin[:\s]*([\d\.]+)",     "g/dL",    12.0, 17.5,
     "Anemia (iron deficiency, B12/folate deficiency, chronic disease, blood loss)",
     "Polycythemia / erythrocytosis"),

    ("Hematocrit",     r"h(?:a?e)?matocrit[:\s]*([\d\.]+)",     "%",       36,   52,
     "Anemia, overhydration",
     "Dehydration, polycythemia"),

    ("WBC",            r"w(?:hite\s*blood\s*cell|bc)[:\s]*([\d\.]+)", "×10³/μL", 4.0, 11.0,
     "Leukopenia — immunosuppression, bone marrow failure, viral infection, lupus",
     "Leukocytosis — bacterial infection, leukemia, inflammation, steroid use"),

    ("Platelets",      r"platelets?[:\s]*([\d\.]+)",             "×10³/μL", 150, 400,
     "Thrombocytopenia — dengue, ITP, DIC, bone marrow failure, liver disease",
     "Thrombocytosis — inflammation, iron deficiency, reactive state"),

    ("RBC",            r"r(?:ed\s*blood\s*cell|bc)[:\s]*([\d\.]+)", "×10⁶/μL", 4.0, 5.9,
     "Anemia",
     "Polycythemia, dehydration"),

    ("MCV",            r"mcv[:\s]*([\d\.]+)",                    "fL",      80,   100,
     "Microcytic anemia — iron deficiency, thalassemia",
     "Macrocytic anemia — B12/folate deficiency, liver disease, hypothyroidism"),

    # Metabolic
    ("Glucose (fasting)", r"(?:fasting\s*)?glucose[:\s]*([\d\.]+)", "mg/dL", 70, 99,
     "Hypoglycemia — insulin excess, Addison's disease, liver failure",
     "Hyperglycemia — Type 1/2 diabetes, prediabetes, stress hyperglycemia, Cushing's syndrome"),

    ("HbA1c",          r"hb\s*a1c[:\s]*([\d\.]+)",              "%",       None, 5.7,
     None,
     "Prediabetes (5.7–6.4%) / Type 2 diabetes (≥6.5%) — poor glycaemic control"),

    ("Cholesterol (total)", r"(?:total\s*)?cholesterol[:\s]*([\d\.]+)", "mg/dL", None, 200,
     None,
     "Hypercholesterolemia — cardiovascular risk, familial hypercholesterolemia, hypothyroidism"),

    ("LDL",            r"ldl[:\s]*([\d\.]+)",                    "mg/dL",   None, 100,
     None,
     "Elevated LDL — increased atherosclerosis & cardiovascular disease risk"),

    ("HDL",            r"hdl[:\s]*([\d\.]+)",                    "mg/dL",   40,   None,
     "Low HDL — cardiovascular disease risk, metabolic syndrome",
     None),

    ("Triglycerides",  r"triglycerides?[:\s]*([\d\.]+)",         "mg/dL",   None, 150,
     None,
     "Hypertriglyceridemia — metabolic syndrome, pancreatitis risk, hypothyroidism, diabetes"),

    # Renal
    ("Creatinine",     r"creatinine[:\s]*([\d\.]+)",             "mg/dL",   0.6,  1.2,
     "Low creatinine — low muscle mass, malnutrition",
     "Elevated creatinine — acute kidney injury, chronic kidney disease, dehydration"),

    ("BUN",            r"b(?:lood\s*urea\s*)?(?:urea\s*)?nitrogen|bun[:\s]*([\d\.]+)", "mg/dL", 7, 20,
     "Low BUN — liver failure, malnutrition",
     "Elevated BUN — kidney disease, dehydration, high protein intake, GI bleed"),

    ("eGFR",           r"e?gfr[:\s]*([\d\.]+)",                  "mL/min",  60,   None,
     "Reduced eGFR — chronic kidney disease (stage depends on value: <60 = CKD, <30 = severe)",
     None),

    ("Uric Acid",      r"uric\s*acid[:\s]*([\d\.]+)",            "mg/dL",   None, 7.0,
     None,
     "Hyperuricemia — gout, kidney stones, metabolic syndrome"),

    # Liver
    ("ALT",            r"alt\b[:\s]*([\d\.]+)",                  "U/L",     None, 56,
     None,
     "Elevated ALT — liver injury, hepatitis, fatty liver disease, medication toxicity"),

    ("AST",            r"ast\b[:\s]*([\d\.]+)",                  "U/L",     None, 40,
     None,
     "Elevated AST — liver disease, cardiac injury, muscle damage"),

    ("Bilirubin (total)", r"(?:total\s*)?bilirubin[:\s]*([\d\.]+)", "mg/dL", None, 1.2,
     None,
     "Hyperbilirubinemia — jaundice, hepatitis, hemolytic anemia, biliary obstruction"),

    # Thyroid
    ("TSH",            r"tsh[:\s]*([\d\.]+)",                    "mIU/L",   0.4,  4.0,
     "Low TSH — hyperthyroidism (Graves' disease, toxic nodule)",
     "High TSH — hypothyroidism (Hashimoto's, iodine deficiency)"),

    ("T4 (free)",      r"(?:free\s*)?t4[:\s]*([\d\.]+)",         "ng/dL",   0.8,  1.8,
     "Low fT4 — hypothyroidism",
     "High fT4 — hyperthyroidism"),

    ("Anti-TPO (Microsomal Antibody)",
     r"(?:anti[\s\-]?tpo|microsomal\s*antibody|anti[\s\-]?thyroid\s*peroxidase)[:\s]*([\d\.]+)",
     "IU/ml", None, 8.0,
     None,
     "Elevated Anti-TPO — autoimmune thyroid disease (Hashimoto's thyroiditis, Graves' disease); "
     "also seen in Rheumatoid Arthritis, Addison's disease, Type 1 Diabetes"),

    ("Anti-Thyroglobulin Antibody",
     r"(?:anti[\s\-]?tg|anti[\s\-]?thyroglobulin|thyroglobulin\s*antibody)[:\s]*([\d\.]+)",
     "IU/ml", None, 18.0,
     None,
     "Elevated Anti-Tg — autoimmune thyroid disease; detectable at low levels in ~20% of patients "
     "with other autoimmune diseases such as Rheumatoid Arthritis, Addison's disease, Type 1 Diabetes"),

    # Electrolytes
    ("Sodium",         r"sodium|na\+?[:\s]*([\d\.]+)",           "mEq/L",   136,  145,
     "Hyponatremia — SIADH, heart failure, cirrhosis, hypothyroidism",
     "Hypernatremia — dehydration, diabetes insipidus"),

    ("Potassium",      r"potassium|k\+?[:\s]*([\d\.]+)",         "mEq/L",   3.5,  5.0,
     "Hypokalemia — diuretics, diarrhea, vomiting, hyperaldosteronism",
     "Hyperkalemia — kidney failure, ACE inhibitors, Addison's disease (RISK: arrhythmia)"),

    # Inflammation
    ("CRP",            r"c[\-\s]?reactive\s*protein|crp[:\s]*([\d\.]+)", "mg/L", None, 10,
     None,
     "Elevated CRP — bacterial infection, inflammation, autoimmune disease, cardiovascular risk"),

    ("ESR",            r"esr[:\s]*([\d\.]+)",                    "mm/hr",   None, 20,
     None,
     "Elevated ESR — infection, autoimmune disease, cancer, chronic inflammation"),
]


def extract_lab_values(text: str) -> list[dict]:
    """
    Extract numeric lab values and flag abnormalities.
    """
    findings = []
    text_lower = text.lower()

    for entry in LAB_REFERENCE:
        if len(entry) == 7:
            name, pattern, unit, low, high, low_msg, high_msg = entry
        else:
            continue

        match = re.search(pattern, text_lower)
        if not match:
            continue

        try:
            raw = match.group(1)
            if raw is None:
                segment = text_lower[match.start():match.start() + 60]
                num_match = re.search(r"([\d]+\.?[\d]*)", segment[len(match.group(0)):])
                if not num_match:
                    continue
                raw = num_match.group(1)
            value = float(raw)
        except (ValueError, IndexError, AttributeError):
            continue

        status = "normal"
        interpretation = None

        if low is not None and value < low:
            status = "LOW"
            interpretation = low_msg
        elif high is not None and value > high:
            status = "HIGH"
            interpretation = high_msg

        findings.append({
            "name": name,
            "value": value,
            "unit": unit,
            "status": status,
            "interpretation": interpretation,
            "low_ref": low,
            "high_ref": high,
        })

    return findings


# ── Severity weights ──────────────────────────────────────────────────────────
SEVERITY_WEIGHTS = {
    # Score 3 — serious / potentially life-threatening
    "arrhythmia":           3,
    "cardiac":              3,
    "leukemia":             3,
    "bone marrow failure":  3,
    "DIC":                  3,
    "pancreatitis":         3,
    # Score 2 — moderate / requires prompt medical review
    "diabetes":             2,
    "kidney":               2,
    "liver":                2,
    "cardiovascular disease": 2,
    "hypothyroidism":       2,
    "hyperthyroidism":      2,
    "autoimmune":           2,
    "hashimoto":            2,
    "graves":               2,
    # Score 1 — mild / monitor
    "anemia":               1,
    "infection":            1,
    "inflammation":         1,
}


def severity_from_findings(findings: list[dict]) -> str:
    """
    Determine overall severity based on abnormal findings.
    """
    abnormal = [f for f in findings if f["status"] != "normal"]

    if not abnormal:
        return "🟢 Low — all measured values within normal range"

    max_score = 0
    for f in abnormal:
        interp = (f["interpretation"] or "").lower()
        for keyword, weight in SEVERITY_WEIGHTS.items():
            if keyword in interp:
                max_score = max(max_score, weight)

    unique_systems = len(set(f["name"].split()[0] for f in abnormal))
    if unique_systems >= 3:
        max_score = min(max_score + 1, 3)

    if max_score >= 3:
        return "🔴 High — serious abnormalities detected; urgent medical review recommended"
    elif max_score == 2:
        return "🟡 Medium — moderate abnormalities detected; schedule a doctor's appointment"
    else:
        return "🟡 Low-Medium — mild abnormality detected; monitor and consult your doctor"


def build_lab_summary(findings: list[dict]) -> str:
    """Build a plain-text summary of extracted lab values for the LLM prompt."""
    if not findings:
        return "No standard lab values were detected in the report text."

    lines = ["Extracted and interpreted lab values:"]
    for f in findings:
        ref_range = ""
        if f["low_ref"] is not None and f["high_ref"] is not None:
            ref_range = f" (ref: {f['low_ref']}–{f['high_ref']} {f['unit']})"
        elif f["high_ref"] is not None:
            ref_range = f" (ref: <{f['high_ref']} {f['unit']})"
        elif f["low_ref"] is not None:
            ref_range = f" (ref: >{f['low_ref']} {f['unit']})"

        status_flag = f" ← {f['status']}" if f["status"] != "normal" else ""
        interp = f"\n    ↳ Suggests: {f['interpretation']}" if f["interpretation"] else ""
        lines.append(
            f"  • {f['name']}: {f['value']} {f['unit']}{ref_range}{status_flag}{interp}"
        )

    return "\n".join(lines)


# ── Chat History (ADDED) ──────────────────────────────────────────────────────
_report_chat_history = []


def add_to_report_history(user: str, assistant: str):
    """Save a (user summary, assistant reply) turn to report chat history."""
    _report_chat_history.append({
        "role": "user",
        "content": user
    })
    _report_chat_history.append({
        "role": "assistant",
        "content": assistant
    })


def get_report_chat_history() -> list[dict]:
    """Return the last 10 messages (5 turns) of report chat history."""
    return _report_chat_history[-10:]


def clear_report_chat_history():
    """Clear report chat history."""
    _report_chat_history.clear()
# ─────────────────────────────────────────────────────────────────────────────


def analyze_medical_report(report_text: str) -> str:
    """
    Analyze a medical report:
    1. Extract lab values with rule-based reference ranges
    2. If ALL values are normal → return a clean healthy report (NO LLM call)
    3. If abnormal values exist → ask LLM to predict likely diseases and severity
    """
    if len(report_text) > 12000:
        report_text = report_text[:12000] + "\n\n[... report truncated ...]"

    # Step 1: Rule-based extraction
    findings = extract_lab_values(report_text)
    severity = severity_from_findings(findings)
    lab_summary = build_lab_summary(findings)

    # ── Step 2: Early exit if NO abnormal values ──────────────────────────────
    abnormal = [f for f in findings if f["status"] != "normal"]

    if not findings:
        # Could not parse any lab values at all
        return (
            "## ✅ Report Analysis Complete\n\n"
            "No standard lab values were detected in this report. "
            "The document may use non-standard formatting, abbreviations, "
            "or the values may not match known test names.\n\n"
            "## ⚠️ Severity Assessment\n"
            "🟢 Low — No abnormal values detected\n\n"
            "## 📊 Smart Insights\n"
            "- Please share the report with your doctor for a manual review.\n"
            "- If you believe this is an error, try uploading a clearer scan.\n\n"
            "> Please consult a qualified doctor for confirmation."
        )

    if not abnormal:
        # All values detected and all are within normal range
        normal_lines = "\n".join(
            f"| {f['name']} | {f['value']} {f['unit']} | ✅ Normal |"
            for f in findings
        )
        return (
            "## ✅ Report is Normal — No Abnormalities Detected\n\n"
            "All detected lab values are **within standard reference ranges**. "
            "There are no abnormal findings that require diagnosis or treatment at this time.\n\n"
            "### 📋 Detected Lab Values\n\n"
            "| Test | Value | Status |\n"
            "|------|-------|--------|\n"
            f"{normal_lines}\n\n"
            "## ⚠️ Severity Assessment\n"
            f"{severity}\n\n"
            "## 📊 Smart Insights\n"
            "- Your report looks healthy based on all detected values.\n"
            "- Continue routine health check-ups as advised by your doctor.\n"
            "- Maintain a balanced diet, regular exercise, and adequate sleep.\n"
            "- No urgent action is required based on these results.\n\n"
            "> Please consult a qualified doctor for confirmation and for any symptoms you may be experiencing."
        )
    # ─────────────────────────────────────────────────────────────────────────

    # Step 3: LLM prediction — only reached when at least one abnormal value exists
    prompt = f"""
You are MedAgent, an expert AI medical assistant performing a clinical interpretation of a medical report.

You have been given:
1. The raw report text
2. A structured extraction of lab values with reference ranges and initial interpretations

Your job is to act as an expert clinician and:
- Identify the most likely disease(s) or condition(s) suggested by the lab pattern
- Assess severity (Low / Medium / High)
- Explain WHY each abnormal value points to the predicted condition
- Give evidence-based next steps and precautions
- Be specific — do NOT just list possibilities; rank the most likely diagnoses

IMPORTANT RULES:
- You MUST use the lab values provided to form your prediction
- ONLY discuss and diagnose based on the ABNORMAL values — do NOT mention or comment on normal values as potential disease indicators
- If lab values strongly suggest a disease, state it clearly even if not named in the report
- If multiple conditions are possible, rank them by likelihood
- For each predicted condition, cite which ABNORMAL lab value(s) support it
- For thyroid antibody results: distinguish between a MONITORING finding vs an URGENT finding.
  An isolated elevated Anti-TPO with no clinical symptoms is typically a MEDIUM severity finding
  requiring follow-up, NOT an emergency.
- Always end with: "Please consult a qualified doctor for confirmation and treatment."

---
{lab_summary}

---
Raw Report:
{report_text}

---
Return your analysis in EXACTLY this format:

## 🔬 Predicted Diagnosis (Most Likely → Less Likely)

## 🧬 Evidence from Abnormal Lab Values

## ⚠️ Severity Assessment
{severity}

## 💊 Possible Treatment Directions

## 🛡️ Immediate Precautions

## 📊 Smart Insights
- Plain-language summary for the patient
- What to monitor going forward
- Urgent warning signs to watch for
"""

    # ── Build messages with chat history (ADDED) ──────────────────────────────
    system_message = {
        "role": "system",
        "content": (
            "You are a senior clinical AI assistant. "
            "Your role is to interpret lab patterns and predict likely diagnoses from evidence. "
            "Be specific, evidence-based, and clinically accurate. "
            "ONLY comment on ABNORMAL values when forming diagnoses. "
            "Do NOT suggest conditions based on values that are within normal range. "
            "Never refuse to make a differential diagnosis when lab evidence supports it. "
            "Calibrate severity carefully: an isolated autoimmune antibody elevation in a young "
            "patient with no other abnormalities is typically Medium severity, not High."
        )
    }

    messages = [system_message] + get_report_chat_history() + [{"role": "user", "content": prompt}]
    # ─────────────────────────────────────────────────────────────────────────

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.2,
        max_tokens=2000
    )

    reply = response.choices[0].message.content

    # ── Save this turn to report chat history (ADDED) ─────────────────────────
    add_to_report_history(
        user=report_text[:200],   # store only a summary, not full text
        assistant=reply[:300]     # store only the start of the reply
    )
    # ─────────────────────────────────────────────────────────────────────────

    return reply