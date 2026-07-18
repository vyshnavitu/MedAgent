# modules/metrics.py
# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Metrics for MedAgent
# ADD-ONLY: This module does NOT touch any existing logic.
# It only records events and exposes aggregated stats.
# ─────────────────────────────────────────────────────────────────────────────

import time
import json
import os
from datetime import datetime
from collections import defaultdict

METRICS_FILE = "metrics_log.json"

# ── In-memory store (also persisted to JSON) ──────────────────────────────────
_metrics = {
    "chat": {
        "total_queries": 0,
        "total_symptoms_matched": 0,
        "total_symptoms_unmatched": 0,
        "severity_distribution": {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
        "llm_response_times_ms": [],          # list of floats
        "urgent_cases_triggered": 0,
        "queries_with_no_symptoms": 0,
    },
    "report": {
        "total_reports_analyzed": 0,
        "total_lab_values_extracted": 0,
        "total_abnormal_values": 0,
        "total_normal_values": 0,
        "severity_distribution": {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
        "llm_response_times_ms": [],
        "short_circuit_normal": 0,            # times LLM was skipped (all normal)
        "ocr_used": 0,
        "pdf_uploads": 0,
        "image_uploads": 0,
        "lab_test_frequency": defaultdict(int),  # which tests appear most
    },
    "session": {
        "start_time": datetime.now().isoformat(),
        "total_interactions": 0,
    }
}


# ── Persistence helpers ───────────────────────────────────────────────────────

def _load_metrics():
    """Load persisted metrics from disk (called once at import)."""
    global _metrics
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                saved = json.load(f)
            # Merge saved values into the in-memory store
            for section in ("chat", "report", "session"):
                if section in saved:
                    for k, v in saved[section].items():
                        if k == "lab_test_frequency":
                            _metrics["report"]["lab_test_frequency"].update(v)
                        else:
                            _metrics[section][k] = v
        except Exception:
            pass  # If file is corrupt, start fresh


def save_metrics():
    """Persist current metrics to disk."""
    try:
        serialisable = json.loads(json.dumps(_metrics, default=lambda x: dict(x) if isinstance(x, defaultdict) else str(x)))
        with open(METRICS_FILE, "w") as f:
            json.dump(serialisable, f, indent=2)
    except Exception:
        pass


_load_metrics()


# ── Timer context manager ─────────────────────────────────────────────────────

class Timer:
    """Usage:  with Timer() as t: ...  then t.elapsed_ms"""
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


# ── Chat metrics ──────────────────────────────────────────────────────────────

def record_chat_query(matched: list, severity: str, response_time_ms: float, is_urgent: bool):
    """
    Call this after run_agent() returns.
    matched       — list of symptom keywords found (from analyze_input)
    severity      — severity string e.g. '🔴 High'
    response_time_ms — LLM call duration in milliseconds
    is_urgent     — bool from is_urgent()
    """
    c = _metrics["chat"]
    c["total_queries"] += 1
    _metrics["session"]["total_interactions"] += 1

    # Symptom match rate
    if matched:
        c["total_symptoms_matched"] += len(matched)
    else:
        c["queries_with_no_symptoms"] += 1

    # Severity
    for label in ("High", "Medium", "Low"):
        if label in severity:
            c["severity_distribution"][label] += 1
            break
    else:
        c["severity_distribution"]["Unknown"] += 1

    # Timing
    c["llm_response_times_ms"].append(round(response_time_ms, 2))

    # Urgency
    if is_urgent:
        c["urgent_cases_triggered"] += 1

    save_metrics()


def record_chat_no_match(user_text: str):
    """Increment unmatched symptom counter when no keywords found."""
    _metrics["chat"]["total_symptoms_unmatched"] += 1
    save_metrics()


# ── Report metrics ────────────────────────────────────────────────────────────

def record_report_analysis(
    findings: list,
    severity: str,
    response_time_ms: float,
    was_short_circuit: bool,
    file_type: str,           # "pdf" or "image"
    ocr_used: bool
):
    """
    Call this after analyze_medical_report() returns.
    findings          — list of dicts from extract_lab_values()
    severity          — severity string
    response_time_ms  — total analysis time in ms
    was_short_circuit — True if LLM was skipped (all-normal early exit)
    file_type         — "pdf" or "image"
    ocr_used          — True if OCR was invoked
    """
    r = _metrics["report"]
    r["total_reports_analyzed"] += 1
    _metrics["session"]["total_interactions"] += 1

    abnormal = [f for f in findings if f["status"] != "normal"]
    normal   = [f for f in findings if f["status"] == "normal"]

    r["total_lab_values_extracted"] += len(findings)
    r["total_abnormal_values"]      += len(abnormal)
    r["total_normal_values"]        += len(normal)

    # Severity
    for label in ("High", "Medium", "Low"):
        if label in severity:
            r["severity_distribution"][label] += 1
            break
    else:
        r["severity_distribution"]["Unknown"] += 1

    # Timing
    r["llm_response_times_ms"].append(round(response_time_ms, 2))

    # Shortcuts / OCR
    if was_short_circuit:
        r["short_circuit_normal"] += 1
    if ocr_used:
        r["ocr_used"] += 1

    # File type
    if file_type == "pdf":
        r["pdf_uploads"] += 1
    else:
        r["image_uploads"] += 1

    # Test frequency
    for f in findings:
        r["lab_test_frequency"][f["name"]] += 1

    save_metrics()


# ── Computed aggregate stats ──────────────────────────────────────────────────

def _avg(lst):
    return round(sum(lst) / len(lst), 1) if lst else 0.0

def _p95(lst):
    if not lst:
        return 0.0
    s = sorted(lst)
    idx = max(0, int(len(s) * 0.95) - 1)
    return round(s[idx], 1)


def get_chat_stats() -> dict:
    c = _metrics["chat"]
    total = c["total_queries"]
    matched = c["total_symptoms_matched"]
    no_match = c["queries_with_no_symptoms"]
    return {
        "Total Queries": total,
        "Queries with Symptoms Detected": total - no_match,
        "Queries with No Symptom Match": no_match,
        "Symptom Detection Rate (%)": round(((total - no_match) / total * 100), 1) if total else 0,
        "Total Symptoms Matched": matched,
        "Avg Symptoms per Query": round(matched / max(total - no_match, 1), 1),
        "Urgent Cases Triggered": c["urgent_cases_triggered"],
        "Urgent Case Rate (%)": round(c["urgent_cases_triggered"] / total * 100, 1) if total else 0,
        "Severity — High": c["severity_distribution"]["High"],
        "Severity — Medium": c["severity_distribution"]["Medium"],
        "Severity — Low": c["severity_distribution"]["Low"],
        "Severity — Unknown": c["severity_distribution"]["Unknown"],
        "Avg LLM Response Time (ms)": _avg(c["llm_response_times_ms"]),
        "P95 LLM Response Time (ms)": _p95(c["llm_response_times_ms"]),
        "Min LLM Response Time (ms)": round(min(c["llm_response_times_ms"]), 1) if c["llm_response_times_ms"] else 0,
        "Max LLM Response Time (ms)": round(max(c["llm_response_times_ms"]), 1) if c["llm_response_times_ms"] else 0,
    }


def get_report_stats() -> dict:
    r = _metrics["report"]
    total = r["total_reports_analyzed"]
    extracted = r["total_lab_values_extracted"]
    return {
        "Total Reports Analyzed": total,
        "PDF Uploads": r["pdf_uploads"],
        "Image Uploads": r["image_uploads"],
        "OCR Invocations": r["ocr_used"],
        "Total Lab Values Extracted": extracted,
        "Total Abnormal Values": r["total_abnormal_values"],
        "Total Normal Values": r["total_normal_values"],
        "Avg Lab Values per Report": round(extracted / total, 1) if total else 0,
        "Abnormal Value Rate (%)": round(r["total_abnormal_values"] / max(extracted, 1) * 100, 1),
        "Normal Report Short-circuits": r["short_circuit_normal"],
        "Short-circuit Rate (%)": round(r["short_circuit_normal"] / total * 100, 1) if total else 0,
        "Severity — High": r["severity_distribution"]["High"],
        "Severity — Medium": r["severity_distribution"]["Medium"],
        "Severity — Low": r["severity_distribution"]["Low"],
        "Avg LLM Response Time (ms)": _avg(r["llm_response_times_ms"]),
        "P95 LLM Response Time (ms)": _p95(r["llm_response_times_ms"]),
        "Min LLM Response Time (ms)": round(min(r["llm_response_times_ms"]), 1) if r["llm_response_times_ms"] else 0,
        "Max LLM Response Time (ms)": round(max(r["llm_response_times_ms"]), 1) if r["llm_response_times_ms"] else 0,
        "Top 5 Most Frequent Lab Tests": dict(
            sorted(r["lab_test_frequency"].items(), key=lambda x: x[1], reverse=True)[:5]
        ),
    }


def get_session_stats() -> dict:
    return {
        "Session Start": _metrics["session"]["start_time"],
        "Total Interactions This Session": _metrics["session"]["total_interactions"],
    }


def reset_metrics():
    """Wipe all metrics (called from the dashboard Reset button)."""
    global _metrics
    _metrics = {
        "chat": {
            "total_queries": 0,
            "total_symptoms_matched": 0,
            "total_symptoms_unmatched": 0,
            "severity_distribution": {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
            "llm_response_times_ms": [],
            "urgent_cases_triggered": 0,
            "queries_with_no_symptoms": 0,
        },
        "report": {
            "total_reports_analyzed": 0,
            "total_lab_values_extracted": 0,
            "total_abnormal_values": 0,
            "total_normal_values": 0,
            "severity_distribution": {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
            "llm_response_times_ms": [],
            "short_circuit_normal": 0,
            "ocr_used": 0,
            "pdf_uploads": 0,
            "image_uploads": 0,
            "lab_test_frequency": defaultdict(int),
        },
        "session": {
            "start_time": datetime.now().isoformat(),
            "total_interactions": 0,
        }
    }
    if os.path.exists(METRICS_FILE):
        os.remove(METRICS_FILE)