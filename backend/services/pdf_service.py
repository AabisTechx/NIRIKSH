"""
PDF Text Extraction and Field Parsing Service for NIRIKSH
Team CODE RED — Smart India Hackathon 2026

Attempts extraction via PyMuPDF (fitz) first if installed; falls back cleanly to pdfplumber / pypdf
so that extraction works reliably across all Python environments.
Raises ValueError on empty, corrupt, or unreadable PDFs so the API layer can return HTTP 400.
"""

import re
from typing import Any, Dict, List

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


def extract_pdf_pages_and_fields(pdf_path: str) -> Dict[str, Any]:
    """
    Extracts page-by-page text from a local PDF file and parses structured AICTE dossier fields
    with page references and source quotes.
    Raises ValueError if the file is not a valid readable PDF.
    """
    pages_data: List[Dict[str, Any]] = []
    engine_used = "fallback"

    if not pdf_path or not pdf_path.lower().endswith(".pdf"):
        raise ValueError("Unsupported file format. Only .pdf files are accepted.")

    try:
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                raise ValueError("Invalid or corrupt PDF header. File does not begin with %PDF- signature.")
    except OSError as exc:
        raise ValueError(f"Unable to read uploaded PDF file: {exc}") from exc

    if HAS_PYMUPDF:
        try:
            doc = fitz.open(pdf_path)
            engine_used = "PyMuPDF (fitz)"
            for idx, page in enumerate(doc):
                text = page.get_text("text") or ""
                pages_data.append({"page_number": idx + 1, "page": idx + 1, "text": text.strip()})
            doc.close()
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PDF file (PyMuPDF parser error): {exc}") from exc
    elif HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                engine_used = "pdfplumber"
                for idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages_data.append({"page_number": idx + 1, "page": idx + 1, "text": text.strip()})
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PDF file (pdfplumber parser error): {exc}") from exc
    elif HAS_PYPDF:
        try:
            reader = PdfReader(pdf_path)
            engine_used = "pypdf"
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_data.append({"page_number": idx + 1, "page": idx + 1, "text": text.strip()})
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PDF file (pypdf parser error): {exc}") from exc
    else:
        raise RuntimeError("No PDF extraction library (PyMuPDF, pdfplumber, or pypdf) is installed.")

    if not pages_data:
        raise ValueError("The uploaded PDF contains 0 readable pages.")

    extracted_fields = parse_dossier_fields_from_pages(pages_data)
    return {
        "engine_used": engine_used,
        "page_count": len(pages_data),
        "pages": pages_data,
        "extracted_fields": extracted_fields,
    }


def parse_dossier_fields_from_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deterministic regex/keyword parser over extracted PDF pages to populate structured dossier fields
    with exact page numbers, verbatim source snippets, and source_type='PDF_EXTRACTED'.
    Supports both table-formatted PDF rows and colon-delimited key: value lines.
    """
    patterns = [
        {
            "field_key": "application_id",
            "field_label": "Application ID",
            "regex": r"Application\s*ID\s*[:\-]?\s*(NIR-\d{4}-\d{3})",
            "expected_norm": "Valid NIR-YYYY-NNN identifier",
        },
        {
            "field_key": "pid",
            "field_label": "Permanent Institute ID (PID)",
            "regex": r"Permanent\s*Institute\s*ID\s*\(PID\)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Valid PID-DEMO-YYYY-NNNN identifier",
        },
        {
            "field_key": "institution_name",
            "field_label": "Institution Name",
            "regex": r"Institution\s*Name\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Registered Technical Institution",
        },
        {
            "field_key": "application_type",
            "field_label": "Application Type",
            "regex": r"Application\s*Type\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Valid AICTE Application Category",
        },
        {
            "field_key": "proposed_programme",
            "field_label": "Primary Proposed Programme",
            "regex": r"(?:Primary\s+Proposed\s+Programme|Proposed\s+Programme\s*[:\-])\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "AICTE Approved Nomenclature",
        },
        {
            "field_key": "proposed_intake",
            "field_label": "Proposed Intake (AI & DS)",
            "regex": r"Proposed\s*Intake(?:\s*\(AI\s*&\s*DS\))?\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Multiples of 30 / 60 seats",
        },
        {
            "field_key": "campus_address",
            "field_label": "Campus Address",
            "regex": r"Campus\s*Address\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Verified Contiguous Campus Location",
        },
        {
            "field_key": "built_up_area",
            "field_label": "Total Built-up Area Available",
            "regex": r"Total\s*(?:Built-up\s*(?:Academic\s*)?Area(?:\s*Available)?|Instructional\s*Area)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Minimum 6,200 Sq.m for proposed intake",
        },
        {
            "field_key": "occupancy_certificate",
            "field_label": "Occupancy Certificate (OC)",
            "regex": r"Occupancy\s*Certificate\s*\(OC\)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Valid Competent Authority OC",
        },
        {
            "field_key": "fire_safety_noc_ref",
            "field_label": "Fire Safety NOC Reference No.",
            "regex": r"Fire\s*Safety\s*NOC\s*(?:Reference\s*No\.|Number)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Registered Municipal Fire Safety NOC",
        },
        {
            "field_key": "fire_safety_noc_validity",
            "field_label": "Fire Safety NOC Validity Date",
            "regex": r"Fire\s*Safety\s*NOC\s*Validity\s*Date\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Valid date covering AY 2026-27",
        },
        {
            "field_key": "total_faculty",
            "field_label": "Sanctioned & Appointed Faculty",
            "regex": r"(?:Sanctioned\s*&\s*Appointed\s*Faculty|Total\s*Full-Time\s*Faculty\s*Appointed)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Minimum 12 Regular Faculty (1:20 Norm)",
        },
        {
            "field_key": "calculated_sfr",
            "field_label": "Calculated Student-Faculty Ratio",
            "regex": r"Calculated\s*Student-Faculty\s*Ratio\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "1:20 or better",
        },
        {
            "field_key": "professor_cadre",
            "field_label": "Professors (Required: 2)",
            "regex": r"Professors?(?:\s*Cadre)?\s*\(Required\s*[:\-]?\s*2\)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "2 Professors & 3 Associate Professors",
        },
        {
            "field_key": "affidavit_ref",
            "field_label": "Affidavit Format (Rs. 100 Stamp)",
            "regex": r"Affidavit\s*Format\s*\(Rs\.\s*100\s*Stamp\)\s*[:\-]?\s*([^\n]+)",
            "expected_norm": "Notarised Digital Affidavit",
        },
    ]

    results: List[Dict[str, Any]] = []

    for pat in patterns:
        matched_val = None
        matched_page = 1
        matched_snippet = ""

        for p in pages:
            p_num = p["page_number"]
            p_text = p["text"]
            m = re.search(pat["regex"], p_text, flags=re.IGNORECASE)
            if m:
                matched_val = m.group(1).strip()
                matched_page = p_num
                matched_snippet = m.group(0).strip()
                break

        status = "VERIFIED"
        confidence_note = f"Extracted and verified from PDF text layer (Page {matched_page})."

        if (
            not matched_val
            or "MISSING" in matched_val.upper()
            or "NOT PROVIDED" in matched_val.upper()
            or "BLANK" in matched_val.upper()
        ):
            status = "MISSING"
            confidence_note = f"Blank / missing field detected on submitted PDF form (Page {matched_page})."
        elif "PENDING" in matched_val.upper() or "WARNING" in matched_val.upper():
            status = "REVIEW_REQUIRED"
            confidence_note = f"Extracted from Page {matched_page}; flagged for human/EVC verification."

        results.append(
            {
                "field_key": pat["field_key"],
                "field_label": pat["field_label"],
                "label": pat["field_label"],
                "extracted_value": matched_val if matched_val else "[MISSING IN SUBMISSION — BLANK FIELD ON FORM]",
                "value": None if status == "MISSING" else matched_val,
                "expected_norm": pat["expected_norm"],
                "page_number": matched_page,
                "source_page": matched_page,
                "source_snippet": matched_snippet or "Field pattern not matched in document text",
                "confidence_note": confidence_note,
                "notes": confidence_note,
                "status": status,
                "source_type": "PDF_EXTRACTED",
                "is_demo_extracted": True,
            }
        )

    return results
