<img width="1404" height="789" alt="Screenshot 2026-07-24 at 1 52 27 AM" src="https://github.com/user-attachments/assets/7c8cb62a-24e5-4ae0-9a6e-e2483df9c7a2" />
<img width="1360" height="707" alt="Screenshot 2026-07-24 at 1 52 32 AM" src="https://github.com/user-attachments/assets/f6ab7ab7-a227-4c07-bd4a-38d93f91678d" />
# QualiSphere — AI Customer Complaint QMS

QualiSphere is a full-stack demonstration application for recording and assessing pharmaceutical customer complaints across API and finished dosage form (FDF) operations. It combines a React/Redux interface with a FastAPI service, LangGraph workflow, and SQL persistence.

> **Important:** This repository is a software demonstration and learning project. It is not a validated GxP system and must not be used to release product, close complaints, approve CAPAs, or make regulatory reporting decisions.

## What it does

- Captures customer, product, batch, quantity, complaint, severity, and priority data.
- Provides a guided AI-style intake experience from pasted complaint text or a test-document upload.
- Runs complaint completeness, initial risk, duplicate likelihood, root-cause, CAPA, and summary recommendations through a LangGraph workflow.
- Saves complaint records to SQL. SQLite is used locally by default; PostgreSQL is included for Docker deployment.
- Includes a fictional DOCX complaint fixture for a repeatable UI test.

## Technology

| Area | Choice |
| --- | --- |
| Frontend | React 18, Redux Toolkit, Vite, Inter |
| API | Python 3.12, FastAPI, Pydantic |
| Agent workflow | LangGraph |
| Persistence | SQLAlchemy; SQLite local fallback / PostgreSQL for deployment |
| AI provider | Groq integration ready; deterministic safe-demo fallback enabled |
| Deployment | Docker, Nginx, Docker Compose, PostgreSQL 16 |

## Repository layout

```text
.
├── src/                    # React + Redux application
├── backend/                # FastAPI API, LangGraph workflow, SQL model
├── fixtures/               # Fictional complaint documents for testing
├── tools/                  # Fixture generator utilities
├── compose.yml             # Web + API + PostgreSQL deployment stack
├── Dockerfile              # Production web image
├── nginx.conf              # SPA delivery and API reverse proxy
├── .env.example            # Frontend environment template
└── README.md
```

## Quick start — local development

### 1. Prerequisites

- Node.js 20 or newer
- Python 3.12 or newer

### 2. Start the API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API starts with a local `qualisphere.db` SQLite database in the working directory. API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Start the frontend

Open another terminal at the repository root:

```bash
npm install
cp .env.example .env
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` calls to FastAPI by default. For a direct API connection, leave `VITE_API_BASE_URL=http://127.0.0.1:8000/api` in `.env`.

### 4. Test an end-to-end complaint

1. Open the running application.
2. Click **browse files** in **AI Complaint Intake**.
3. Select `fixtures/Customer_Complaint_Metformin_MTF240821.docx`.
4. Confirm the extracted fields and AI assessment cards.
5. Click **Save complaint**. A complaint number is created and stored in the local database.

## Production-style Docker deployment

Docker Compose starts PostgreSQL, FastAPI, and a static Nginx-served React build.

```bash
docker compose up --build
```

Open `http://localhost:8080`. Before any non-local deployment, change the database password in `compose.yml`, place secrets in a secret manager, restrict CORS origins, and use TLS at the ingress layer.

To stop the stack:

```bash
docker compose down
```

To also remove the local PostgreSQL data volume:

```bash
docker compose down -v
```

## Environment variables

### Frontend

| Variable | Purpose | Example |
| --- | --- | --- |
| `VITE_API_BASE_URL` | API URL exposed to the browser | `http://127.0.0.1:8000/api` |

### Backend

Copy `backend/.env.example` into your deployment environment.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Use PostgreSQL in shared environments. |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API. |
| `GROQ_API_KEY` | Groq credential; never commit it. |

Example PostgreSQL URL:

```text
postgresql+psycopg://qualisphere:strong-password@db-host:5432/qualisphere
```

## AI workflow and Groq

The default `quality_assessment` LangGraph node deliberately uses deterministic rule-based output. This makes the repository safe to run without a network key and keeps fictional test data local.

To use Groq in an approved environment:

1. Create a Groq key and set `GROQ_API_KEY` outside source control.
2. In `backend/main.py`, replace `rule_analysis` within the `quality_assessment` node with a `langchain_groq.ChatGroq` structured-output call.
3. Use `gemma2-9b-it` for routine classification/extraction and `llama-3.3-70b-versatile` only where the additional context quality is justified.
4. Store model name, prompt version, input hash, output, reviewer, and approval event in the audit trail.

Do not allow an LLM to autonomously classify final patient/product risk, approve a CAPA, close a complaint, or determine reportability.

## QMS and data-model notes

The Customer Complaint module is a controlled feedback point in the pharmaceutical quality system. A real implementation should link the complaint to batch records, deviations, laboratory results, supplier records, investigations, CAPAs, change controls, periodic product quality review, and management review.

The included table is intentionally small for a running demo. Before using the system in a regulated environment, implement at least:

- Role-based access control and SSO.
- Validated electronic records, immutable audit trail, and compliant electronic signatures.
- Database migrations (Alembic), backups, encryption, retention, and disaster recovery.
- Malware scanning and controlled object storage for attachments.
- Real document parsing/OCR with confidence scores and field-level human verification.
- Duplicate search using approved embeddings or full-text search with explainable similarity evidence.
- A governed taxonomy for products, sites, customers, batches, complaint types, risks, and CAPA categories.
- Automated tests, monitoring, rate limits, structured logs, error tracking, vulnerability scans, and CI/CD approvals.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Service liveness check |
| `POST` | `/api/complaints/analyze` | Returns LangGraph assessment recommendations |
| `POST` | `/api/complaints` | Validates and persists a complaint record |
| `GET` | `/docs` | Interactive OpenAPI documentation |

## GitHub upload checklist

```bash
git init
git add .
git commit -m "Initial QualiSphere complaint QMS prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USER/qualisphere-qms.git
git push -u origin main
```

Before pushing, confirm that `.env`, `.venv`, `node_modules`, database files, logs, and real complaint data are excluded. The included `.gitignore` is configured for this repository.




