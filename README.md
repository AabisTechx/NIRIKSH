# NIRIKSH — AICTE Approval Workflow Automation

**Smart India Hackathon 2026 | SIH26262 | Team CodeRanger**

## 🚀 Live Demo

**🌐 Live Application:** https://niriksh-frontend.vercel.app

**⚙️ Backend API:** https://niriksh-suta.onrender.com

**📘 API Documentation:** https://niriksh-suta.onrender.com/docs

**💻 GitHub Repository:** https://github.com/AabisTechx/NIRIKSH

---

## 📌 Project Overview

NIRIKSH is an AI-assisted platform designed to streamline the AICTE institutional approval process through document processing, compliance verification, application tracking and officer review.

The platform provides a centralised digital workflow connecting institutions and regulatory officers. It helps organise application scrutiny, identify missing information, track compliance findings and manage clarification requests.

NIRIKSH combines rule-based verification with AI-assisted document analysis to support transparent and traceable scrutiny.

**Final approval or rejection remains the responsibility of authorised officers.**

---

## 🎯 Problem Statement

**Problem Statement ID:** SIH26262

**Title:** Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System.

The AICTE approval process involves multiple stages of application scrutiny, document verification, compliance monitoring, inspections and communication between institutions and regulatory authorities.

A unified digital platform is required to improve workflow management, application tracking, compliance monitoring, deadline management and transparency.

---

## 💡 Proposed Solution

NIRIKSH provides a unified platform with two primary portals.

### 1. Institution Portal

- Institution dashboard.
- Application submission and tracking.
- Supporting document submission.
- PDF document viewing.
- Application status monitoring.
- Clarification requests and resubmission.
- Application communication tracking.

### 2. AICTE / Officer Portal

- Application overview and scrutiny dashboard.
- Document review and verification.
- Compliance findings and supporting evidence.
- Rule-based compliance checks.
- AI-assisted document analysis.
- Clarification requests to institutions.
- Application decision management.
- EVC and inspection workflow support.
- Audit trail and application history.

---

## ⚙️ Key Features

| Feature | Description |
|---|---|
| Two-Portal Architecture | Separate Institution and Officer interfaces |
| Application Management | Application submission, tracking and review |
| PDF Processing | Document extraction and page-level references |
| Compliance Verification | Rule-based compliance checks |
| AI-Assisted Analysis | RAG-oriented document analysis |
| Evidence Traceability | Findings linked to supporting documents |
| Clarification Workflow | Requests, corrections and resubmission |
| EVC Management | Inspection-related workflow support |
| Supervisor Overview | Application monitoring and oversight |
| Audit Trail | Records of application activities |

---

## 🔄 System Workflow

1. Institution submits an application and supporting documents.
2. Documents are processed to extract relevant information.
3. The compliance engine checks selected requirements.
4. AI-assisted analysis generates additional findings and suggestions.
5. Officers review the findings and supporting evidence.
6. Officers can request clarification.
7. Institutions submit revised information.
8. Authorised officers record the final decision.
9. Application activities are maintained through an audit trail.

---

## 🏗️ Technical Architecture

```text
             Institution Portal
                     |
                     v
              FastAPI Backend
                     |
          +----------+----------+
          |                     |
          v                     v
   PDF Processing       Application Management
          |                     |
          v                     |
   Extracted Information       |
          |                     |
     +----+----+                |
     |         |                |
     v         v                |
 Rule Engine  AI-Assisted       |
     |        Analysis          |
     |         |                |
     +----+----+                |
          |                     |
          v                     |
    Findings & Evidence         |
          |                     |
          v                     |
      Officer Portal <----------+
          |
          v
 Clarification / Decision
          |
          v
       Audit Trail
```

---

## 🧰 Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Tailwind CSS

### Backend
- Python
- FastAPI
- Pydantic
- Uvicorn

### Document Processing
- PyMuPDF
- PDF text extraction
- Page-level document references

### AI & Compliance
- Rule-based verification
- AI-assisted document analysis
- Retrieval-Augmented Generation (RAG)-oriented processing

### Database
- SQLite
- SQLAlchemy

### Deployment
- Vercel — Frontend
- Render — Backend API
- GitHub — Source Code

---

## 🔐 Demonstration Access

The application provides demonstration accounts for testing the portals.

| Portal | Username | Password |
|---|---|---|
| Institution | `INST-DTI-2026` | `Niriksh@2026` |
| Officer | `AICTE-OFF-8841` | `Aicte#Scrutiny26` |

**Note:** These are demonstration credentials for synthetic sample data only. They are not real institutional or government accounts.

---

## 🖥️ Run Locally

### Prerequisites

- Python 3.9 or later
- Git
- Modern web browser

### 1. Clone Repository

```bash
git clone https://github.com/AabisTechx/NIRIKSH.git
cd NIRIKSH
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start Backend Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Open Application

```text
http://127.0.0.1:8000
```

API Documentation:

```text
http://127.0.0.1:8000/docs
```

### Windows Launcher

You can also run the included Windows launcher:

```text
START_NIRIKSH_WINDOWS.bat
```

---

## 📁 Repository Structure

```text
NIRIKSH/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   ├── services/
│   ├── sample_data/
│   ├── scripts/
│   └── test_niriksh.py
│
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   └── config.js
│   └── package.json
│
├── generate_sample_pdf.py
├── START_NIRIKSH_WINDOWS.bat
├── DEPLOYMENT_GUIDE.md
├── .env.example
├── .gitignore
└── README.md
```

---

## 🌐 Deployment

NIRIKSH uses separate frontend and backend deployments.

| Component | Platform | Deployment |
|---|---|---|
| Frontend | Vercel | Live |
| Backend | Render | Live |
| API Documentation | Render | Live |
| Source Code | GitHub | Public Repository |

The frontend communicates with the FastAPI backend through the deployed API URL configured in `frontend/public/config.js`.

---

## 🔮 Future Scope

- Configurable approval-stage routing.
- Region-wise pendency and workload dashboards.
- Time-bound undertaking tracking.
- Lease and document expiry monitoring.
- Automated reminders and escalation mechanisms.
- Secure persistent document storage.
- Integration with authorised AICTE and government systems.
- Enhanced role-based access control.
- Compliance rule versioning and validation.

---

## ⚠️ Prototype Limitations

NIRIKSH is a Smart India Hackathon 2026 prototype.

- The current implementation uses synthetic demonstration data.
- AI-assisted analysis supports, but does not replace, authorised officer scrutiny.
- The deployed demonstration uses SQLite; persistent database and document storage are not guaranteed.
- Production integration with official AICTE and government systems is not claimed.
- Production deployment would require security audits, persistent storage, operational monitoring and regulatory validation.

Features described under Future Scope are proposed enhancements, not claims of completed implementation.

---

## 👥 Team Information

**Team Name:** CodeRanger  
**Competition:** Smart India Hackathon 2026  
**Problem Statement ID:** SIH26262

**Project Name:** NIRIKSH

---

## 📄 Disclaimer

NIRIKSH is an independent prototype developed for Smart India Hackathon 2026. It is not an official AICTE application or government service and is not affiliated with or endorsed by AICTE or the Ministry of Education.

All demonstration records are synthetic. Final regulatory decisions must remain with the competent authorities.

---

<p align="center">
  <strong>NIRIKSH — Making Institutional Approval Workflows More Transparent, Traceable and Accountable.</strong>
</p>
