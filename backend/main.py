"""
NIRIKSH — FastAPI Backend Application
Team CODE RED — Smart India Hackathon 2026 (Problem Statement SIH26262)
Tagline: Every case traceable. Every deadline visible. Every decision accountable.
Core Principle: AI suggests. Verified rules check. Authorised officers decide.

Two-Portal Architecture:
1. Institution / College Portal — Submit applications, upload documents, track progress, respond to clarifications.
2. AICTE / Government Portal — Review applications, run compliance checks (Deterministic Rules + AI RAG),
   manage EVC inspections, record officer decisions, monitor supervisor queues, and inspect audit logs.

Prototype Disclaimer: This backend powers a Smart India Hackathon prototype using synthetic
institutional data and deterministic prototype compliance rules. It is not connected to live
AICTE databases and does not issue official regulatory approvals.
"""

import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from database import get_db_connection, init_db_schema
from models import SAMPLE_PDF_PATH, compute_dynamic_alerts_from_cases, seed_database
from schemas import (
    ClarificationResubmitPayload,
    CreateApplicationPayload,
    DemoFieldTogglePayload,
    EvcUpdatePayload,
    OfficerDecisionPayload,
    RunChecksPayload,
    VerifyDocumentPayload,
)
from services.audit_service import list_audit_logs, record_audit_event
from services.pdf_service import extract_pdf_pages_and_fields
from services.rag_service import build_combined_findings_summary, generate_ai_rag_suggestions
from services.rules_engine import evaluate_case_compliance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "sample_data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_PDF_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://niriksh.local:3000",
    "http://niriksh.local:8000",
]
ALLOWED_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("NIRIKSH_CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if o.strip()
]

app = FastAPI(
    title="NIRIKSH Two-Portal Prototype API",
    description="Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System (SIH 2026 Prototype — Team CODE RED)",
    version="2.0.0-prototype",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def _ensure_initialized() -> None:
    init_db_schema(force_recreate=False)
    with get_db_connection() as conn:
        seed_database(conn, force_reset=False)


@app.on_event("startup")
def on_startup() -> None:
    _ensure_initialized()


def _compute_next_actions(case_dict: dict) -> tuple[str, str]:
    """Computes human-readable next actions for both Institution Portal and AICTE Officer Portal."""
    stage = case_dict.get("current_stage", "Document Scrutiny")
    comp = case_dict.get("compliance_status", "")
    evc = case_dict.get("evc_inspection") or {}
    decisions = case_dict.get("decisions") or []
    latest_dec = decisions[0].get("decision_type", "") if decisions else ""

    if stage == "Draft":
        return ("Upload PDF dossier and submit application", "Not yet submitted by institution")
    if stage == "Deficiency Query Issued" or "Clarification" in latest_dec:
        return ("Respond to officer clarification & upload rectified document", "Await institutional clarification resubmission")
    if stage == "Decision Recorded":
        if "Reject" in latest_dec:
            return ("Review rejection order & cited rule clauses", "Completed — Rejection recorded")
        return ("Download / view approval decision record", "Completed — Officer decision recorded")
    if stage == "EVC Inspection":
        v_stat = evc.get("visit_status", "Scheduled")
        if v_stat in ("Completed", "Completed - Clear"):
            return ("EVC visit completed; awaiting final officer decision", "Review EVC report & record final decision")
        return (f"Prepare campus for EVC visit ({evc.get('scheduled_date', 'TBD')})", "Record EVC inspection status & visit report")
    if stage == "Officer Decision":
        return ("Under final officer review — await decision", "Review findings & record final decision")
    if comp == "Compliance Flags Raised":
        return ("Under scrutiny — respond if clarification is requested", "Review compliance findings & request clarification")
    return ("Application under scrutiny review", "Run compliance checks & verify documents")


def _row_to_case_dict(row, for_institution: bool = False) -> dict:
    app_id = row["application_id"]
    extracted_fields = json.loads(row["extracted_fields_json"])
    documents = json.loads(row["documents_json"])
    compliance_results = json.loads(row["compliance_results_json"])
    evc_inspection = json.loads(row["evc_inspection_json"])
    decisions = json.loads(row["decisions_json"])

    if for_institution:
        sanitized_decisions = []
        for d in decisions:
            d_copy = dict(d)
            d_copy.pop("correction_note", None)
            sanitized_decisions.append(d_copy)
        decisions = sanitized_decisions

    base_dict = {
        "application_id": app_id,
        "case_id": app_id,
        "institution_name": row["institution_name"],
        "state": row["state"],
        "city": row["city"],
        "application_type": row["application_type"],
        "programme": row["programme"],
        "programme_name": row["programme"],
        "proposed_intake": row["proposed_intake"],
        "submission_date": row["submission_date"],
        "current_stage": row["current_stage"],
        "compliance_status": row["compliance_status"],
        "assigned_officer": row["assigned_officer"],
        "assigned_role": row["assigned_role"],
        "sla_deadline": row["sla_deadline"],
        "deadline_date": row["sla_deadline"],
        "evc_required": bool(row["evc_required"]),
        "evc_applicable": bool(row["evc_required"]),
        "evc_due": bool(row["evc_due"]),
        "extracted_fields": extracted_fields,
        "documents": documents,
        "compliance_results": compliance_results,
        "evc_inspection": evc_inspection,
        "decisions": decisions,
        "updated_at": row["updated_at"],
    }

    if row["current_stage"] == "Draft":
        ai_suggestions = []
        findings_summary = []
    else:
        ai_suggestions = generate_ai_rag_suggestions(base_dict)
        findings_summary = build_combined_findings_summary(compliance_results, ai_suggestions)

    next_inst, next_off = _compute_next_actions(base_dict)
    base_dict["ai_suggestions"] = ai_suggestions
    base_dict["findings_summary"] = findings_summary
    base_dict["next_action_institution"] = next_inst
    base_dict["next_action_officer"] = next_off
    return base_dict


def _sync_alerts_table(conn) -> list:
    """Recomputes alerts from current persisted cases and updates the alerts table."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases ORDER BY application_id ASC")
    all_cases = [_row_to_case_dict(r) for r in cursor.fetchall()]
    dynamic_alerts = compute_dynamic_alerts_from_cases(all_cases)
    cursor.execute("DELETE FROM alerts")
    for a in dynamic_alerts:
        a["alert_id"] = a["id"]
        a["case_id"] = a["application_id"]
        a["status"] = "OPEN"
        cursor.execute(
            """
            INSERT INTO alerts (
                id, application_id, institution_name, severity, category,
                title, message, due_date, escalation_status, recommended_action, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                a["id"],
                a["application_id"],
                a["institution_name"],
                a["severity"],
                a["category"],
                a["title"],
                a["message"],
                a["due_date"],
                a["escalation_status"],
                a["recommended_action"],
                a["created_at"],
            ),
        )
    return dynamic_alerts



FRONTEND_INDEX_CANDIDATES = [
    os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "public", "index.html")),
    os.path.abspath(os.path.join(BASE_DIR, "index.html")),
]


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def serve_frontend_portal():
    """Serves the NIRIKSH Two-Portal Web Application directly at http://127.0.0.1:8000/."""
    _ensure_initialized()
    for candidate in FRONTEND_INDEX_CANDIDATES:
        if os.path.exists(candidate):
            return FileResponse(candidate, media_type="text/html")
    return {"message": "NIRIKSH API is running. Open frontend/public/index.html or /api/health."}


@app.get("/api/health")
def health_check():
    _ensure_initialized()
    return {
        "status": "ok",
        "product": "NIRIKSH",
        "team": "CODE RED",
        "problem_statement": "SIH26262",
        "portals": ["Institution / College Portal", "AICTE / Government Portal"],
        "mode": "SIH 2026 Prototype (Synthetic Data Only)",
        "cors_origins": ALLOWED_CORS_ORIGINS,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


@app.get("/api/cases")
def get_all_cases(
    search: Optional[str] = None,
    stage: Optional[str] = None,
    compliance_status: Optional[str] = None,
    evc_due: Optional[bool] = None,
    include_drafts: bool = False,
):
    """Returns submitted cases for the AICTE / Government Portal (or all cases if include_drafts=True)."""
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY application_id ASC")
        all_rows = [_row_to_case_dict(r) for r in cursor.fetchall()]

    all_cases = all_rows if include_drafts else [c for c in all_rows if c["current_stage"] != "Draft"]

    kpis = {
        "total_applications": len(all_cases),
        "pending_scrutiny": sum(
            1
            for c in all_cases
            if c["current_stage"]
            in (
                "Submitted",
                "Document Verification",
                "Document Scrutiny",
                "Compliance Scrutiny",
                "Compliance Review",
            )
        ),
        "compliance_flags": sum(
            1 for c in all_cases if c["compliance_status"] != "All Checks Passed" and c["current_stage"] != "Draft"
        ),
        "evc_visits_due": sum(1 for c in all_cases if c["evc_due"]),
        "decisions_pending": sum(
            1 for c in all_cases if c["current_stage"] == "Officer Decision"
        ),
        "approved_or_closed": sum(
            1
            for c in all_cases
            if "Approved" in c["current_stage"] or "Decision Recorded" in c["current_stage"]
        ),
    }

    filtered = all_cases
    if search:
        q = search.strip().lower()
        filtered = [
            c
            for c in filtered
            if q in c["application_id"].lower()
            or q in c["institution_name"].lower()
            or q in c["programme"].lower()
            or q in c["state"].lower()
            or q in c["assigned_officer"].lower()
        ]
    if stage and stage != "ALL":
        if stage == "PENDING_SCRUTINY":
            filtered = [
                c
                for c in filtered
                if c["current_stage"]
                in (
                    "Submitted",
                    "Document Verification",
                    "Document Scrutiny",
                    "Compliance Scrutiny",
                    "Compliance Review",
                )
            ]
        else:
            filtered = [c for c in filtered if c["current_stage"] == stage]
    if compliance_status and compliance_status != "ALL":
        if compliance_status == "FLAGGED":
            filtered = [c for c in filtered if c["compliance_status"] != "All Checks Passed"]
        else:
            filtered = [c for c in filtered if c["compliance_status"] == compliance_status]
    if evc_due is not None:
        filtered = [c for c in filtered if c["evc_due"] == evc_due]

    return {"kpis": kpis, "cases": filtered, "total_filtered": len(filtered)}


@app.get("/api/institution/cases")
def get_institution_cases(
    institution_name: str = "Demo Technical Institute",
    search: Optional[str] = None,
):
    """
    Returns applications belonging strictly to the specified institution for the Institution / College Portal.
    Includes institutional Draft applications and strips internal officer-only notes for RBAC privacy.
    """
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY application_id ASC")
        all_rows = [_row_to_case_dict(r, for_institution=True) for r in cursor.fetchall()]

    inst_query = institution_name.strip().lower()
    if inst_query in ("all", "all demo institutions"):
        inst_cases = all_rows
    else:
        inst_cases = [c for c in all_rows if c["institution_name"].strip().lower() == inst_query]

    metrics = {
        "total_applications": len(inst_cases),
        "draft_applications": sum(1 for c in inst_cases if c["current_stage"] == "Draft"),
        "under_review": sum(
            1
            for c in inst_cases
            if c["current_stage"]
            in (
                "Submitted",
                "Document Scrutiny",
                "Document Verification",
                "Compliance Review",
                "Compliance Scrutiny",
                "EVC Inspection",
                "Officer Decision",
            )
        ),
        "action_required": sum(
            1
            for c in inst_cases
            if c["current_stage"] == "Deficiency Query Issued"
            or (
                c["current_stage"] != "Draft"
                and c["current_stage"] != "Decision Recorded"
                and c["compliance_status"] == "Compliance Flags Raised"
            )
        ),
    }

    filtered = inst_cases
    if search:
        q = search.strip().lower()
        filtered = [
            c
            for c in filtered
            if q in c["application_id"].lower()
            or q in c["programme"].lower()
            or q in c["application_type"].lower()
            or q in c["current_stage"].lower()
        ]

    return {
        "institution_name": institution_name,
        "metrics": metrics,
        "cases": filtered,
        "total": len(filtered),
    }


@app.post("/api/institution/applications")
def create_institution_application(payload: CreateApplicationPayload):
    """
    Creates a new institutional application (either as Draft or formally Submitted to AICTE)
    from the Institution / College Portal.
    """
    _ensure_initialized()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    today_date = datetime.utcnow().strftime("%Y-%m-%d")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT application_id FROM cases ORDER BY application_id DESC")
        existing_ids = [r["application_id"] for r in cursor.fetchall()]
        max_num = 6
        for eid in existing_ids:
            parts = eid.split("-")
            if len(parts) == 3 and parts[2].isdigit():
                max_num = max(max_num, int(parts[2]))
        new_app_id = f"NIR-2026-{max_num + 1:03d}"

        stage = "Draft" if payload.save_as_draft else "Document Scrutiny"
        extracted_fields = [
            {
                "field_key": "institution_name",
                "field_label": "Institution Name",
                "label": "Institution Name",
                "extracted_value": payload.institution_name.strip(),
                "value": payload.institution_name.strip(),
                "expected_norm": "Registered Technical Institution",
                "page_number": 1,
                "source_page": 1,
                "source_snippet": f"Institution Name: {payload.institution_name.strip()}",
                "confidence_note": "Submitted via Institution Portal Form (Page 1).",
                "notes": "Submitted via Institution Portal Form (Page 1).",
                "status": "VERIFIED",
                "source_type": "PDF_EXTRACTED",
            },
            {
                "field_key": "pid",
                "field_label": "Permanent Institute ID (PID)",
                "label": "Permanent Institute ID (PID)",
                "extracted_value": payload.aishe_id.strip(),
                "value": payload.aishe_id.strip(),
                "expected_norm": "Valid PID / AISHE Identifier",
                "page_number": 1,
                "source_page": 1,
                "source_snippet": f"Permanent ID: {payload.aishe_id.strip()}",
                "confidence_note": "Submitted via Institution Portal Form (Page 1).",
                "notes": "Submitted via Institution Portal Form (Page 1).",
                "status": "VERIFIED",
                "source_type": "PDF_EXTRACTED",
            },
            {
                "field_key": "proposed_programme",
                "field_label": "Primary Proposed Programme",
                "label": "Primary Proposed Programme",
                "extracted_value": f"{payload.programme.strip()} ({payload.proposed_intake} Seats)",
                "value": f"{payload.programme.strip()} ({payload.proposed_intake} Seats)",
                "expected_norm": "AICTE Approved Nomenclature",
                "page_number": 1,
                "source_page": 1,
                "source_snippet": f"Proposed Programme: {payload.programme.strip()}",
                "confidence_note": "Submitted via Institution Portal Form (Page 1).",
                "notes": "Submitted via Institution Portal Form (Page 1).",
                "status": "VERIFIED",
                "source_type": "PDF_EXTRACTED",
            },
            {
                "field_key": "built_up_area",
                "field_label": "Total Built-up Area Available",
                "label": "Total Built-up Area Available",
                "extracted_value": "5,400 Sq. Meters (Declared in Part II)",
                "value": "5,400 Sq. Meters (Declared in Part II)",
                "expected_norm": "Minimum 4,200 Sq.m",
                "page_number": 2,
                "source_page": 2,
                "source_snippet": "Total Built-up Area Available: 5,400 Sq. Meters",
                "confidence_note": "Declared in Institution Portal Form (Page 2).",
                "notes": "Declared in Institution Portal Form (Page 2).",
                "status": "VERIFIED",
                "source_type": "PDF_EXTRACTED",
            },
            {
                "field_key": "fire_safety_noc_validity",
                "field_label": "Fire Safety NOC Validity Date",
                "label": "Fire Safety NOC Validity Date",
                "extracted_value": "Valid till 2028-03-31",
                "value": "Valid till 2028-03-31",
                "expected_norm": "Valid date covering AY 2026-27",
                "page_number": 2,
                "source_page": 2,
                "source_snippet": "Fire Safety NOC Validity Date: 2028-03-31",
                "confidence_note": "Declared in Institution Portal Form (Page 2).",
                "notes": "Declared in Institution Portal Form (Page 2).",
                "status": "VERIFIED",
                "source_type": "PDF_EXTRACTED",
            },
        ]

        docs = []
        if not payload.save_as_draft:
            docs.append(
                {
                    "doc_id": f"DOC-{max_num + 1:03d}-A",
                    "title": f"Institutional Application Form ({payload.programme.strip()})",
                    "category": "Application Form",
                    "filename": f"{new_app_id}_Application_Form.pdf",
                    "file_size_kb": 195,
                    "pages": 3,
                    "page_count": 3,
                    "uploaded_at": now_str,
                    "status": "Verified",
                    "source_page_ref": "Pages 1–3",
                    "notes": "Submitted via Institution Portal.",
                    "extracted_pages_text": [],
                }
            )

        evc_obj = {
            "required": payload.evc_required,
            "applicable": payload.evc_required,
            "applicability_reason": (
                "New programme / intake scrutiny requires EVC verification."
                if payload.evc_required
                else "Standard renewal — EVC not required."
            ),
            "inspection_mode": "Physical EVC" if payload.evc_required else "Not Applicable",
            "committee_chair": "EVC Panel Assignment Pending" if payload.evc_required else None,
            "assigned_committee": "EVC Panel Assignment Pending" if payload.evc_required else None,
            "scheduled_date": "2026-11-12" if payload.evc_required else None,
            "proposed_date": "2026-11-12" if payload.evc_required else None,
            "visit_status": "Not Scheduled" if payload.evc_required else "Not Applicable",
            "report_uploaded": "Pending Visit" if payload.evc_required else "Not Applicable",
            "report_status": "Pending Visit" if payload.evc_required else "Not Applicable",
            "observations": "Initial application record created via Institution Portal.",
            "notes": "Initial application record created via Institution Portal.",
            "recommendation": "Complete document scrutiny",
            "next_action": "Complete document scrutiny",
            "checklist": [],
            "updated_by": payload.actor_name,
            "updated_at": now_str,
        }

        temp_case = {
            "application_id": new_app_id,
            "extracted_fields": extracted_fields,
            "documents": docs,
            "evc_inspection": evc_obj,
            "evc_required": payload.evc_required,
        }
        if payload.save_as_draft:
            rule_results = []
            overall_status = "Draft — Not Yet Submitted"
        else:
            rule_results, overall_status = evaluate_case_compliance(temp_case)

        cursor.execute(
            """
            INSERT INTO cases (
                application_id, institution_name, state, city, application_type,
                programme, proposed_intake, submission_date, current_stage,
                compliance_status, assigned_officer, assigned_role, sla_deadline,
                evc_required, evc_due, extracted_fields_json, documents_json,
                compliance_results_json, evc_inspection_json, decisions_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_app_id,
                payload.institution_name.strip(),
                payload.state.strip(),
                payload.city.strip(),
                payload.application_type.strip(),
                payload.programme.strip(),
                payload.proposed_intake,
                today_date,
                stage,
                overall_status,
                "Sh. Vikramaditya Sen" if not payload.save_as_draft else "Unassigned (Draft)",
                "Reviewing Officer (Scrutiny Wing)",
                "2026-11-15",
                1 if payload.evc_required else 0,
                1 if (payload.evc_required and not payload.save_as_draft) else 0,
                json.dumps(extracted_fields),
                json.dumps(docs),
                json.dumps(rule_results),
                json.dumps(evc_obj),
                json.dumps([]),
                now_str,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=new_app_id,
            actor_name=payload.actor_name,
            actor_role="Applicant Institution",
            action_type="APPLICATION_DRAFT_SAVED" if payload.save_as_draft else "APPLICATION_SUBMITTED",
            previous_value="New Form",
            new_value=f"{stage} ({payload.programme.strip()}, {payload.proposed_intake} Seats)",
            remarks=f"{payload.institution_name.strip()} {'saved draft' if payload.save_as_draft else 'submitted application'} {new_app_id} for {payload.application_type.strip()}.",
        )
        _sync_alerts_table(conn)

        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (new_app_id,))
        created_case = _row_to_case_dict(cursor.fetchone())
        created_case["audit_trail"] = list_audit_logs(conn, application_id=new_app_id)

    return {
        "message": f"Application {new_app_id} {'saved as draft' if payload.save_as_draft else 'submitted to AICTE scrutiny'}.",
        "case": created_case,
    }


@app.post("/api/cases/{case_id}/resubmit")
def resubmit_clarification(case_id: str, payload: ClarificationResubmitPayload):
    """
    Allows an institution in the Institution / College Portal to respond to an officer's
    Clarification Request, upload/attach rectified document evidence, and return the case
    to Document Processing & Compliance Review.
    """
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        prev_stage = case_dict["current_stage"]
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        fields = case_dict.get("extracted_fields", [])
        docs = case_dict.get("documents", [])

        # Update missing/deficient fields (Fire Safety NOC or Land CLU)
        target_key = payload.rectified_field_key or "fire_safety_noc_validity"
        target_val = payload.rectified_field_value or "Valid till 2028-06-30 (Rectified Cert #FS-UP-2026-9921)"

        updated_field = False
        for f in fields:
            if f.get("field_key") in (target_key, "fire_safety_noc_validity", "land_clu_cert") and f.get("status") == "MISSING":
                f["extracted_value"] = target_val
                f["value"] = target_val
                f["status"] = "VERIFIED"
                f["confidence_note"] = f"Verified via Institutional Clarification Resubmission ({now_str})"
                f["notes"] = f"Verified via Institutional Clarification Resubmission ({now_str})"
                f["source_snippet"] = f"{f.get('field_label', 'Statutory Field')}: {target_val}"
                updated_field = True

        if not updated_field:
            f_noc = next((f for f in fields if f.get("field_key") == "fire_safety_noc_validity"), None)
            if f_noc:
                f_noc["extracted_value"] = target_val
                f_noc["value"] = target_val
                f_noc["status"] = "VERIFIED"
                f_noc["confidence_note"] = f"Verified via Institutional Clarification Resubmission ({now_str})"
                f_noc["source_snippet"] = f"Fire Safety NOC Validity Date: {target_val}"

        # Mark previously deficient documents as Verified and prepend the supplementary clarification annexure
        for d in docs:
            if d.get("status") in ("Missing Field", "Pending Scrutiny", "MISSING", "PENDING_VERIFICATION"):
                d["status"] = "Verified"
                d["notes"] = f"Rectified via institutional clarification resubmission: {payload.response_remarks.strip()}"

        clarification_doc = {
            "doc_id": f"DOC-CLR-{int(datetime.utcnow().timestamp()) % 100000}",
            "title": payload.document_title or "Supplementary Clarification Annexure (Certified)",
            "category": "Clarification Resubmission",
            "filename": payload.document_filename or f"{case_id}_Clarification_Rectified.pdf",
            "file_size_kb": 240,
            "pages": 2,
            "page_count": 2,
            "uploaded_at": now_str,
            "status": "Verified",
            "source_page_ref": "Page 2, Section 2.2 (Rectified)",
            "notes": f"Submitted by institution in response to clarification query: {payload.response_remarks.strip()}",
            "extracted_pages_text": [],
        }
        docs.insert(0, clarification_doc)

        case_dict["extracted_fields"] = fields
        case_dict["documents"] = docs
        # Return application to Compliance Review after re-running Document Processing & Compliance Rules
        new_stage = "Compliance Review"
        case_dict["current_stage"] = new_stage

        rule_results, overall_status = evaluate_case_compliance(case_dict)
        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET current_stage = ?, extracted_fields_json = ?, documents_json = ?,
                compliance_results_json = ?, compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                new_stage,
                json.dumps(fields),
                json.dumps(docs),
                json.dumps(rule_results),
                overall_status,
                now_str,
                case_id,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=payload.actor_name.strip(),
            actor_role=payload.actor_role.strip(),
            action_type="CLARIFICATION_RESUBMITTED",
            previous_value=prev_stage,
            new_value=f"{new_stage} ({overall_status})",
            remarks=f"Institution submitted clarification response & supplementary document '{clarification_doc['filename']}': {payload.response_remarks.strip()}",
        )
        _sync_alerts_table(conn)

        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        updated_case = _row_to_case_dict(cursor.fetchone())
        updated_case["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": f"Clarification response submitted for {case_id}. Application returned to Document Processing & Compliance Review.",
        "case": updated_case,
    }


@app.get("/api/supervisor/overview")
def get_supervisor_overview():
    """
    Provides the Supervisor View in the AICTE / Government Portal using the same underlying case records.
    Summarizes application status, pending cases, overdue / SLA-at-risk actions, and inspection delays.
    """
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY application_id ASC")
        all_cases = [_row_to_case_dict(r) for r in cursor.fetchall() if r["current_stage"] != "Draft"]
        alerts = _sync_alerts_table(conn)

    pending_cases = [c for c in all_cases if c["current_stage"] != "Decision Recorded"]
    overdue_or_at_risk = [
        c
        for c in all_cases
        if c["current_stage"] != "Decision Recorded"
        and (c["sla_deadline"] <= "2026-10-30" or c["compliance_status"] == "Compliance Flags Raised")
    ]
    inspection_delays = [
        c
        for c in all_cases
        if c["evc_required"]
        and c["evc_inspection"].get("visit_status") in ("Not Scheduled", "Scheduled", "Pending Schedule")
    ]

    return {
        "summary": {
            "total_submitted_cases": len(all_cases),
            "pending_cases_count": len(pending_cases),
            "overdue_or_sla_risk_count": len(overdue_or_at_risk),
            "inspection_delays_count": len(inspection_delays),
            "completed_decisions_count": sum(1 for c in all_cases if c["current_stage"] == "Decision Recorded"),
        },
        "pending_cases": pending_cases,
        "overdue_or_at_risk": overdue_or_at_risk,
        "inspection_delays": inspection_delays,
        "active_alerts": alerts,
    }


@app.get("/api/cases/{case_id}")
def get_case_detail(case_id: str, for_institution: bool = False):
    """Returns full case dossier including extracted fields, documents, compliance rules, RAG suggestions, EVC, and audit logs."""
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Application case '{case_id}' not found.")
        case_dict = _row_to_case_dict(row, for_institution=for_institution)
        logs = list_audit_logs(conn, application_id=case_id)
        if for_institution:
            # Strip internal officer correction notes from audit remarks if present
            sanitized_logs = []
            for lg in logs:
                lg_copy = dict(lg)
                if " | [Officer Correction Logged" in lg_copy.get("remarks", ""):
                    lg_copy["remarks"] = lg_copy["remarks"].split(" | [Officer Correction Logged")[0]
                sanitized_logs.append(lg_copy)
            logs = sanitized_logs
        case_dict["audit_trail"] = logs
        return case_dict


@app.get("/api/cases/{case_id}/sample-pdf")
def download_sample_pdf(case_id: str):
    """Serves the local synthetic sample PDF dossier for preview or download."""
    if not os.path.exists(SAMPLE_PDF_PATH):
        raise HTTPException(status_code=404, detail="Synthetic sample PDF file not found on server.")
    return FileResponse(
        SAMPLE_PDF_PATH,
        media_type="application/pdf",
        filename=f"{case_id}_Demo_Technical_Institute.pdf",
    )


@app.post("/api/documents/upload")
async def upload_and_parse_pdf(
    application_id: str = Form("NIR-2026-001"),
    actor_name: str = Form("Sh. Vikramaditya Sen"),
    actor_role: str = Form("Reviewing Officer (Scrutiny Wing)"),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form("Uploaded PDF Dossier"),
    file: UploadFile = File(...),
):
    """
    Validates, saves, and parses an uploaded PDF document using PyMuPDF / pdfplumber / pypdf.
    Updates the target case's extracted fields and document list, and writes an audit trail entry.
    """
    _ensure_initialized()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .pdf documents are accepted for AICTE scrutiny.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty (0 bytes).")
    if len(content) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded PDF exceeds the 10 MB prototype file size limit.")

    safe_name = os.path.basename(file.filename)
    saved_path = os.path.join(UPLOAD_DIR, f"{application_id}_{safe_name}")
    with open(saved_path, "wb") as f:
        f.write(content)

    try:
        extraction_result = extract_pdf_pages_and_fields(saved_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF file: {exc}") from exc

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{application_id}' not found.")

        case_dict = _row_to_case_dict(row)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        new_doc = {
            "doc_id": f"DOC-UPL-{int(datetime.utcnow().timestamp()) % 100000}",
            "title": title or f"Uploaded Dossier ({safe_name})",
            "category": category or "Uploaded PDF Dossier",
            "filename": safe_name,
            "pages": extraction_result["page_count"],
            "page_count": extraction_result["page_count"],
            "file_size_kb": max(1, round(len(content) / 1024)),
            "uploaded_at": now_str,
            "status": "Verified",
            "notes": f"Parsed via {extraction_result['engine_used']} ({extraction_result['page_count']} pages).",
            "source_page_ref": f"Pages 1–{extraction_result['page_count']}",
            "extracted_pages_text": extraction_result["pages"],
        }

        docs = case_dict["documents"]
        docs.insert(0, new_doc)

        extracted_fields = extraction_result["extracted_fields"]
        case_dict["extracted_fields"] = extracted_fields
        case_dict["documents"] = docs
        if case_dict["current_stage"] == "Draft":
            case_dict["current_stage"] = "Document Scrutiny"

        rule_results, overall_status = evaluate_case_compliance(case_dict)
        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET current_stage = ?, extracted_fields_json = ?, documents_json = ?, compliance_results_json = ?,
                compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                case_dict["current_stage"],
                json.dumps(case_dict["extracted_fields"]),
                json.dumps(case_dict["documents"]),
                json.dumps(case_dict["compliance_results"]),
                case_dict["compliance_status"],
                case_dict["updated_at"],
                application_id,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=application_id,
            actor_name=actor_name,
            actor_role=actor_role,
            action_type="PDF_DOCUMENT_UPLOADED_AND_PARSED",
            previous_value="Prior Dossier",
            new_value=f"{safe_name} ({extraction_result['page_count']} pages via {extraction_result['engine_used']})",
            remarks=f"Uploaded and parsed '{safe_name}'. Re-evaluated compliance rules -> {overall_status}.",
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (application_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=application_id)

    return {
        "message": f"Successfully parsed '{safe_name}' using {extraction_result['engine_used']}.",
        "extraction": extraction_result,
        "case": case_dict,
    }


@app.post("/api/cases/{case_id}/verify-document/{doc_id}")
def verify_case_document(case_id: str, doc_id: str, payload: VerifyDocumentPayload):
    """Updates verification status of a specific document annexure, re-evaluates rules, and logs an audit event."""
    _ensure_initialized()
    status_map = {
        "Verified": "Verified",
        "VERIFIED": "Verified",
        "Pending Scrutiny": "Pending Scrutiny",
        "PENDING_VERIFICATION": "Pending Scrutiny",
        "Missing Field": "Missing Field",
        "MISSING": "Missing Field",
    }
    if payload.status not in status_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document status '{payload.status}'.",
        )
    normalized_status = status_map[payload.status]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        docs = case_dict.get("documents", [])
        target_doc = next((d for d in docs if d.get("doc_id") == doc_id), None)
        if not target_doc:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in case '{case_id}'.")

        prev_status = target_doc.get("status", "Pending Scrutiny")
        target_doc["status"] = normalized_status
        if payload.remarks:
            target_doc["notes"] = payload.remarks

        rule_results, overall_status = evaluate_case_compliance(case_dict)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET documents_json = ?, compliance_results_json = ?, compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                json.dumps(docs),
                json.dumps(rule_results),
                overall_status,
                now_str,
                case_id,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=payload.actor_name,
            actor_role=payload.actor_role,
            action_type="DOCUMENT_VERIFICATION_UPDATED",
            previous_value=f"{doc_id}: {prev_status}",
            new_value=f"{doc_id}: {normalized_status}",
            remarks=payload.remarks or f"Document '{target_doc.get('title')}' marked as {normalized_status}.",
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": f"Document '{target_doc.get('title')}' updated to '{normalized_status}'.",
        "case": case_dict,
    }


@app.post("/api/cases/{case_id}/toggle-demo-field")
def toggle_demo_field_deficiency(case_id: str, payload: DemoFieldTogglePayload):
    """
    Allows the officer in the live demo to simulate receiving or reverting the renewed Fire Safety NOC
    clarification on Page 2, persisting the change to SQLite and logging an audit event.
    """
    _ensure_initialized()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        fields = case_dict.get("extracted_fields", [])
        docs = case_dict.get("documents", [])
        f_noc = next((f for f in fields if f.get("field_key") == "fire_safety_noc_validity"), None)
        d_noc = next((d for d in docs if "Fire Safety" in d.get("title", "")), None)

        prev_val = (f_noc.get("extracted_value") or f_noc.get("value") or "MISSING") if f_noc else "MISSING"
        if payload.resolve_deficiency:
            if f_noc:
                f_noc["extracted_value"] = "Valid till 2028-06-30 (Rectified Cert #FS-UP-2026-9921)"
                f_noc["value"] = "Valid till 2028-06-30 (Rectified Cert #FS-UP-2026-9921)"
                f_noc["status"] = "VERIFIED"
                f_noc["confidence_note"] = "Verified via Clarification Upload (Page 2)"
                f_noc["notes"] = "Verified via Clarification Upload (Page 2)"
                f_noc["source_snippet"] = "Fire Safety NOC Validity Date: 2028-06-30 (Endorsement FS-UP-2026-9921)"
            if d_noc:
                d_noc["status"] = "Verified"
                d_noc["notes"] = "Renewal endorsement FS-UP-2026-9921 verified through 2028-06-30."
            new_val = "2028-06-30 (Verified)"
            remark_msg = "Simulated institutional clarification upload providing Fire Safety NOC Validity Date (2028-06-30)."
        else:
            if f_noc:
                f_noc["extracted_value"] = "[MISSING IN SUBMISSION — BLANK FIELD ON FORM]"
                f_noc["value"] = None
                f_noc["status"] = "MISSING"
                f_noc["confidence_note"] = "Blank / missing field detected on submitted PDF form (Page 2 Section 2.2)."
                f_noc["notes"] = "Blank / missing field detected on submitted PDF form (Page 2 Section 2.2)."
                f_noc["source_snippet"] = "Fire Safety NOC Validity Date [MISSING IN SUBMISSION — BLANK FIELD ON FORM]"
            if d_noc:
                d_noc["status"] = "Pending Scrutiny"
                d_noc["notes"] = "Certificate number present on Page 2, but validity expiration date is omitted in Section 2.2."
            new_val = "[MISSING IN SUBMISSION — BLANK FIELD ON FORM]"
            remark_msg = "Reverted Fire Safety NOC Validity Date to missing state for demonstration."

        rule_results, overall_status = evaluate_case_compliance(case_dict)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET extracted_fields_json = ?, documents_json = ?, compliance_results_json = ?,
                compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                json.dumps(fields),
                json.dumps(docs),
                json.dumps(rule_results),
                overall_status,
                now_str,
                case_id,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=payload.actor_name,
            actor_role=payload.actor_role,
            action_type="CLARIFICATION_FIELD_UPDATED",
            previous_value=str(prev_val),
            new_value=new_val,
            remarks=remark_msg,
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": remark_msg,
        "case": case_dict,
    }


@app.post("/api/cases/{case_id}/run-checks")
def run_compliance_checks(case_id: str, payload: Optional[RunChecksPayload] = None):
    """Executes deterministic compliance rules and AI RAG suggestions on the specified case, persists results, and writes an audit entry."""
    _ensure_initialized()
    actor_name = payload.actor_name if payload else "Sh. Vikramaditya Sen"
    actor_role = payload.actor_role if payload else "Reviewing Officer (Scrutiny Wing)"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        previous_status = case_dict["compliance_status"]

        rule_results, overall_status = evaluate_case_compliance(case_dict)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET compliance_results_json = ?, compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (json.dumps(rule_results), overall_status, now_str, case_id),
        )

        pass_cnt = sum(1 for r in rule_results if r["status"] in ("Pass", "PASSED"))
        fail_cnt = sum(1 for r in rule_results if r["status"] in ("Fail", "FAILED"))
        rev_cnt = sum(
            1
            for r in rule_results
            if r["status"] in ("Requires Human Review", "Warning", "Pending Verification", "WARNING")
        )

        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=actor_name,
            actor_role=actor_role,
            action_type="COMPLIANCE_CHECK",
            previous_value=previous_status,
            new_value=f"{overall_status} ({pass_cnt} Pass, {fail_cnt} Fail, {rev_cnt} Review)",
            remarks=f"Executed 5 deterministic prototype compliance checks (Checks A-E) + AI RAG retrieval. Overall status: {overall_status}.",
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": f"Compliance rules executed for {case_id}. Result: {overall_status}",
        "compliance_status": overall_status,
        "compliance_results": rule_results,
        "ai_suggestions": case_dict["ai_suggestions"],
        "findings_summary": case_dict["findings_summary"],
        "case": case_dict,
    }


@app.post("/api/cases/{case_id}/evc")
def update_evc_inspection(case_id: str, payload: EvcUpdatePayload):
    """Updates EVC inspection status, observations, and recommendation for a case and logs an audit entry."""
    _ensure_initialized()
    sched_date = payload.scheduled_date or payload.proposed_date or "2026-11-04"
    rep_status = payload.report_uploaded or payload.report_status or "Pending Visit"
    obs_text = (payload.observations or payload.notes or "").strip()
    rec_text = payload.recommendation or payload.next_action or "Proceed to Officer Decision"

    if len(obs_text) < 5:
        raise HTTPException(status_code=400, detail="EVC observations/notes must be at least 5 characters.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        evc = case_dict["evc_inspection"]
        prev_status = evc.get("visit_status", "Not Scheduled")

        has_evc_doc = any(
            "EVC" in d.get("title", "").upper() or "INSPECTION" in d.get("title", "").upper()
            for d in case_dict.get("documents", [])
        )
        if rep_status == "Uploaded & Verified" and not has_evc_doc:
            rep_status = "Uploaded & Verified (Demo Status)"

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        evc["visit_status"] = payload.visit_status
        evc["scheduled_date"] = sched_date
        evc["proposed_date"] = sched_date
        if payload.assigned_committee:
            evc["committee_chair"] = payload.assigned_committee
            evc["assigned_committee"] = payload.assigned_committee
        evc["report_uploaded"] = rep_status
        evc["report_status"] = rep_status
        evc["observations"] = obs_text
        evc["notes"] = obs_text
        evc["recommendation"] = rec_text
        evc["next_action"] = rec_text
        if payload.checklist is not None:
            evc["checklist"] = [item.dict() for item in payload.checklist]
        evc["updated_by"] = f"{payload.actor_name} ({payload.actor_role})"
        evc["updated_at"] = now_str

        evc_due = payload.visit_status in ("Scheduled", "Pending Schedule", "Not Scheduled", "In Progress")
        new_stage = case_dict["current_stage"]
        if payload.visit_status in ("Scheduled", "In Progress") and new_stage in (
            "Submitted",
            "Document Scrutiny",
            "Document Verification",
            "Compliance Review",
            "Compliance Scrutiny",
        ):
            new_stage = "EVC Inspection"
        elif payload.visit_status.startswith("Completed") and new_stage in (
            "Submitted",
            "Document Scrutiny",
            "EVC Inspection",
            "Compliance Scrutiny",
            "Compliance Review",
        ):
            new_stage = "Officer Decision"

        case_dict["evc_inspection"] = evc
        case_dict["evc_due"] = evc_due
        case_dict["current_stage"] = new_stage
        rule_results, overall_status = evaluate_case_compliance(case_dict)
        case_dict["compliance_results"] = rule_results
        case_dict["compliance_status"] = overall_status
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET evc_inspection_json = ?, evc_due = ?, current_stage = ?,
                compliance_results_json = ?, compliance_status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                json.dumps(evc),
                1 if evc_due else 0,
                new_stage,
                json.dumps(rule_results),
                overall_status,
                now_str,
                case_id,
            ),
        )

        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=payload.actor_name,
            actor_role=payload.actor_role,
            action_type="EVC_UPDATED",
            previous_value=prev_status,
            new_value=f"{payload.visit_status} | Report: {rep_status} ({rec_text})",
            remarks=f"EVC Observation: {obs_text}",
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": f"EVC inspection record updated for {case_id}.",
        "case": case_dict,
    }


@app.post("/api/cases/{case_id}/decision")
def record_officer_decision(case_id: str, payload: OfficerDecisionPayload):
    """
    Records an authorised officer's formal workflow decision with mandatory remarks.
    Core Principle: AI suggests. Verified rules check. Authorised officers decide.
    """
    _ensure_initialized()
    decision_str = (payload.decision or payload.decision_type or "").strip()
    valid_decisions = {
        "Approve": ("Approved (Officer Decision Recorded)", "Decision Recorded"),
        "Reject": ("Rejected (Deficiency Refusal Recorded)", "Decision Recorded"),
        "Request Clarification": ("Clarification Requested from Institution", "Deficiency Query Issued"),
        "Request Additional Information": ("Additional Information Requested", "Deficiency Query Issued"),
        "Mark Scrutiny Complete": ("Scrutiny Marked Complete", "EVC Inspection"),
        "Record Recommendation": ("Recommendation Recorded (Prototype)", "Decision Recorded"),
        "Approve for Next Stage": ("Approved for Next Stage", "Officer Decision"),
        "Recommend EVC Inspection": ("Recommended EVC Inspection", "EVC Inspection"),
        "Escalate to Senior Committee": ("Escalated to Senior Committee", "Officer Decision"),
        "Reject / Hold": ("Held / Deficient (Officer Decision)", "Deficiency Query Issued"),
    }

    if decision_str not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision action '{decision_str}'.",
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

        case_dict = _row_to_case_dict(row)
        prev_stage = case_dict["current_stage"]
        decision_status_label, new_stage = valid_decisions[decision_str]

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        corr_note = (payload.correction_note or "").strip()
        decision_record = {
            "decision_id": f"DEC-{int(datetime.utcnow().timestamp()) % 100000}",
            "application_id": case_id,
            "officer_name": payload.officer_name.strip(),
            "officer_role": payload.officer_role.strip(),
            "decision": decision_str,
            "decision_type": decision_str,
            "decision_status": decision_status_label,
            "remarks": payload.remarks.strip(),
            "correction_note": corr_note,
            "previous_stage": prev_stage,
            "new_stage": new_stage,
            "timestamp": now_str,
        }

        decisions = case_dict["decisions"]
        decisions.insert(0, decision_record)

        evc_due = case_dict["evc_due"]
        evc_req = case_dict["evc_required"]
        if decision_str in ("Recommend EVC Inspection", "Mark Scrutiny Complete") and evc_req:
            evc_due = case_dict["evc_inspection"].get("visit_status") not in ("Completed", "Completed - Clear")
        elif new_stage == "Decision Recorded":
            evc_due = False

        case_dict["decisions"] = decisions
        case_dict["current_stage"] = new_stage
        case_dict["evc_due"] = evc_due
        case_dict["evc_required"] = evc_req
        case_dict["updated_at"] = now_str

        cursor.execute(
            """
            UPDATE cases
            SET decisions_json = ?, current_stage = ?, evc_due = ?, evc_required = ?,
                evc_inspection_json = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (
                json.dumps(decisions),
                new_stage,
                1 if evc_due else 0,
                1 if evc_req else 0,
                json.dumps(case_dict["evc_inspection"]),
                now_str,
                case_id,
            ),
        )

        audit_remarks = payload.remarks.strip()
        if corr_note:
            audit_remarks = f"{audit_remarks} | [Officer Correction Logged for Rule/Prompt Refinement: {corr_note}]"
        record_audit_event(
            conn=conn,
            application_id=case_id,
            actor_name=payload.officer_name.strip(),
            actor_role=payload.officer_role.strip(),
            action_type="DECISION_RECORDED",
            previous_value=prev_stage,
            new_value=f"{new_stage} ({decision_str})",
            remarks=audit_remarks,
        )
        _sync_alerts_table(conn)
        cursor.execute("SELECT * FROM cases WHERE application_id = ?", (case_id,))
        case_dict = _row_to_case_dict(cursor.fetchone())
        case_dict["audit_trail"] = list_audit_logs(conn, application_id=case_id)

    return {
        "message": f"Decision '{decision_str}' recorded by {payload.officer_name}.",
        "decision": decision_record,
        "case": case_dict,
    }


@app.get("/api/cases/{case_id}/audit")
def get_case_audit_trail(case_id: str):
    _ensure_initialized()
    with get_db_connection() as conn:
        logs = list_audit_logs(conn, application_id=case_id)
    return {"application_id": case_id, "audit_logs": logs}


@app.get("/api/audit")
def get_global_audit_trail(application_id: Optional[str] = None):
    _ensure_initialized()
    with get_db_connection() as conn:
        logs = list_audit_logs(conn, application_id=application_id)
    return {"audit_logs": logs, "total": len(logs)}


@app.get("/api/alerts")
def get_alerts(severity: Optional[str] = None):
    """Returns dynamically computed in-app alerts derived from persisted case states, compliance flags, and EVC status."""
    _ensure_initialized()
    with get_db_connection() as conn:
        alerts = _sync_alerts_table(conn)
    if severity and severity != "ALL":
        alerts = [a for a in alerts if a["severity"] == severity]
    return {
        "alerts": alerts,
        "total": len(alerts),
        "delivery_mode": "IN_APP_NOTIFICATION (Prototype — No External Email/SMS Dispatched)",
    }


@app.post("/api/demo/reset")
def reset_demo_state():
    """Resets the SQLite database back to the clean initial SIH 2026 demonstration state."""
    init_db_schema(force_recreate=False)
    with get_db_connection() as conn:
        seed_database(conn, force_reset=True)
    return {"status": "reset_complete", "message": "NIRIKSH prototype database restored to initial demo state."}
