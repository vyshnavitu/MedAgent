import streamlit as st
import fitz
import json
import os
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from modules.agent import run_agent, analyze_input
from modules.qa_chain import analyze_medical_report, extract_lab_values, severity_from_findings

# ── METRICS IMPORT (additive only) ───────────────────────────────────────────
from modules.metrics import (
    Timer,
    record_chat_query,
    record_report_analysis,
    get_chat_stats,
    get_report_stats,
    get_session_stats,
    reset_metrics,
)
# ─────────────────────────────────────────────────────────────────────────────

# =========================================================
# TESSERACT + POPPLER SETUP
# =========================================================
pytesseract.pytesseract.tesseract_cmd = r"D:\Tesseract-OCR\tesseract.exe"
os.environ["PATH"] += os.pathsep + r"D:\poppler\poppler-25.12.0\Library\bin"

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="MedAgent",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 MedAgent — AI Medical Assistant")
st.warning(
    "⚠️ This AI does not replace professional medical advice. "
    "Always consult a qualified doctor."
)

# =========================================================
# HELPER: Highlight matched symptoms in chat
# =========================================================
def highlight_text(text: str, words: list[str]) -> str:
    for word in words:
        text = text.replace(word, f"**:red[{word}]**")
    return text

# =========================================================
# HELPER: Render lab findings as a styled table
# =========================================================
def render_lab_table(findings: list[dict]):
    if not findings:
        st.info("No standard lab values were automatically detected in the text.")
        return
    rows = []
    for f in findings:
        ref = ""
        if f["low_ref"] is not None and f["high_ref"] is not None:
            ref = f"{f['low_ref']} – {f['high_ref']} {f['unit']}"
        elif f["high_ref"] is not None:
            ref = f"< {f['high_ref']} {f['unit']}"
        elif f["low_ref"] is not None:
            ref = f"> {f['low_ref']} {f['unit']}"

        status = f["status"]
        if status == "LOW":
            badge = "🔵 LOW"
        elif status == "HIGH":
            badge = "🔴 HIGH"
        else:
            badge = "✅ Normal"

        rows.append({
            "Test": f["name"],
            "Value": f"{f['value']} {f['unit']}",
            "Reference Range": ref,
            "Status": badge,
            "Suggests": f["interpretation"] or "—",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

# =========================================================
# LOAD CHAT HISTORY
# =========================================================
if "agent_messages" not in st.session_state:
    if os.path.exists("chat_history.json"):
        with open("chat_history.json", "r") as f:
            st.session_state.agent_messages = json.load(f)
    else:
        st.session_state.agent_messages = []

# =========================================================
# TABS  ← added tab3 for metrics; tab1 & tab2 unchanged
# =========================================================
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📄 Report Analyzer", "📊 Metrics Dashboard"])

# =========================================================
# TAB 1 — SYMPTOM CHAT  (original logic UNTOUCHED)
# =========================================================
with tab1:
    st.caption("Describe your symptoms in plain language.")

    # Show previous messages
    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "Enter symptoms (e.g. 'I have a fever, headache and fatigue')..."
    ):
        matched, severity, reasoning, reason = analyze_input(prompt)

        with st.chat_message("user"):
            st.markdown(highlight_text(prompt, matched))

        with st.chat_message("assistant"):
            with st.spinner("Analyzing symptoms..."):
                # ── METRICS: time the LLM call ────────────────────────────
                from modules.agent import is_urgent as _is_urgent
                with Timer() as _t:
                    response = run_agent(prompt, st.session_state.agent_messages)
                record_chat_query(
                    matched=matched,
                    severity=severity,
                    response_time_ms=_t.elapsed_ms,
                    is_urgent=_is_urgent(prompt),
                )
                # ─────────────────────────────────────────────────────────
            st.markdown(response)

            # Severity banner
            st.markdown(f"### 🚨 Severity Level: {severity}")
            if "High" in severity or "🔴" in severity:
                st.error("⚠️ This may be serious. Seek medical help immediately.")
            elif "Medium" in severity or "🟡" in severity:
                st.warning("⚠️ Please monitor symptoms and consult a doctor soon.")
            elif "Low" in severity or "🟢" in severity:
                st.success("✅ Symptoms appear mild. Continue monitoring.")
            else:
                st.info("ℹ️ Could not determine severity. Please describe symptoms in more detail.")

            # Explainable AI expander
            with st.expander("🧠 Why this answer?"):
                st.markdown("#### 🔍 Detected Symptoms")
                if matched:
                    for m in matched:
                        st.write(f"• {m}")
                else:
                    st.write("No major symptoms detected from the keyword list.")
                st.markdown("#### ⚖️ Severity Reason")
                st.write(reason)
                st.markdown("#### 🧠 Risk Analysis")
                if reasoning:
                    for r in reasoning:
                        st.write("•", r)
                else:
                    st.write("No major risk indicators found.")

        # Persist chat history
        with open("chat_history.json", "w") as f:
            json.dump(st.session_state.agent_messages, f, indent=2)

    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        if st.button("🔄 Reset Chat"):
            st.session_state.agent_messages = []
            if os.path.exists("chat_history.json"):
                os.remove("chat_history.json")
            st.rerun()
        st.download_button(
            "📥 Download Chat History",
            data=json.dumps(st.session_state.agent_messages, indent=2),
            file_name="chat_history.json",
            mime="application/json"
        )

# =========================================================
# TAB 2 — REPORT ANALYZER  (original logic UNTOUCHED)
# =========================================================
with tab2:
    st.caption(
        "Upload a medical report (PDF or image). "
        "MedAgent will extract lab values, and — only if abnormalities are found — "
        "predict possible conditions and assess severity."
    )

    uploaded_file = st.file_uploader(
        "Upload Medical Report", type=["pdf", "png", "jpg", "jpeg"]
    )

    if uploaded_file:
        file_type = uploaded_file.type
        text = ""
        _ocr_used = False      # ← metrics flag (does not affect any logic)
        _file_category = "pdf" if "pdf" in file_type else "image"  # ← metrics flag

        # ── PDF ──────────────────────────────────────────
        if "pdf" in file_type:
            pdf_bytes = uploaded_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = "\n".join([page.get_text("text") for page in doc])

            # OCR fallback for scanned PDFs
            if len(text.strip()) < 500:
                st.warning("⚠️ Very little text found. PDF may be scanned. Running OCR...")
                try:
                    images = convert_from_bytes(pdf_bytes)
                    ocr_text = ""
                    for img in images[:5]:
                        gray = img.convert("L")
                        ocr_text += pytesseract.image_to_string(
                            gray, lang="eng", config="--oem 3 --psm 6"
                        )
                    text = ocr_text
                    _ocr_used = True   # ← metrics flag
                    st.success("✅ OCR completed successfully.")
                except Exception as e:
                    st.error(f"OCR failed: {str(e)}")
            else:
                st.success("✅ PDF processed successfully.")

        # ── Image ─────────────────────────────────────────
        else:
            st.info("🖼️ Image detected. Running OCR...")
            try:
                image = Image.open(uploaded_file)
                gray = image.convert("L")
                text = pytesseract.image_to_string(
                    gray, lang="eng", config="--oem 3 --psm 6"
                )
                _ocr_used = True   # ← metrics flag
                st.success("✅ Image OCR completed successfully.")
            except Exception as e:
                st.error(f"Image OCR failed: {str(e)}")

        # ── Extracted Text Preview ────────────────────────
        with st.expander("📄 View Extracted Text"):
            if text.strip():
                st.text(text[:3000] + ("..." if len(text) > 3000 else ""))
            else:
                st.error("❌ No readable text extracted from the file.")

        # ── Auto Lab Value Detection ──────────────────────
        if text.strip():
            st.subheader("🧪 Detected Lab Values")
            st.caption(
                "Automatically extracted from your report and checked "
                "against standard reference ranges."
            )
            findings = extract_lab_values(text)
            render_lab_table(findings)

            if findings:
                overall_severity = severity_from_findings(findings)
                abnormal = [f for f in findings if f["status"] != "normal"]
                if abnormal:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Abnormal Values Found", len(abnormal))
                    with col2:
                        st.metric(
                            "Overall Severity",
                            overall_severity.split("—")[0].strip()
                        )
                else:
                    st.success(
                        "✅ All detected values are within normal reference ranges. "
                        "No abnormalities found."
                    )

            # ── Full AI Analysis ──────────────────────────
            st.divider()
            if st.button(
                "🔍 Run Full AI Analysis",
                type="primary",
                disabled=not text.strip()
            ):
                if not text.strip():
                    st.error("Cannot analyze — no text was extracted from the file.")
                else:
                    with st.spinner(
                        "MedAgent is analyzing your report. This may take a moment..."
                    ):
                        # ── METRICS: time the full analysis ──────────────
                        with Timer() as _rt:
                            result = analyze_medical_report(text)

                        # Compute metrics inputs (does not change result)
                        _findings_for_metrics = extract_lab_values(text)
                        _abnormal_for_metrics = [f for f in _findings_for_metrics if f["status"] != "normal"]
                        _sev_for_metrics = severity_from_findings(_findings_for_metrics)
                        _short_circuit = (len(_findings_for_metrics) > 0 and len(_abnormal_for_metrics) == 0)
                        record_report_analysis(
                            findings=_findings_for_metrics,
                            severity=_sev_for_metrics,
                            response_time_ms=_rt.elapsed_ms,
                            was_short_circuit=_short_circuit,
                            file_type=_file_category,
                            ocr_used=_ocr_used,
                        )
                        # ─────────────────────────────────────────────────

                    st.markdown(result)

                    # Re-check findings for the severity banner
                    findings = extract_lab_values(text)
                    abnormal = [f for f in findings if f["status"] != "normal"]
                    overall_severity = severity_from_findings(findings)
                    st.divider()
                    if abnormal:
                        if "🔴" in overall_severity:
                            st.error(
                                f"⚠️ **{len(abnormal)} serious abnormal value(s) detected.** "
                                "Please consult a doctor urgently."
                            )
                        elif "🟡" in overall_severity:
                            st.warning(
                                f"⚠️ **{len(abnormal)} abnormal value(s) detected.** "
                                "Schedule an appointment with your doctor."
                            )
                        else:
                            st.info(
                                f"ℹ️ **{len(abnormal)} mild abnormality detected.** "
                                "Monitor and consult your doctor if symptoms persist."
                            )
                    else:
                        st.success(
                            "✅ All lab values are within normal range. "
                            "No diagnosis or treatment indicated."
                        )

            # How it works
            with st.expander("🧠 How this analysis was performed"):
                st.markdown("""
**Step 1 — Text extraction**
- Digital PDFs: direct text layer extraction via PyMuPDF
- Scanned PDFs / images: OCR via Tesseract

**Step 2 — Rule-based lab value detection**
- Regex patterns detect 25+ common lab tests (CBC, metabolic panel, renal, liver, thyroid, electrolytes)
- Each value is compared against standard clinical reference ranges
- Abnormal values are mapped to likely conditions *before* the LLM is involved

**Step 3 — Normal report short-circuit**
- If ALL detected values are within normal range, the analysis stops here
- A clean "All Normal" summary is returned — no LLM call is made, no diagnosis is predicted

**Step 4 — AI-powered clinical interpretation (abnormal reports only)**
- The pre-parsed ABNORMAL lab findings are passed to the LLM alongside the raw report
- The model acts as a clinical reasoner: it ranks likely diagnoses by evidence strength,
  explains *why* each value supports a condition, and suggests next steps
- Temperature is set low (0.2) for consistent, factual output
- Normal values are explicitly excluded from the diagnosis reasoning

**Step 5 — Severity assessment**
- Computed from the number and type of abnormal values using deterministic rules
- Not dependent on LLM output, so it is fast and reproducible

---
*This tool is for informational purposes only. It does not replace a qualified medical professional.*
""")

    elif not uploaded_file:
        st.info("Upload a file above to begin analysis.")


# =========================================================
# TAB 3 — METRICS DASHBOARD  (fully new, additive only)
# =========================================================
with tab3:
    st.subheader("📊 MedAgent — Evaluation Metrics Dashboard")
    st.caption(
        "Live metrics collected during this session (and persisted across restarts). "
        "No patient data is stored — only aggregate counts and timings."
    )

    # ── Session overview ──────────────────────────────────────────────────────
    sess = get_session_stats()
    st.markdown("### 🕐 Session Overview")
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Session Started", sess["Session Start"][:19].replace("T", " "))
    col_s2.metric("Total Interactions", sess["Total Interactions This Session"])

    st.divider()

    # ── Chat metrics ──────────────────────────────────────────────────────────
    st.markdown("### 💬 Symptom Chat Metrics")
    chat = get_chat_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Queries",          chat["Total Queries"])
    c2.metric("Symptom Detection Rate", f"{chat['Symptom Detection Rate (%)']}%")
    c3.metric("Urgent Cases",           chat["Urgent Cases Triggered"])
    c4.metric("Urgent Case Rate",       f"{chat['Urgent Case Rate (%)']}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Avg LLM Time (ms)",  chat["Avg LLM Response Time (ms)"])
    c6.metric("P95 LLM Time (ms)",  chat["P95 LLM Response Time (ms)"])
    c7.metric("Min LLM Time (ms)",  chat["Min LLM Response Time (ms)"])
    c8.metric("Max LLM Time (ms)",  chat["Max LLM Response Time (ms)"])

    st.markdown("#### Severity Distribution — Chat")
    sev_cols = st.columns(4)
    sev_cols[0].metric("🔴 High",    chat["Severity — High"])
    sev_cols[1].metric("🟡 Medium",  chat["Severity — Medium"])
    sev_cols[2].metric("🟢 Low",     chat["Severity — Low"])
    sev_cols[3].metric("⚪ Unknown",  chat["Severity — Unknown"])

    with st.expander("📋 Full Chat Metrics Table"):
        chat_display = {k: v for k, v in chat.items()}
        st.table(chat_display)

    st.divider()

    # ── Report metrics ─────────────────────────────────────────────────────────
    st.markdown("### 📄 Report Analyzer Metrics")
    rep = get_report_stats()

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Total Reports",          rep["Total Reports Analyzed"])
    r2.metric("Lab Values Extracted",   rep["Total Lab Values Extracted"])
    r3.metric("Abnormal Values",        rep["Total Abnormal Values"])
    r4.metric("Abnormal Rate",          f"{rep['Abnormal Value Rate (%)']}%")

    r5, r6, r7, r8 = st.columns(4)
    r5.metric("PDF Uploads",            rep["PDF Uploads"])
    r6.metric("Image Uploads",          rep["Image Uploads"])
    r7.metric("OCR Invocations",        rep["OCR Invocations"])
    r8.metric("Normal Short-circuits",  rep["Normal Report Short-circuits"])

    r9, r10, r11, r12 = st.columns(4)
    r9.metric("Avg Analysis Time (ms)", rep["Avg LLM Response Time (ms)"])
    r10.metric("P95 Analysis Time (ms)",rep["P95 LLM Response Time (ms)"])
    r11.metric("Min Analysis Time (ms)",rep["Min LLM Response Time (ms)"])
    r12.metric("Max Analysis Time (ms)",rep["Max LLM Response Time (ms)"])

    st.markdown("#### Severity Distribution — Reports")
    rsev = st.columns(4)
    rsev[0].metric("🔴 High",   rep["Severity — High"])
    rsev[1].metric("🟡 Medium", rep["Severity — Medium"])
    rsev[2].metric("🟢 Low",    rep["Severity — Low"])

    if rep["Top 5 Most Frequent Lab Tests"]:
        st.markdown("#### 🏆 Top 5 Most Frequently Detected Lab Tests")
        for test, count in rep["Top 5 Most Frequent Lab Tests"].items():
            st.write(f"• **{test}** — detected in {count} report(s)")

    with st.expander("📋 Full Report Metrics Table"):
        rep_display = {k: v for k, v in rep.items() if k != "Top 5 Most Frequent Lab Tests"}
        st.table(rep_display)

    st.divider()

    # ── Export & Reset ─────────────────────────────────────────────────────────
    st.markdown("### 🛠️ Metrics Management")
    col_exp, col_rst = st.columns(2)

    with col_exp:
        all_metrics = {
            "session": get_session_stats(),
            "chat": get_chat_stats(),
            "report": get_report_stats(),
        }
        st.download_button(
            label="📥 Export Metrics as JSON",
            data=json.dumps(all_metrics, indent=2),
            file_name="medagent_metrics.json",
            mime="application/json",
        )

    with col_rst:
        if st.button("🗑️ Reset All Metrics", type="secondary"):
            reset_metrics()
            st.success("✅ All metrics have been reset.")
            st.rerun()