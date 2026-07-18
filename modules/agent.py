from modules.llm import get_llm_response

# ── Symptom database ──────────────────────────────────────────────────────────
# Format: symptom_keyword → (severity_level, description)
# severity_level: "high", "medium", "low"
SYMPTOMS = {
    # High severity — urgent
    "chest pain":            ("high",   "URGENT: Possible heart-related issue"),
    "shortness of breath":   ("high",   "URGENT: Possible respiratory or cardiac issue"),
    "difficulty breathing":  ("high",   "URGENT: Possible respiratory or cardiac issue"),
    "can't breathe":         ("high",   "URGENT: Possible respiratory emergency"),
    "unconscious":           ("high",   "URGENT: Loss of consciousness"),
    "stroke":                ("high",   "URGENT: Possible stroke"),
    "seizure":               ("high",   "URGENT: Neurological emergency"),
    "severe bleeding":       ("high",   "URGENT: Possible internal or external haemorrhage"),
    "overdose":              ("high",   "URGENT: Possible drug overdose"),
    "heart attack":          ("high",   "URGENT: Cardiac emergency"),
    "fainting":              ("high",   "Possible cardiac or neurological event"),
    "sudden vision loss":    ("high",   "URGENT: Possible retinal or neurological emergency"),

    # Medium severity — consult doctor soon
    "fever":                 ("medium", "Possible infection, flu, or viral illness"),
    "high temperature":      ("medium", "Possible infection or inflammatory condition"),
    "cough":                 ("medium", "Possible cold, flu, or respiratory infection"),
    "persistent cough":      ("medium", "Possible chronic respiratory condition"),
    "dizziness":             ("medium", "Possible dehydration, low BP, or vertigo"),
    "nausea":                ("medium", "Possible gastritis, infection, or food poisoning"),
    "vomiting":              ("medium", "Possible infection, food poisoning, or gastritis"),
    "diarrhoea":             ("medium", "Possible infection or gastrointestinal issue"),
    "abdominal pain":        ("medium", "Possible gastric, liver, or intestinal issue"),
    "back pain":             ("medium", "Possible musculoskeletal or renal issue"),
    "rash":                  ("medium", "Possible allergic reaction or skin infection"),
    "swelling":              ("medium", "Possible inflammation, allergy, or circulatory issue"),
    "joint pain":            ("medium", "Possible arthritis or autoimmune condition"),
    "frequent urination":    ("medium", "Possible diabetes or urinary tract infection"),
    "burning urination":     ("medium", "Possible urinary tract infection"),
    "blurred vision":        ("medium", "Possible diabetes, hypertension, or eye condition"),
    "palpitations":          ("medium", "Possible arrhythmia or anxiety"),
    "weight loss":           ("medium", "Possible thyroid disorder, diabetes, or cancer"),

    # Low severity — monitor
    "headache":              ("low",    "Possible migraine, stress, or dehydration"),
    "fatigue":               ("low",    "Possible weakness, anemia, or viral infection"),
    "body pain":             ("low",    "Possible viral fever or physical fatigue"),
    "weakness":              ("low",    "Possible fatigue, anemia, or low nutrients"),
    "sore throat":           ("low",    "Possible viral or bacterial throat infection"),
    "runny nose":            ("low",    "Possible cold or allergy"),
    "sneezing":              ("low",    "Possible allergy or common cold"),
    "mild fever":            ("low",    "Possible viral illness — monitor temperature"),
    "loss of appetite":      ("low",    "Possible viral illness or stress"),
    "bloating":              ("low",    "Possible gas, indigestion, or dietary issue"),
    "constipation":          ("low",    "Possible dietary issue or dehydration"),
    "dry skin":              ("low",    "Possible dehydration or skin condition"),
    "hair loss":             ("low",    "Possible thyroid issue, stress, or nutritional deficiency"),
    "insomnia":              ("low",    "Possible stress, anxiety, or lifestyle factor"),
    "anxiety":               ("low",    "Possible stress response or anxiety disorder"),
    "mood swings":           ("low",    "Possible hormonal or psychological factor"),
}

URGENT_KEYWORDS = [
    "chest pain", "can't breathe", "difficulty breathing",
    "unconscious", "stroke", "seizure", "severe bleeding",
    "overdose", "heart attack", "fainting", "sudden vision loss"
]

SYSTEM_PROMPT = """
You are MedAgent, an expert AI medical assistant.

Rules:
1. Analyze the reported symptoms carefully
2. Identify the most likely causes for each symptom
3. Detect overall severity (Low / Medium / High) based on symptom pattern
4. If symptoms suggest something dangerous, strongly advise urgent medical help
5. Suggest likely causes — do NOT give a final medical diagnosis
6. Provide clear precautions, home care tips, and when to see a doctor
7. Be empathetic, clear, and easy to understand for non-medical users
8. Always end with:
   'Please consult a qualified doctor for professional advice.'
"""


# ── Explainable AI logic ──────────────────────────────────────────────────────
def analyze_input(user_text: str):
    """
    Scan user input for known symptoms and compute a severity level.

    Returns:
        matched   — list of symptom keywords found
        severity  — emoji + label string
        reasoning — list of "symptom → risk explanation" strings
        reason    — short reason for the severity level chosen
    """
    user_text_lower = user_text.lower()
    matched = []
    reasoning = []
    severity_scores = []

    for symptom, (level, description) in SYMPTOMS.items():
        if symptom in user_text_lower:
            matched.append(symptom)
            reasoning.append(f"{symptom} → {description}")
            severity_scores.append(level)

    # Determine overall severity by the WORST single symptom
    if "high" in severity_scores:
        severity = "🔴 High"
        reason = "One or more high-risk / urgent symptoms detected"
    elif "medium" in severity_scores:
        severity = "🟡 Medium"
        reason = "Moderate-risk symptoms detected — please consult a doctor soon"
    elif "low" in severity_scores:
        severity = "🟢 Low"
        reason = "Only mild symptoms detected — monitor and rest"
    else:
        severity = "⚪ Unknown"
        reason = "No recognised symptoms detected — please describe in more detail"

    return matched, severity, reasoning, reason


def is_urgent(text: str) -> bool:
    return any(k in text.lower() for k in URGENT_KEYWORDS)


# ── Main agent ────────────────────────────────────────────────────────────────
def run_agent(user_query: str, history: list[dict]) -> str:
    """
    Run the symptom analysis agent:
    1. Parse severity from rule-based symptom list
    2. Inject urgency note if needed
    3. Query the LLM with full conversation history
    4. Return formatted response
    """
    matched, severity, reasoning, reason = analyze_input(user_query)

    urgency_note = ""
    if is_urgent(user_query):
        urgency_note = (
            "🚨 **URGENT: Please call emergency services (112 / 911) immediately "
            "or go to the nearest emergency department.**\n\n"
        )

    history.append({
        "role": "user",
        "content": user_query
    })

    # Keep last 10 messages for context window efficiency
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-10:]

    reply = get_llm_response(messages)

    history.append({
        "role": "assistant",
        "content": reply
    })

    final_response = f"""
## 🚨 Severity Level
{severity}

{urgency_note}
## 🧾 Medical Advice
{reply}

---
*Please consult a qualified doctor for professional advice.*
"""

    return final_response
