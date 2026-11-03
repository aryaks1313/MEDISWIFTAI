# MediSwift AI

MediSwift AI is a medicine-ordering demo with customer accounts, a searchable medicine catalogue, prescription uploads, pharmacist review, and delivery-order workflows. The backend is a FastAPI application backed by PostgreSQL; the frontend is a small HTML/CSS/JavaScript client.

> **Demo software only.** This project is not a medical device or a substitute for professional advice. Prescription matching is a draft for pharmacist review; it does not diagnose, prescribe, approve prescriptions, or authorize substitutions. Do not use it to make clinical decisions or process real patient data.

## Features

- Register and sign in as a customer, pharmacy owner, or delivery person.
- Browse and search active medicines; pharmacy owners can manage the catalogue through the API.
- Upload JPG, PNG, WEBP, or PDF prescriptions for pharmacist review.
- Submit extracted prescription text to the optional AI-assisted matching endpoint. OCR is not implemented; text must be supplied separately.
- Require pharmacist approval before ordering medicines marked as prescription-only.
- Place and track orders, assign delivery people, and progress orders through role-based status transitions.
- Explore and try the API at FastAPI's interactive documentation page.

## Requirements

- Python 3.10 or newer
- PostgreSQL
- pip
- An OpenAI API key only if you want to enable the optional CrewAI analysis

## Setup

### 1. Create a PostgreSQL database

Create a database for the application, for example:

```sql
CREATE DATABASE mediswift;
```

### 2. Configure environment variables

Create a `.env` file in the project root (next to `requirements.txt`):

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:your-password@localhost:5432/mediswift
JWT_SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
# Optional: enables CrewAI-assisted analysis; without it, analysis returns
# catalogue candidates for pharmacist review without calling an AI provider.
OPENAI_API_KEY=
# Optional; defaults to uploads/prescriptions
# UPLOAD_DIR=uploads/prescriptions
```

Use your own database credentials and a strong, private JWT secret. Keep `.env` out of source control; this repository's `.gitignore` excludes environment files.

### 3. Install dependencies

From the project root, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, you can invoke the environment's Python directly as `.\.venv\Scripts\python.exe`.

### 4. Start the API

From the project root, run:

```powershell
python -m uvicorn backend.main:app --reload
```

The API listens at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/api/health` for service status and open `http://127.0.0.1:8000/docs` for interactive API documentation.

On startup, the application creates missing database tables. To add the sample medicines and development accounts, open another terminal in the project root and run:

```powershell
python -m backend.seed
```

The seed script creates these **development-only** accounts when they do not already exist:

| Role | Email | Password |
|---|---|---|
| Customer | `customer@mediswift.demo` | `Customer@123` |
| Pharmacy owner | `pharmacist@mediswift.demo` | `Pharmacist@123` |
| Delivery person | `delivery@mediswift.demo` | `Delivery@123` |

Do not use these credentials outside a local demo.

### 5. Open the frontend

In another terminal, serve the frontend directory:

```powershell
python -m http.server 5500 --directory frontend
```

Then open `http://127.0.0.1:5500/`. The frontend currently targets the API at `http://127.0.0.1:8000/api`; run it locally alongside the backend.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/register` | Register a customer, pharmacy owner, or delivery person |
| `POST` | `/api/auth/login` | Sign in and receive a bearer token |
| `GET` | `/api/auth/me` | Get the current account |
| `GET` | `/api/medicines` | List/search the active medicine catalogue |
| `POST`, `PUT`, `DELETE` | `/api/medicines` | Create, update, or deactivate catalogue entries (pharmacy owner) |
| `POST` | `/api/prescriptions/upload` | Upload a prescription (customer) |
| `POST` | `/api/prescriptions/{id}/analyze` | Analyze supplied OCR text and return review candidates |
| `GET` | `/api/prescriptions` | List prescriptions for pharmacist review (pharmacy owner) |
| `POST` | `/api/prescriptions/{id}/review` | Approve, reject, or request clarification (pharmacy owner) |
| `POST`, `GET` | `/api/orders` | Place an order or list orders visible to the current role |
| `POST` | `/api/orders/{id}/assign-delivery` | Assign a delivery person (pharmacy owner) |
| `PATCH` | `/api/orders/{id}/status` | Advance an order through permitted status transitions |

Use `/docs` for request schemas, authorization requirements, and response details.

## Project layout

```text
backend/
  agents/       CrewAI workflow
  ai/           Prescription analysis agent
  services/     Medicine matching and order services
  main.py       FastAPI application and API routes
  database.py   SQLAlchemy/PostgreSQL connection
  models.py     Database models
  seed.py       Development sample accounts and medicines
frontend/
  index.html    Main demo page
  css/          Styles
  js/           Browser API client
uploads/
  prescriptions/ Uploaded files (created at runtime; not tracked)
medi.ipynb      Project notebook
requirements.txt
```

## Development notes

- `python -m backend.test_db` checks the configured database connection.
- Prescription image OCR is not implemented. The analyze endpoint accepts extracted text as form data.
- CrewAI analysis requires a provider configuration such as `OPENAI_API_KEY`; without it, the API returns catalogue candidates and still requires pharmacist review.
- Before any deployment, configure restrictive CORS origins, a strong JWT secret, secure database credentials, private prescription-file storage, and appropriate access controls. The current app is a local demo, not a production-ready patient-data service.
