"""
AI-Assisted Analysis (Simulated RAG Evidence Retrieval) Service for NIRIKSH
Team CODE RED — Smart India Hackathon 2026

Architecture Alignment (SIH26262 PPT):
- Document Processing extracts text, fields and page references using PDF parsing / OCR.
- AI-Assisted Analysis (RAG) retrieves relevant AICTE Approval Process Handbook (APH) passages
  and suggests possible mismatches for officer attention.
- Deterministic Rule Engine evaluates configured rules independently.
- Findings Summary combines rule results and AI suggestions with supporting evidence.
- Authorised Officer reviews the findings and makes the final decision.

Important Governance Guardrail:
AI suggestions are advisory retrieval hints over a prototype AICTE handbook passage corpus.
They are NEVER presented as verified regulatory facts and NEVER make approval or rejection decisions.
"""

from datetime import datetime
from typing import Any, Dict, List


# Curated Prototype Corpus of AICTE Approval Process Handbook (APH 2024–27) Clauses for RAG Retrieval
AICTE_APH_DEMO_CORPUS = {
    "CLAUSE_FIRE_NOC": {
        "clause_id": "AICTE APH 2024–27, Chapter VII, Clause 7.4",
        "title": "Fire and Life Safety NOC Validity Requirement",
        "passage": (
            "All Applicant Institutions seeking Extension of Approval (EoA) or New Course addition "
            "shall upload a valid Fire Safety Certificate issued by the Competent State/Municipal Fire "
            "Authority explicitly stating the date of issue and validity period covering the applied Academic Year."
        ),
    },
    "CLAUSE_LAND_CLU": {
        "clause_id": "AICTE APH 2024–27, Chapter I, Clause 1.6.2",
        "title": "Land Use Conversion (CLU) & Contiguous Land Title",
        "passage": (
            "For establishment of a new Technical Institution, undisputed ownership and non-agricultural "
            "Land Use Conversion (CLU) certificate issued by the Competent Revenue Authority must be "
            "submitted in Annexure-I prior to Expert Visit Committee (EVC) dispatch."
        ),
    },
    "CLAUSE_FACULTY_CADRE": {
        "clause_id": "AICTE APH 2024–27, Chapter VII, Clause 7.2",
        "title": "Faculty Cadre Ratio (1 : 2 : 6) & Student-Faculty Ratio Norms",
        "passage": (
            "Institutions offering UG Degree Programmes in Engineering & Technology shall maintain a "
            "Student-Faculty Ratio (SFR) not exceeding 1:20 and a cadre ratio of 1 Professor : 2 Associate "
            "Professors : 6 Assistant Professors. Offer letters without physical joining reports require verification."
        ),
    },
    "CLAUSE_LAB_EVC": {
        "clause_id": "AICTE APH 2024–27, Chapter II, Clause 2.9",
        "title": "Laboratory Readiness & Expert Visit Committee (EVC) Scrutiny",
        "passage": (
            "Where an existing institution applies for a New Programme/Course or Increase in Intake, "
            "availability of specialized laboratory equipment, licensed software tools, and computing nodes "
            "shall be verified by an Expert Visit Committee (EVC) before final approval."
        ),
    },
    "CLAUSE_BUILT_UP_AREA": {
        "clause_id": "AICTE APH 2024–27, Annexure-III, Clause 3.1",
        "title": "Instructional and Built-Up Carpet Area Norms",
        "passage": (
            "Total built-up instructional, administrative, and amenities area must equal or exceed the "
            "normative sq. meter requirement calculated from sanctioned intake across all active divisions, "
            "supported by a valid Municipal Occupancy Certificate (OC)."
        ),
    },
}


def generate_ai_rag_suggestions(case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retrieves relevant AICTE handbook passages against the case's extracted fields and documents,
    returning separate AI-Assisted Analysis (RAG) suggestions.
    Every suggestion is explicitly marked as an AI suggestion (not a verified regulatory fact).
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    fields = case_data.get("extracted_fields", [])
    fields_by_key = {f.get("field_key"): f for f in fields if f.get("field_key")}
    docs = case_data.get("documents", [])
    evc = case_data.get("evc_inspection") or case_data.get("evc") or {}

    suggestions: List[Dict[str, Any]] = []

    # 1. Check statutory Fire NOC / Land CLU evidence across pages
    noc_field = fields_by_key.get("fire_safety_noc_validity")
    clu_field = fields_by_key.get("land_clu_cert")

    if clu_field and (clu_field.get("status") == "MISSING" or not clu_field.get("value")):
        corpus = AICTE_APH_DEMO_CORPUS["CLAUSE_LAND_CLU"]
        page_num = clu_field.get("page_number") or 2
        suggestions.append(
            {
                "suggestion_id": "RAG-SUG-01",
                "finding_title": "AI Suggestion: Possible Land Conversion (CLU) Order Omission",
                "status": "Possible deficiency",
                "short_explanation": (
                    "Retrieved APH Clause 1.6.2 requires a Revenue Authority CLU order number for new "
                    "institutions; Page 2 text shows the CLU reference field is blank."
                ),
                "source_page": page_num,
                "source_document": "Application Form / Annexure-I",
                "evidence_quote": clu_field.get("source_snippet") or "Land Conversion (CLU): [MISSING]",
                "handbook_citation": corpus["clause_id"],
                "retrieved_passage": corpus["passage"],
                "recommended_action": "Verify Annexure-I and request certified Land Use Conversion (CLU) certificate from the institution.",
                "source_type": "AI_RAG_SUGGESTION",
                "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
                "evaluated_at": now_str,
            }
        )
    elif noc_field and (
        noc_field.get("status") == "MISSING"
        or "MISSING" in str(noc_field.get("extracted_value") or "").upper()
    ):
        corpus = AICTE_APH_DEMO_CORPUS["CLAUSE_FIRE_NOC"]
        page_num = noc_field.get("page_number") or 2
        suggestions.append(
            {
                "suggestion_id": "RAG-SUG-01",
                "finding_title": "AI Suggestion: Provisional Fire NOC Missing Expiration Date",
                "status": "Possible deficiency",
                "short_explanation": (
                    "Cross-checking Page 2 against APH Clause 7.4 indicates Fire Safety NOC reference "
                    "FS-UP-2024-0918 is listed as a provisional renewal without an explicit expiration date."
                ),
                "source_page": page_num,
                "source_document": "Consolidated Application Form (Part II)",
                "evidence_quote": noc_field.get("source_snippet")
                or "Fire Safety NOC Validity Date [MISSING IN SUBMISSION — BLANK FIELD ON FORM]",
                "handbook_citation": corpus["clause_id"],
                "retrieved_passage": corpus["passage"],
                "recommended_action": "Request clarification from institution with valid Fire Safety NOC covering AY 2026-27.",
                "source_type": "AI_RAG_SUGGESTION",
                "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
                "evaluated_at": now_str,
            }
        )
    else:
        corpus = AICTE_APH_DEMO_CORPUS["CLAUSE_FIRE_NOC"]
        noc_val = (noc_field.get("extracted_value") if noc_field else "Verified on Page 2") or "Verified on Page 2"
        suggestions.append(
            {
                "suggestion_id": "RAG-SUG-01",
                "finding_title": "AI Suggestion: Statutory Fire & Safety NOC Coverage",
                "status": "Compliant / complete under configured checks",
                "short_explanation": (
                    f"Retrieved APH Clause 7.4 aligns with extracted statutory safety validity ({noc_val})."
                ),
                "source_page": (noc_field.get("page_number") or 2) if noc_field else 2,
                "source_document": "Application Form (Part II)",
                "evidence_quote": noc_field.get("source_snippet", str(noc_val)) if noc_field else str(noc_val),
                "handbook_citation": corpus["clause_id"],
                "retrieved_passage": corpus["passage"],
                "recommended_action": "Officer may confirm certificate authenticity in Document Review.",
                "source_type": "AI_RAG_SUGGESTION",
                "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
                "evaluated_at": now_str,
            }
        )

    # 2. Check Faculty Cadre / Specialized Lab evidence on Page 3
    prof_field = (
        fields_by_key.get("professor_cadre")
        or fields_by_key.get("vlsi_eda_licenses")
        or fields_by_key.get("calculated_sfr")
    )
    if prof_field and (
        prof_field.get("status") == "REVIEW_REQUIRED"
        or "PENDING" in str(prof_field.get("extracted_value") or "").upper()
        or "PROCUREMENT" in str(prof_field.get("extracted_value") or "").upper()
    ):
        corpus = AICTE_APH_DEMO_CORPUS["CLAUSE_FACULTY_CADRE"]
        p_val = prof_field.get("extracted_value") or prof_field.get("value") or ""
        p_page = prof_field.get("page_number") or 3
        suggestions.append(
            {
                "suggestion_id": "RAG-SUG-02",
                "finding_title": "AI Suggestion: Senior Cadre Joining / Lab License Evidence Unclear",
                "status": "Unclear evidence / human review required",
                "short_explanation": (
                    f"Page {p_page} mentions '{p_val}'. Under APH Clause 7.2, an offer letter or ongoing "
                    "procurement note requires human / EVC verification of actual joining or installation."
                ),
                "source_page": p_page,
                "source_document": "Faculty & Lab Annexure (Part III)",
                "evidence_quote": prof_field.get("source_snippet") or str(p_val),
                "handbook_citation": corpus["clause_id"],
                "retrieved_passage": corpus["passage"],
                "recommended_action": "Assign human review or verify physical joining report during EVC inspection.",
                "source_type": "AI_RAG_SUGGESTION",
                "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
                "evaluated_at": now_str,
            }
        )
    else:
        corpus = AICTE_APH_DEMO_CORPUS["CLAUSE_FACULTY_CADRE"]
        suggestions.append(
            {
                "suggestion_id": "RAG-SUG-02",
                "finding_title": "AI Suggestion: Faculty Strength & Cadre Distribution Alignment",
                "status": "Compliant / complete under configured checks",
                "short_explanation": (
                    "Extracted faculty roster and Student-Faculty Ratio align with APH Clause 7.2 reference norms."
                ),
                "source_page": 3,
                "source_document": "Faculty Roster Annexure (Part III)",
                "evidence_quote": (prof_field.get("source_snippet") if prof_field else "Student-Faculty Ratio verified on Page 3.") or "Verified on Page 3",
                "handbook_citation": corpus["clause_id"],
                "retrieved_passage": corpus["passage"],
                "recommended_action": "No mismatch suggested; routine officer verification applies.",
                "source_type": "AI_RAG_SUGGESTION",
                "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
                "evaluated_at": now_str,
            }
        )

    # 3. Built-up area & Occupancy Certificate correlation across documents
    area_field = fields_by_key.get("built_up_area")
    corpus_area = AICTE_APH_DEMO_CORPUS["CLAUSE_BUILT_UP_AREA"]
    area_val = (area_field.get("extracted_value") if area_field else "Verified built-up area") or "Verified built-up area"
    suggestions.append(
        {
            "suggestion_id": "RAG-SUG-03",
            "finding_title": "AI Suggestion: Built-Up Area & Occupancy Certificate Cross-Check",
            "status": "Compliant / complete under configured checks",
            "short_explanation": (
                f"Multi-document correlation matches declared built-up area ({area_val}) with Municipal Occupancy Certificate on Page 2."
            ),
            "source_page": (area_field.get("page_number") or 2) if area_field else 2,
            "source_document": f"{docs[0].get('title', 'Application Form') if docs else 'Application Form'}",
            "evidence_quote": (area_field.get("source_snippet") if area_field else str(area_val)) or str(area_val),
            "handbook_citation": corpus_area["clause_id"],
            "retrieved_passage": corpus_area["passage"],
            "recommended_action": "No action required on built-up area.",
            "source_type": "AI_RAG_SUGGESTION",
            "source_label": "AI-Assisted Analysis (RAG Suggestion — Not a Verified Fact)",
            "evaluated_at": now_str,
        }
    )

    return suggestions


def build_combined_findings_summary(
    rule_results: List[Dict[str, Any]], ai_suggestions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Combines Deterministic Rule Engine results and AI-Assisted Analysis (RAG) suggestions
    into a unified Findings Summary while keeping their source labels strictly distinct.
    """
    combined: List[Dict[str, Any]] = []

    for r in rule_results:
        raw_status = r.get("status", "Pass")
        if raw_status in ("Fail", "FAILED"):
            outcome = "Possible deficiency"
        elif raw_status in ("Requires Human Review", "Warning", "WARNING", "Pending Verification"):
            outcome = "Unclear evidence / human review required"
        else:
            outcome = "Compliant / complete under configured checks"

        combined.append(
            {
                "id": r.get("rule_id", "RULE"),
                "finding_title": r.get("finding_title") or r.get("rule_name", "Compliance Rule Check"),
                "status": outcome,
                "raw_status": raw_status,
                "short_explanation": r.get("explanation", ""),
                "source_page": r.get("evidence_page", 1),
                "source_evidence": r.get("evidence_quote", ""),
                "recommended_action": r.get("corrective_action", "No corrective action required."),
                "source_engine": "DETERMINISTIC_RULE",
                "source_badge": "Deterministic Rule Engine",
                "citation": r.get("rule_id", "PROTOTYPE-RULE"),
                "is_ai_suggestion": False,
            }
        )

    for s in ai_suggestions:
        combined.append(
            {
                "id": s.get("suggestion_id", "RAG"),
                "finding_title": s.get("finding_title", "AI-Assisted Analysis Suggestion"),
                "status": s.get("status", "Unclear evidence / human review required"),
                "raw_status": s.get("status", "Unclear evidence / human review required"),
                "short_explanation": s.get("short_explanation", ""),
                "source_page": s.get("source_page", 1),
                "source_evidence": f"{s.get('evidence_quote', '')} | Retrieved Reference: {s.get('handbook_citation', '')} — \"{s.get('retrieved_passage', '')}\"",
                "recommended_action": s.get("recommended_action", "Requires authorised officer verification."),
                "source_engine": "AI_RAG_SUGGESTION",
                "source_badge": "AI Suggestion (RAG — Advisory Only)",
                "citation": s.get("handbook_citation", "AICTE APH Demo Corpus"),
                "is_ai_suggestion": True,
            }
        )

    return combined
