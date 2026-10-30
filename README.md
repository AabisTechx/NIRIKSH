# NIRIKSH — Institutional Approval & Compliance System
**Smart India Hackathon 2026 · Team CODERANGER**

NIRIKSH is a two-portal government approval and compliance prototype aligned with the SIH 2026 Technical Approach:
1. **Institution / College Portal** — Separate login screen, uncluttered dashboard, application & PDF document submission, 5-stage application status tracker, and clarification resubmission workflow.
2. **AICTE / Officer Portal** — Separate login screen, officer scrutiny dashboard, document & page-reference extraction viewer, parallel compliance review (**Deterministic Rule Engine** + **AI-Assisted Analysis / RAG**), clarification & officer decision workflow, Expert Visit Committee (EVC) inspection management, supervisor monitoring, and chronological audit trail.

## 1. Windows Setup & How to Run (3 Easy Ways)

### Option A — 1-Click Windows Launcher (Recommended)
1. Extract the ZIP folder on your Windows PC.
2. Double-click **`START_NIRIKSH_WINDOWS.bat`** inside the `niriksh` folder.
3. It will automatically start the FastAPI + SQLite server and open **`http://127.0.0.1:8000`** in your browser.

### Option B — Run from VS Code Terminal (Single Terminal Command)
Open your terminal in the extracted folder and run:

```powershell
cd niriksh\backend
pip install fastapi uvicorn sqlalchemy pydantic pymupdf python-multipart
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Then open **`http://127.0.0.1:8000`** in Chrome or Edge. Both the Two-Portal Frontend UI and the FastAPI + SQLite Backend run together on `http://127.0.0.1:8000`.

### Option C — Instant Browser Mode (Zero Installation)
If you want to demonstrate the UI immediately without starting the Python backend:
- Double-click **`niriksh\frontend\public\index.html`** to open it directly in Chrome/Edge, OR run:
  ```powershell
  cd niriksh\frontend\public
  python -m http.server 3000
  ```
  and open **`http://localhost:3000`**.

## 2. Working Demo Login Credentials

Credentials are pre-filled on both login screens (and also have 1-click auto-fill buttons):

| Portal | Role / Account | Demo Login ID | Demo Password |
| :--- | :--- | :--- | :--- |
| **1. Institution / College Portal** | Demo Technical Institute, Lucknow (`NIR-2026-001`) | `INST-DTI-2026` | `Niriksh@2026` |
| **1. Institution / College Portal** | Kaveri Polytechnic & Rural Tech Centre (`NIR-2026-004`) | `INST-KAVERI-2026` | `Niriksh@2026` |
| **2. AICTE / Officer Portal** | Scrutiny / Reviewing Officer (Sh. Vikramaditya Sen) | `AICTE-OFF-8841` | `Aicte#Scrutiny26` |
| **2. AICTE / Officer Portal** | Supervisor / Regional Director (Dr. S. Verma) | `AICTE-SUP-1024` | `Aicte#Scrutiny26` |

## 3. Two-Minute Live Demonstration Script (After Technical Approach Slide)

All steps use one consistent flagship sample application: **`NIR-2026-001` (`Demo Technical Institute, Lucknow` — B.Tech in Artificial Intelligence & Data Science, 120 Seats)**.

1. **Institution Portal (30 sec):**
   - Click **Proceed to Institution Login** → Click **Sign In to Institution Portal** (`INST-DTI-2026` / `Niriksh@2026`).
   - On the dashboard, view the summary metrics and click **View** on **`NIR-2026-001`** at the top of *My Applications*.
   - Show the 5-stage progress tracker (`Submitted → Documents Verified → Compliance Review → Inspection → Decision`) and click **Page 1 / Page 2 / Page 3** in the PDF viewer to show the submitted 3-page dossier.
2. **AICTE / Officer Portal — Compliance & Evidence (40 sec):**
   - Click **AICTE / Officer Portal** in the top bar → Click **Sign In to AICTE Officer Portal** (`AICTE-OFF-8841` / `Aicte#Scrutiny26`).
   - Click **View** on **`NIR-2026-001`** in the *Applications Requiring Attention* table (or click **Run Compliance Checks**).
   - Switch between **Findings (Combined Summary)**, **Rule Results (Deterministic Engine)**, and **AI Analysis (RAG Suggestions)** to show how deterministic rules and RAG operate in parallel.
   - Click **View Evidence** on the Page 2 Fire Safety NOC deficiency (`PROTOTYPE-RULE-DOC-01` & `RAG-SUG-01`) to display the exact extracted snippet and AICTE Approval Process Handbook 2024–27 citation.
3. **Clarification Request & Resubmission (30 sec):**
   - Click **Clarification / Decision Workflow →**, keep **Request Clarification** selected with the pre-filled Page 2 & Page 3 remarks, and click **Record Authorised Officer Decision**.
   - Switch back to **Institution Portal** → Open **Communications** (`Clarifications & Resubmission`) → Show the officer's official remarks (while internal officer notes remain hidden) and click **Resubmit Application & Re-Run Scrutiny**.
4. **EVC, Final Decision & Audit Trail (20 sec):**
   - Switch to **AICTE / Officer Portal** → See that `NIR-2026-001` is back in **Compliance Review** with the Page 2 deficiency resolved.
   - Open **EVC & Inspections** (optional) or **Clarification & Decision** to record **Approve**, and open **Audit Trail** to show every timestamped action.

## 4. Running Automated Tests

```powershell
cd niriksh\backend
python test_niriksh.py -v
```
