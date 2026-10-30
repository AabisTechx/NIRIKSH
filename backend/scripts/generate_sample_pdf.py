#!/usr/bin/env python3
"""
Generates realistic multi-page synthetic sample PDFs for NIRIKSH demo cases
and renders high-DPI PNG previews of each page for the in-app document viewer.
"""
import os
import json
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import pypdfium2 as pdfium
import pdfplumber

BASE_DIR = "/working_dir/c_f76ad8a97b579fbf/artifacts/file_generation/ttl=63d/intermediate"
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "niriksh/backend/sample_data")
os.makedirs(SAMPLE_DATA_DIR, exist_ok=True)


def draw_header(c, width, height, page_num, total_pages, doc_ref):
    # Top institutional banner
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(15 * mm, height - 28 * mm, width - 30 * mm, 16 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, height - 19 * mm, "SYNTHETIC DEMO SUBMISSION — NIRIKSH PROTOTYPE (SIH 2026)")
    c.setFont("Helvetica", 8.5)
    c.drawString(20 * mm, height - 24.5 * mm, "Not an official AICTE document. Prepared for workflow & compliance rule verification.")
    c.drawRightString(width - 20 * mm, height - 19 * mm, f"Ref: {doc_ref}")
    c.drawRightString(width - 20 * mm, height - 24.5 * mm, f"Page {page_num} of {total_pages}")

    # Bottom footer
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(15 * mm, 18 * mm, width - 15 * mm, 18 * mm)
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 8)
    c.drawString(15 * mm, 13 * mm, "NIRIKSH Demo Case Dossier | Case ID: NIR-2026-001 | Demo Technical Institute")
    c.drawRightString(width - 15 * mm, 13 * mm, f"Page {page_num} of {total_pages}")


def draw_section_title(c, x, y, width, title):
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.rect(x, y - 6 * mm, width, 8 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 3 * mm, y - 3.5 * mm, title)
    return y - 12 * mm


def draw_kv_row(c, x, y, col1_w, col2_w, label, value, highlight_missing=False):
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    if highlight_missing:
        c.setFillColor(colors.HexColor("#FEF2F2"))
        c.rect(x, y - 5.5 * mm, col1_w + col2_w, 7.5 * mm, fill=1, stroke=1)
    else:
        c.setFillColor(colors.white)
        c.rect(x, y - 5.5 * mm, col1_w + col2_w, 7.5 * mm, fill=1, stroke=1)
    c.line(x + col1_w, y - 5.5 * mm, x + col1_w, y + 2 * mm)

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 2.5 * mm, y - 3 * mm, label)

    if highlight_missing:
        c.setFillColor(colors.HexColor("#B91C1C"))
        c.setFont("Helvetica-Bold", 8.5)
    else:
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8.5)
    c.drawString(x + col1_w + 2.5 * mm, y - 3 * mm, value)
    return y - 7.5 * mm


def generate_nir_2026_001_pdf(filepath):
    width, height = A4
    content_w = width - 30 * mm
    x0 = 15 * mm
    c = canvas.Canvas(filepath, pagesize=A4)
    c.setTitle("NIR-2026-001 Application Dossier - Demo Technical Institute")
    c.setAuthor("Demo Technical Institute (Synthetic Demo Data)")

    # ================= PAGE 1 =================
    draw_header(c, width, height, 1, 3, "NIR-2026-001 / AY 2026-27")
    y = height - 38 * mm

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x0, y, "PART I: INSTITUTIONAL APPLICATION & PROGRAMME PROPOSAL")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Application for Extension of Approval (EoA) & New Programme Addition (AY 2026-27)")
    y -= 8 * mm

    y = draw_section_title(c, x0, y, content_w, "1.1 Institution & Application Particulars")
    rows_1 = [
        ("Application ID", "NIR-2026-001", False),
        ("Permanent Institute ID (PID)", "PID-DEMO-2021-0842 (Synthetic)", False),
        ("Institution Name", "Demo Technical Institute", False),
        ("Institution Type", "Private Self-Financed Technical Institution", False),
        ("Parent Trust / Society", "Vidyapeeth Technical Education Foundation, Lucknow", False),
        ("Campus Address", "Plot No. 14, Knowledge Park Phase II, Gomti Nagar Ext., Lucknow, UP - 226010", False),
        ("Affiliating University", "Dr. A.P.J. Abdul Kalam Technical University (AKTU), Lucknow (Demo Ref)", False),
        ("Application Type", "Extension of Approval (EoA) + New Course (B.Tech AI & Data Science)", False),
        ("Academic Year", "2026-27", False),
        ("Date of Submission", "2026-10-18", False),
        ("Head of Institution / Principal", "Dr. Rajeshwar Prasad Verma (Ph.D., Computer Science)", False),
        ("Official Contact Email", "registrar@demotech-edu.example.org", False),
    ]
    for label, val, miss in rows_1:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 6 * mm
    y = draw_section_title(c, x0, y, content_w, "1.2 Proposed Programme & Intake Matrix (Page 1 Evidence)")
    rows_2 = [
        ("Primary Proposed Programme", "B.Tech in Artificial Intelligence and Data Science", False),
        ("Programme Level & Duration", "Undergraduate Degree (UG) — 4 Years Full-Time", False),
        ("Existing Approved Intake (CSE)", "120 Seats", False),
        ("Proposed Intake (AI & DS)", "120 Seats (2 Divisions of 60 Seats each)", False),
        ("Total Institutional Intake", "240 Seats", False),
        ("AICTE Processing Fee Ref", "TXN-DEMO-9841204 (Paid Rs. 1,50,000 on 2026-10-17)", False),
    ]
    for label, val, miss in rows_2:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 8 * mm
    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Oblique", 8.5)
    c.drawString(x0, y, "Declaration: All particulars stated on Page 1 are extracted from the institutional submission form.")

    c.showPage()

    # ================= PAGE 2 =================
    draw_header(c, width, height, 2, 3, "NIR-2026-001 / AY 2026-27")
    y = height - 38 * mm

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x0, y, "PART II: INFRASTRUCTURE, LAND, BUILT-UP AREA & STATUTORY NOCs")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Physical Infrastructure Verification & Statutory Safety Certificates (Page 2 Evidence)")
    y -= 8 * mm

    y = draw_section_title(c, x0, y, content_w, "2.1 Land & Built-up Area Particulars")
    rows_p2_1 = [
        ("Total Contiguous Land Area", "4.25 Acres (Freehold Lease via Development Authority)", False),
        ("Land Use Certificate (CLU)", "Issued by Competent Authority — Ref: CLU/LKO/2021/419 (Verified)", False),
        ("Total Instructional Area", "4,850 Sq. Meters (Norm Requirement: >= 4,200 Sq. Meters)", False),
        ("Administrative & Amenities Area", "2,000 Sq. Meters", False),
        ("Total Built-up Area Available", "6,850 Sq. Meters (PASS — Exceeds Minimum Norm of 6,200 Sq.m)", False),
        ("Computing Laboratories", "6 Dedicated Labs with 260 Workstations (1:4 PC Ratio Met)", False),
        ("Central Library Holdings", "14,200 Volumes, 42 Print Journals, Digital e-Journal Consortium", False),
        ("Barrier-Free Environment", "Ramps, Tactile Paths, Elevator & Accessible Washrooms Installed", False),
    ]
    for label, val, miss in rows_p2_1:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 6 * mm
    y = draw_section_title(c, x0, y, content_w, "2.2 Building Plan & Statutory Safety Certificates")
    rows_p2_2 = [
        ("Building Plan Approval Authority", "Lucknow Development Authority (Permit #LDA/BP/2021/882)", False),
        ("Occupancy Certificate (OC)", "OC/LKO/2022/119 — Issued 14-Aug-2022 (Attached & Verified)", False),
        ("Structural Stability Certificate", "Issued by Registered Structural Engineer (Valid till 2028)", False),
        ("Fire Safety NOC Reference No.", "FS-UP-2024-0918 (Provisional Renewal Application Submitted)", False),
        ("Fire Safety NOC Validity Date", "[MISSING IN SUBMISSION — BLANK FIELD ON FORM]", True),
        ("Potable Water & Sanitary Cert.", "Municipal Health Officer Cert #MHO/2026/301 (Valid till Mar 2027)", False),
    ]
    for label, val, miss in rows_p2_2:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 8 * mm
    c.setFillColor(colors.HexColor("#FEF2F2"))
    c.setStrokeColor(colors.HexColor("#FECACA"))
    c.rect(x0, y - 14 * mm, content_w, 16 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#991B1B"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x0 + 3 * mm, y - 4 * mm, "SCRUTINY OBSERVATION NOTE (PAGE 2):")
    c.setFont("Helvetica", 8.5)
    c.drawString(x0 + 3 * mm, y - 9.5 * mm, "Field 'Fire Safety NOC Validity Date' is blank in Section 2.2. Furthermore, the signed")
    c.drawString(x0 + 3 * mm, y - 13 * mm, "annexure 'Fire Safety NOC Certificate' is pending verification in the Document Register.")

    c.showPage()

    # ================= PAGE 3 =================
    draw_header(c, width, height, 3, 3, "NIR-2026-001 / AY 2026-27")
    y = height - 38 * mm

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x0, y, "PART III: FACULTY CADRE RATIO, LAB EQUIPMENT & AFFIDAVIT")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Teaching Staff Roster Summary, Student-Faculty Ratio (SFR) & EVC Readiness (Page 3 Evidence)")
    y -= 8 * mm

    y = draw_section_title(c, x0, y, content_w, "3.1 Faculty Strength & Student-Faculty Ratio (SFR)")
    rows_p3_1 = [
        ("Total Approved + Proposed Intake", "240 Students (Across CSE & Proposed AI-DS)", False),
        ("Required Faculty (1:20 Norm)", "12 Regular Faculty Members minimum", False),
        ("Sanctioned & Appointed Faculty", "14 Regular Full-Time Faculty Members (Verified Payroll & PAN)", False),
        ("Calculated Student-Faculty Ratio", "1 : 17.1 (WARNING — Cadre Distribution Needs EVC Verification)", False),
        ("Professors (Required: 2)", "1 Appointed (Dr. R.P. Verma) — 1 Offer Letter Issued (Joining Pending)", False),
        ("Associate Professors (Req: 3)", "3 Appointed and Full-Time On-Roll", False),
        ("Assistant Professors (Req: 7)", "10 Appointed and Full-Time On-Roll", False),
        ("Faculty Aadhaar / PAN Seeding", "14 / 14 Verified on Demo Payroll Register", False),
    ]
    for label, val, miss in rows_p3_1:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 6 * mm
    y = draw_section_title(c, x0, y, content_w, "3.2 AI & Data Science Lab Readiness & Digital Affidavit")
    rows_p3_2 = [
        ("High-Performance GPU Server Lab", "2x NVIDIA A100 Nodes + 64 Core Compute Cluster Installed", False),
        ("Open-Source AI Stack & Licenses", "Python, PyTorch, TensorFlow, PostgreSQL, Linux Lab Ready", False),
        ("EVC Inspection Applicability", "REQUIRED (New Course Addition + Physical Lab & Cadre Verification)", False),
        ("Affidavit Format (Rs. 100 Stamp)", "Notarised Digital Affidavit Ref #AFF-UP-2026-88412", False),
        ("Authorised Signatory", "Dr. Rajeshwar Prasad Verma, Principal & Member Secretary", False),
        ("Digital Signature Timestamp", "2026-10-18 16:42:10 IST (Verified)", False),
    ]
    for label, val, miss in rows_p3_2:
        y = draw_kv_row(c, x0, y, 62 * mm, content_w - 62 * mm, label, val, miss)

    y -= 8 * mm
    c.setFillColor(colors.HexColor("#FFFBEB"))
    c.setStrokeColor(colors.HexColor("#FDE68A"))
    c.rect(x0, y - 14 * mm, content_w, 16 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#92400E"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x0 + 3 * mm, y - 4 * mm, "HUMAN REVIEW & EVC VERIFICATION NOTE (PAGE 3):")
    c.setFont("Helvetica", 8.5)
    c.drawString(x0 + 3 * mm, y - 9.5 * mm, "Overall SFR is 1:17.1 (within 1:20 threshold), but Professor cadre shows 1 onboarded and")
    c.drawString(x0 + 3 * mm, y - 13 * mm, "1 joining pending. Expert Visit Committee (EVC) physical verification of GPU lab & faculty required.")

    c.save()


def render_pdf_pages_and_extract(filepath):
    doc = pdfium.PdfDocument(filepath)
    page_images_b64 = []
    for idx in range(len(doc)):
        page = doc[idx]
        bitmap = page.render(scale=1.5)
        pil_img = bitmap.to_pil()
        img_path = os.path.join(SAMPLE_DATA_DIR, f"NIR-2026-001_page_{idx+1}.png")
        pil_img.save(img_path, format="PNG", optimize=True)
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
            page_images_b64.append(f"data:image/png;base64,{b64}")

    pages_text = []
    with pdfplumber.open(filepath) as pdf:
        for i, p in enumerate(pdf.pages):
            txt = p.extract_text() or ""
            pages_text.append({"page": i + 1, "text": txt, "char_count": len(txt)})

    with open(filepath, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("ascii")

    summary = {
        "pdf_path": filepath,
        "page_count": len(pages_text),
        "pages_text": pages_text,
        "page_images_b64": page_images_b64,
        "pdf_b64": f"data:application/pdf;base64,{pdf_b64}"
    }
    with open(os.path.join(SAMPLE_DATA_DIR, "nir_2026_001_extracted_assets.json"), "w") as out:
        json.dump(summary, out, indent=2)
    print(f"Generated {filepath} ({len(pages_text)} pages) and rendered PNG previews.")


if __name__ == "__main__":
    pdf_path = os.path.join(SAMPLE_DATA_DIR, "NIR-2026-001_Demo_Technical_Institute.pdf")
    generate_nir_2026_001_pdf(pdf_path)
    render_pdf_pages_and_extract(pdf_path)
