"""
Automated Backend & Integration Test Suite for NIRIKSH Two-Portal Prototype
Team CODE RED — Smart India Hackathon 2026 (Problem Statement SIH26262)
Tagline: Every case traceable. Every deadline visible. Every decision accountable.
Core Principle: AI suggests. Verified rules check. Authorised officers decide.

Executes 15 automated tests covering:
1. Health endpoint (`GET /api/health`) and CORS configuration.
2. Case listing (`GET /api/cases`) and case detail (`GET /api/cases/NIR-2026-001`).
3. Unknown case ID (`GET /api/cases/NIR-2026-999` -> 404).
4. PDF extraction and correct page numbering (`NIR-2026-001_Demo_Technical_Institute.pdf`, Pages 1, 2, 3).
5. Invalid, empty, or corrupt PDF upload (`POST /api/documents/upload` -> 400).
6. Missing Fire Safety NOC validity date flagged with Page 2 evidence.
7. Faculty cadre warning / human review required with Page 3 evidence.
8. EVC update validation and SQLite persistence (`POST /api/cases/NIR-2026-001/evc`).
9. Officer decision validation and SQLite persistence (`POST /api/cases/NIR-2026-001/decision`).
10. Audit event creation and chronological retrieval (`GET /api/cases/NIR-2026-001/audit` & `GET /api/audit`).
11. Database isolation using a temporary test database (`NIRIKSH_DB_PATH`).
12. Repeated startup without duplicate seeding or loss of existing user changes.
13. Institution Portal isolation (`GET /api/institution/cases`, `POST /api/institution/applications`) and hiding internal officer notes.
14. Separate Deterministic Rule Engine & AI-Assisted Analysis (RAG) outputs + Supervisor View (`GET /api/supervisor/overview`).
15. End-to-End 10-Step Acceptance Test Journey across Institution Portal and AICTE / Government Portal.
"""

import io
import os
import sys
import tempfile
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

_TEMP_DB_DIR = tempfile.mkdtemp(prefix="niriksh_test_")
TEST_DB_PATH = os.path.join(_TEMP_DB_DIR, "niriksh_isolated_test.db")
os.environ["NIRIKSH_DB_PATH"] = TEST_DB_PATH

from fastapi.testclient import TestClient  # noqa: E402
from database import get_db_connection, init_db_schema  # noqa: E402
from main import app, on_startup  # noqa: E402
from models import SAMPLE_PDF_PATH, seed_database  # noqa: E402
from services.pdf_service import extract_pdf_pages_and_fields  # noqa: E402


class TestNirikshPrototype(unittest.TestCase):
    """15-test automated verification suite for NIRIKSH FastAPI backend and Two-Portal workflow."""

    @classmethod
    def setUpClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        init_db_schema(force_recreate=True)
        with get_db_connection() as conn:
            seed_database(conn, force_reset=True)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass

    def setUp(self) -> None:
        init_db_schema(force_recreate=False)
        with get_db_connection() as conn:
            seed_database(conn, force_reset=True)

    # -------------------------------------------------------------------------
    # Test 1: Health endpoint
    # -------------------------------------------------------------------------
    def test_01_health_endpoint(self) -> None:
        resp_root = self.client.get("/")
        self.assertEqual(resp_root.status_code, 200)
        self.assertIn("NIRIKSH", resp_root.text)
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["product"], "NIRIKSH")
        self.assertEqual(data["team"], "CODE RED")
        self.assertIn("http://localhost:3000", data.get("cors_origins", []))

    # -------------------------------------------------------------------------
    # Test 2: Case listing and case detail
    # -------------------------------------------------------------------------
    def test_02_case_listing_and_detail(self) -> None:
        list_resp = self.client.get("/api/cases")
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.json()
        self.assertIn("kpis", payload)
        self.assertIn("cases", payload)
        self.assertEqual(len(payload["cases"]), 5)
        self.assertEqual(payload["kpis"]["total_applications"], 5)

        detail_resp = self.client.get("/api/cases/NIR-2026-001")
        self.assertEqual(detail_resp.status_code, 200)
        case_data = detail_resp.json()
        self.assertEqual(case_data["case_id"], "NIR-2026-001")
        self.assertEqual(case_data["institution_name"], "Demo Technical Institute")
        self.assertTrue(len(case_data["extracted_fields"]) >= 8)
        self.assertTrue(len(case_data["documents"]) >= 4)
        self.assertTrue(len(case_data["compliance_results"]) == 5)

    # -------------------------------------------------------------------------
    # Test 3: Unknown case ID returns HTTP 404
    # -------------------------------------------------------------------------
    def test_03_unknown_case_id_returns_404(self) -> None:
        resp = self.client.get("/api/cases/NIR-2026-999")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # Test 4: PDF extraction and correct page numbering (Pages 1, 2, 3)
    # -------------------------------------------------------------------------
    def test_04_pdf_extraction_and_page_numbering(self) -> None:
        self.assertTrue(
            os.path.exists(SAMPLE_PDF_PATH),
            f"Sample PDF missing at expected path: {SAMPLE_PDF_PATH}",
        )
        extraction = extract_pdf_pages_and_fields(SAMPLE_PDF_PATH)
        self.assertEqual(extraction["page_count"], 3)
        pages = extraction["pages"]
        self.assertEqual([p["page_number"] for p in pages], [1, 2, 3])
        self.assertIn("NIR-2026-001", pages[0]["text"])
        self.assertIn("Fire Safety NOC Validity Date", pages[1]["text"])
        self.assertIn("Professors (Required: 2)", pages[2]["text"])

        fields_by_key = {f["field_key"]: f for f in extraction["extracted_fields"]}
        self.assertEqual(fields_by_key["institution_name"]["page_number"], 1)
        self.assertEqual(fields_by_key["fire_safety_noc_validity"]["page_number"], 2)
        self.assertEqual(fields_by_key["fire_safety_noc_validity"]["status"], "MISSING")
        self.assertEqual(fields_by_key["professor_cadre"]["page_number"], 3)
        self.assertEqual(fields_by_key["professor_cadre"]["status"], "REVIEW_REQUIRED")

    # -------------------------------------------------------------------------
    # Test 5: Invalid, empty, or corrupt PDF upload returns HTTP 400
    # -------------------------------------------------------------------------
    def test_05_invalid_empty_or_corrupt_pdf_upload(self) -> None:
        resp_txt = self.client.post(
            "/api/documents/upload",
            data={"application_id": "NIR-2026-001", "title": "Invalid Text File"},
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
        )
        self.assertEqual(resp_txt.status_code, 400)

        resp_empty = self.client.post(
            "/api/documents/upload",
            data={"application_id": "NIR-2026-001", "title": "Empty PDF"},
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        )
        self.assertEqual(resp_empty.status_code, 400)

        resp_corrupt = self.client.post(
            "/api/documents/upload",
            data={"application_id": "NIR-2026-001", "title": "Corrupt PDF"},
            files={"file": ("corrupt.pdf", io.BytesIO(b"NOT_A_VALID_PDF_BINARY"), "application/pdf")},
        )
        self.assertEqual(resp_corrupt.status_code, 400)

    # -------------------------------------------------------------------------
    # Test 6: Missing Fire Safety NOC validity date flagged with Page 2 evidence
    # -------------------------------------------------------------------------
    def test_06_missing_fire_safety_noc_flagged_page_2(self) -> None:
        resp = self.client.post(
            "/api/cases/NIR-2026-001/run-checks",
            json={"actor_name": "Sh. Vikramaditya Sen", "actor_role": "Reviewing Officer (Scrutiny Wing)"},
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["compliance_results"]
        rules_by_id = {r["rule_id"]: r for r in results}

        rule_doc_01 = rules_by_id.get("PROTOTYPE-RULE-DOC-01")
        self.assertIsNotNone(rule_doc_01)
        self.assertEqual(rule_doc_01["status"], "Fail")
        self.assertEqual(rule_doc_01["outcome_label"], "Possible deficiency")
        self.assertEqual(rule_doc_01["evidence_page"], 2)
        self.assertIn("Fire Safety NOC Validity Date", rule_doc_01["explanation"])
        self.assertTrue(rule_doc_01["is_prototype_rule"])

    # -------------------------------------------------------------------------
    # Test 7: Faculty cadre warning with Page 3 evidence
    # -------------------------------------------------------------------------
    def test_07_faculty_cadre_warning_page_3(self) -> None:
        resp = self.client.post(
            "/api/cases/NIR-2026-001/run-checks",
            json={"actor_name": "Sh. Vikramaditya Sen", "actor_role": "Reviewing Officer (Scrutiny Wing)"},
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["compliance_results"]
        rules_by_id = {r["rule_id"]: r for r in results}

        rule_fac_03 = rules_by_id.get("PROTOTYPE-RULE-FAC-03")
        self.assertIsNotNone(rule_fac_03)
        self.assertEqual(rule_fac_03["status"], "Requires Human Review")
        self.assertEqual(rule_fac_03["outcome_label"], "Unclear evidence / human review required")
        self.assertEqual(rule_fac_03["evidence_page"], 3)
        self.assertTrue(rule_fac_03["human_review_required"])
        self.assertIn("Joining Pending", rule_fac_03["evidence_quote"])

    # -------------------------------------------------------------------------
    # Test 8: EVC update validation and persistence
    # -------------------------------------------------------------------------
    def test_08_evc_update_validation_and_persistence(self) -> None:
        bad_resp = self.client.post(
            "/api/cases/NIR-2026-001/evc",
            json={
                "visit_status": "Scheduled",
                "proposed_date": "2026-11-04",
                "notes": "abc",
            },
        )
        self.assertEqual(bad_resp.status_code, 400)

        ok_resp = self.client.post(
            "/api/cases/NIR-2026-001/evc",
            json={
                "visit_status": "Scheduled",
                "proposed_date": "2026-11-04",
                "assigned_committee": "EVC Panel North-II (Chair: Prof. A.K. Chaturvedi)",
                "report_status": "Pending Visit",
                "notes": "Physical EVC scheduled for GPU lab and Professor joining verification.",
                "next_action": "Conduct EVC site inspection on 2026-11-04",
                "actor_name": "Sh. Vikramaditya Sen",
                "actor_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.assertEqual(ok_resp.status_code, 200)

        detail = self.client.get("/api/cases/NIR-2026-001").json()
        self.assertEqual(detail["evc_inspection"]["visit_status"], "Scheduled")
        self.assertEqual(detail["evc_inspection"]["scheduled_date"], "2026-11-04")
        self.assertEqual(detail["current_stage"], "EVC Inspection")

    # -------------------------------------------------------------------------
    # Test 9: Officer decision validation and persistence
    # -------------------------------------------------------------------------
    def test_09_officer_decision_validation_and_persistence(self) -> None:
        short_resp = self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Request Clarification",
                "remarks": "Too short",
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.assertIn(short_resp.status_code, (400, 422))

        valid_remarks = (
            "Issued deficiency query citing PROTOTYPE-RULE-DOC-01 (Page 2 missing Fire Safety NOC Validity Date) "
            "and requested Professor joining report verification."
        )
        ok_resp = self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Request Clarification",
                "remarks": valid_remarks,
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.assertEqual(ok_resp.status_code, 200)

        detail = self.client.get("/api/cases/NIR-2026-001").json()
        self.assertEqual(detail["current_stage"], "Deficiency Query Issued")
        self.assertTrue(len(detail["decisions"]) >= 1)
        self.assertEqual(detail["decisions"][0]["decision_type"], "Request Clarification")
        self.assertEqual(detail["decisions"][0]["remarks"], valid_remarks)

    # -------------------------------------------------------------------------
    # Test 10: Audit event creation and retrieval
    # -------------------------------------------------------------------------
    def test_10_audit_event_creation_and_retrieval(self) -> None:
        before_logs = self.client.get("/api/cases/NIR-2026-001/audit").json()["audit_logs"]
        initial_count = len(before_logs)

        self.client.post(
            "/api/cases/NIR-2026-001/run-checks",
            json={"actor_name": "Sh. Vikramaditya Sen", "actor_role": "Reviewing Officer (Scrutiny Wing)"},
        )

        after_logs = self.client.get("/api/cases/NIR-2026-001/audit").json()["audit_logs"]
        self.assertEqual(len(after_logs), initial_count + 1)
        latest = after_logs[0]
        self.assertEqual(latest["application_id"], "NIR-2026-001")
        self.assertEqual(latest["action_type"], "COMPLIANCE_CHECK")
        self.assertEqual(latest["actor_name"], "Sh. Vikramaditya Sen")

        global_audit = self.client.get("/api/audit").json()
        self.assertGreaterEqual(global_audit["total"], len(after_logs))

    # -------------------------------------------------------------------------
    # Test 11: Database isolation using a temporary test database
    # -------------------------------------------------------------------------
    def test_11_database_isolation_temporary_db(self) -> None:
        self.assertEqual(os.environ.get("NIRIKSH_DB_PATH"), TEST_DB_PATH)
        self.assertTrue(os.path.exists(TEST_DB_PATH))
        prod_db_path = os.path.join(BACKEND_DIR, "niriksh_demo.db")
        self.assertNotEqual(os.path.abspath(TEST_DB_PATH), os.path.abspath(prod_db_path))

    # -------------------------------------------------------------------------
    # Test 12: Repeated startup without duplicate seeding or loss of existing changes
    # -------------------------------------------------------------------------
    def test_12_repeated_startup_preserves_changes_without_duplicate_seeding(self) -> None:
        self.client.post(
            "/api/cases/NIR-2026-001/evc",
            json={
                "visit_status": "Completed",
                "proposed_date": "2026-11-04",
                "assigned_committee": "EVC Panel North-II",
                "report_status": "Uploaded & Verified (Demo Status)",
                "notes": "Physical inspection completed and verified during test 12.",
                "next_action": "Proceed to Officer Decision",
                "actor_name": "Sh. Vikramaditya Sen",
                "actor_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Record Recommendation",
                "remarks": "Recorded final recommendation after EVC completion; must survive repeated startups.",
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )

        before_cases = self.client.get("/api/cases").json()["cases"]
        before_audits = self.client.get("/api/audit").json()["audit_logs"]
        self.assertEqual(len(before_cases), 5)

        on_startup()
        on_startup()

        after_cases = self.client.get("/api/cases").json()["cases"]
        after_audits = self.client.get("/api/audit").json()["audit_logs"]
        self.assertEqual(len(after_cases), 5)
        self.assertEqual(len(after_audits), len(before_audits))

        nir_001 = self.client.get("/api/cases/NIR-2026-001").json()
        self.assertEqual(nir_001["current_stage"], "Decision Recorded")
        self.assertEqual(nir_001["evc_inspection"]["visit_status"], "Completed")
        self.assertEqual(
            nir_001["decisions"][0]["remarks"],
            "Recorded final recommendation after EVC completion; must survive repeated startups.",
        )

    # -------------------------------------------------------------------------
    # Test 13: Institution Portal isolation and internal note privacy
    # -------------------------------------------------------------------------
    def test_13_institution_portal_isolation_and_privacy(self) -> None:
        # Officer records a decision with an internal correction_note
        self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Request Clarification",
                "remarks": "Please provide renewed Fire Safety NOC validity date (Page 2).",
                "correction_note": "INTERNAL OFFICER NOTE: Check municipal fire registry manually.",
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )

        # Institution Portal query for Demo Technical Institute
        inst_resp = self.client.get(
            "/api/institution/cases", params={"institution_name": "Demo Technical Institute"}
        )
        self.assertEqual(inst_resp.status_code, 200)
        inst_data = inst_resp.json()
        # Demo Technical Institute has NIR-2026-001 (Submitted) and NIR-2026-006 (Draft)
        self.assertEqual(inst_data["metrics"]["total_applications"], 2)
        self.assertEqual(inst_data["metrics"]["draft_applications"], 1)
        self.assertEqual(inst_data["metrics"]["action_required"], 1)
        for c in inst_data["cases"]:
            self.assertEqual(c["institution_name"], "Demo Technical Institute")
            for dec in c.get("decisions", []):
                self.assertNotIn("correction_note", dec)

    # -------------------------------------------------------------------------
    # Test 14: Separate RAG AI Suggestions + Deterministic Rules & Supervisor View
    # -------------------------------------------------------------------------
    def test_14_rag_separation_and_supervisor_overview(self) -> None:
        chk = self.client.post("/api/cases/NIR-2026-001/run-checks").json()
        self.assertEqual(len(chk["compliance_results"]), 5)
        self.assertTrue(len(chk["ai_suggestions"]) >= 3)
        self.assertTrue(len(chk["findings_summary"]) >= 8)

        # Verify AI suggestions are explicitly labeled as advisory and separate from deterministic rules
        for sug in chk["ai_suggestions"]:
            self.assertEqual(sug["source_type"], "AI_RAG_SUGGESTION")
            self.assertIn("Not a Verified Fact", sug["source_label"])

        sup = self.client.get("/api/supervisor/overview")
        self.assertEqual(sup.status_code, 200)
        sup_data = sup.json()
        self.assertEqual(sup_data["summary"]["total_submitted_cases"], 5)
        self.assertGreaterEqual(sup_data["summary"]["inspection_delays_count"], 1)

    # -------------------------------------------------------------------------
    # Test 15: Complete 10-Step Acceptance Test Journey (Section H)
    # -------------------------------------------------------------------------
    def test_15_complete_10_step_acceptance_journey(self) -> None:
        # Step 1 & 2: Open Institution Portal, inspect Demo Technical Institute applications & documents
        inst_list = self.client.get(
            "/api/institution/cases", params={"institution_name": "Demo Technical Institute"}
        ).json()
        self.assertEqual(inst_list["metrics"]["total_applications"], 2)
        case_001_inst = self.client.get(
            "/api/cases/NIR-2026-001", params={"for_institution": True}
        ).json()
        self.assertEqual(len(case_001_inst["documents"]), 4)

        # Step 3 & 4: Switch to AICTE Portal, open NIR-2026-001 and run compliance checks
        chk_resp = self.client.post(
            "/api/cases/NIR-2026-001/run-checks",
            json={"actor_name": "Sh. Vikramaditya Sen", "actor_role": "Reviewing Officer (Scrutiny Wing)"},
        )
        self.assertEqual(chk_resp.status_code, 200)
        chk_data = chk_resp.json()
        self.assertEqual(chk_data["compliance_status"], "Compliance Flags Raised")

        # Step 5: Show a finding with a source-page reference (Page 2 Fire Safety NOC Validity Date)
        doc01 = next(r for r in chk_data["compliance_results"] if r["rule_id"] == "PROTOTYPE-RULE-DOC-01")
        self.assertEqual(doc01["evidence_page"], 2)
        self.assertEqual(doc01["outcome_label"], "Possible deficiency")

        # Step 6: Request clarification and record officer remarks
        clar_resp = self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Request Clarification",
                "remarks": "Please upload the renewed Fire Safety NOC with explicit validity date (Page 2, Section 2.2).",
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.assertEqual(clar_resp.status_code, 200)
        self.assertEqual(clar_resp.json()["case"]["current_stage"], "Deficiency Query Issued")

        # Step 7: Return to Institution Portal, verify Clarification state, and resubmit rectified document
        resub_resp = self.client.post(
            "/api/cases/NIR-2026-001/resubmit",
            json={
                "actor_name": "Dr. R.K. Sharma (Institute Nodal Officer)",
                "actor_role": "Institution Nodal Officer",
                "response_remarks": "Uploaded certified Fire Safety NOC renewal (FS-UP-2026-9921) valid through 2028-06-30.",
                "rectified_field_key": "fire_safety_noc_validity",
                "rectified_field_value": "Valid till 2028-06-30 (Rectified Cert #FS-UP-2026-9921)",
                "document_title": "Supplementary Fire Safety NOC Renewal (FS-UP-2026-9921)",
                "document_filename": "Fire_Safety_NOC_Rectified_2028.pdf",
            },
        )
        self.assertEqual(resub_resp.status_code, 200)
        resub_case = resub_resp.json()["case"]
        self.assertEqual(resub_case["current_stage"], "Compliance Review")
        # Mandatory field & annexure checks now pass!
        rules_after_resub = {r["rule_id"]: r for r in resub_case["compliance_results"]}
        self.assertEqual(rules_after_resub["PROTOTYPE-RULE-DOC-01"]["status"], "Pass")
        self.assertEqual(rules_after_resub["PROTOTYPE-RULE-DOC-02"]["status"], "Pass")

        # Step 8: Show EVC stage when applicable and record completed visit report
        evc_resp = self.client.post(
            "/api/cases/NIR-2026-001/evc",
            json={
                "visit_status": "Completed",
                "proposed_date": "2026-11-04",
                "assigned_committee": "EVC Panel North-II (Chair: Prof. A.K. Chaturvedi)",
                "report_status": "Uploaded & Verified (Demo Status)",
                "notes": "EVC verified 2x NVIDIA A100 GPU Lab, Fire Safety NOC original, and 2nd Professor joining report.",
                "next_action": "Return to Reviewing Officer for final approval decision",
                "actor_name": "Prof. A.K. Chaturvedi (EVC Chair)",
                "actor_role": "Expert Visit Committee",
            },
        )
        self.assertEqual(evc_resp.status_code, 200)
        evc_case = evc_resp.json()["case"]
        self.assertEqual(evc_case["current_stage"], "Officer Decision")

        # Step 9: Record the authorised officer's final decision (Approve)
        dec_resp = self.client.post(
            "/api/cases/NIR-2026-001/decision",
            json={
                "decision_type": "Approve",
                "remarks": "All statutory deficiencies rectified, EVC report verified, and compliance checks satisfied. Approved for AY 2026-27.",
                "officer_name": "Sh. Vikramaditya Sen",
                "officer_role": "Reviewing Officer (Scrutiny Wing)",
            },
        )
        self.assertEqual(dec_resp.status_code, 200)
        final_case = dec_resp.json()["case"]
        self.assertEqual(final_case["current_stage"], "Decision Recorded")
        self.assertEqual(final_case["decisions"][0]["decision_type"], "Approve")

        # Step 10: Open the audit trail and verify all recorded actions chronologically
        audit_logs = self.client.get("/api/cases/NIR-2026-001/audit").json()["audit_logs"]
        action_types = [log["action_type"] for log in audit_logs]
        self.assertIn("COMPLIANCE_CHECK", action_types)
        self.assertIn("CLARIFICATION_RESUBMITTED", action_types)
        self.assertIn("EVC_UPDATED", action_types)
        self.assertIn("DECISION_RECORDED", action_types)


if __name__ == "__main__":
    unittest.main(verbosity=2)
