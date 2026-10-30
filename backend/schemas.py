"""
Pydantic Schemas for NIRIKSH API Request/Response Validation
Team CODE RED — Smart India Hackathon 2026
Supports both Institution / College Portal and AICTE / Government Portal payloads.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedFieldSchema(BaseModel):
    field_key: str
    field_label: str
    extracted_value: Optional[str] = None
    expected_norm: Optional[str] = None
    page_number: int = 1
    source_snippet: str = ""
    confidence_note: str = "Verified PDF Text"
    status: str = "VERIFIED"  # VERIFIED | MISSING | REVIEW_REQUIRED
    source_type: str = "PDF_EXTRACTED"  # PDF_EXTRACTED | SEEDED_CASE_DATA


class DocumentItemSchema(BaseModel):
    doc_id: str
    title: str
    category: str
    filename: str
    pages: int
    uploaded_at: str
    status: str  # Verified | Missing Field | Pending Scrutiny | Uploaded
    notes: str = ""
    extracted_pages_text: List[dict] = Field(default_factory=list)


class RuleResultSchema(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    status: str  # Pass | Fail | Warning | Pending Verification | Requires Human Review
    severity: str = "HIGH"  # CRITICAL | HIGH | AMBER | NORMAL
    explanation: str
    evidence_quote: str
    evidence_page: int
    corrective_action: str
    human_review_required: bool = False
    is_prototype_rule: bool = True
    evaluated_at: str


class EvcChecklistItemSchema(BaseModel):
    item_id: str
    label: str
    status: str  # Verified | Observation Noted | Pending


class EvcInspectionSchema(BaseModel):
    required: bool
    inspection_mode: str
    committee_chair: str
    scheduled_date: str
    visit_status: str
    report_uploaded: str
    observations: str
    recommendation: str
    checklist: List[EvcChecklistItemSchema] = Field(default_factory=list)
    updated_by: str = ""
    updated_at: str = ""


class OfficerDecisionPayload(BaseModel):
    officer_name: str = Field(default="Sh. Vikramaditya Sen", min_length=2)
    officer_role: str = Field(default="Reviewing Officer (Scrutiny Wing)", min_length=2)
    decision: Optional[str] = None
    decision_type: Optional[str] = None
    remarks: str = Field(..., min_length=10, description="Mandatory audit remarks justifying the decision")
    correction_note: Optional[str] = Field(
        default=None,
        description="Optional internal officer-only note (hidden from Institution Portal)",
    )
    confirmed: Optional[bool] = True


class EvcUpdatePayload(BaseModel):
    actor_name: str = Field(default="Sh. Vikramaditya Sen", min_length=2)
    actor_role: str = Field(default="Reviewing Officer (Scrutiny Wing)", min_length=2)
    visit_status: str = Field(..., min_length=2)
    scheduled_date: Optional[str] = None
    proposed_date: Optional[str] = None
    assigned_committee: Optional[str] = None
    report_uploaded: Optional[str] = None
    report_status: Optional[str] = None
    observations: Optional[str] = None
    notes: Optional[str] = None
    recommendation: Optional[str] = None
    next_action: Optional[str] = None
    checklist: Optional[List[EvcChecklistItemSchema]] = None


class VerifyDocumentPayload(BaseModel):
    actor_name: str = Field(default="Sh. Vikramaditya Sen")
    actor_role: str = Field(default="Reviewing Officer (Scrutiny Wing)")
    status: str = Field(..., description="Verified | Pending Scrutiny | Missing Field | VERIFIED | PENDING_VERIFICATION")
    remarks: Optional[str] = Field(default="Updated annexure verification status after document inspection.")


class DemoFieldTogglePayload(BaseModel):
    actor_name: str = Field(default="Sh. Vikramaditya Sen")
    actor_role: str = Field(default="Reviewing Officer (Scrutiny Wing)")
    resolve_deficiency: bool = Field(default=True)


class RunChecksPayload(BaseModel):
    actor_name: str = Field(default="Sh. Vikramaditya Sen")
    actor_role: str = Field(default="Reviewing Officer (Scrutiny Wing)")


class CreateApplicationPayload(BaseModel):
    institution_name: str = Field(..., min_length=3)
    aishe_id: str = Field(default="PID-DEMO-2021-0842")
    state: str = Field(default="Uttar Pradesh")
    city: str = Field(default="Lucknow")
    application_type: str = Field(..., min_length=3)
    programme: str = Field(..., min_length=3)
    proposed_intake: int = Field(default=60, ge=15, le=600)
    academic_year: str = Field(default="2026-27")
    save_as_draft: bool = Field(default=False)
    evc_required: bool = Field(default=True)
    actor_name: str = Field(default="Dr. R.K. Sharma (Institute Nodal Officer)")


class ClarificationResubmitPayload(BaseModel):
    actor_name: str = Field(default="Dr. R.K. Sharma (Institute Nodal Officer)")
    actor_role: str = Field(default="Institution Nodal Officer")
    response_remarks: str = Field(..., min_length=8, description="Institution response explaining rectification")
    rectified_field_key: Optional[str] = Field(default="fire_safety_noc_validity")
    rectified_field_value: Optional[str] = Field(
        default="Valid till 2028-06-30 (Rectified Cert #FS-UP-2026-9921)"
    )
    document_title: Optional[str] = Field(
        default="Supplementary Clarification Annexure — Fire Safety NOC Renewal (FS-UP-2026-9921)"
    )
    document_filename: Optional[str] = Field(default="Fire_Safety_NOC_Rectified_2028.pdf")
