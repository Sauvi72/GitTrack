# OpenTrack — GitHub Student Contribution Tracker

**OpenTrack** is a production-grade web application designed for teachers, professors, and open-source mentors to monitor student pull requests (PRs) across GitHub.

It provides continuous tracking of open-source contributions, outcome classifications (Merged vs. Open vs. Closed Unmerged), real-time analytics, and CSV reporting across both global public GitHub activity and targeted classroom/course scopes.

---

## 1. Architecture & Design

```
Teacher (Browser)
       │
       ▼
React + Vite Frontend (TypeScript + Tailwind CSS + Recharts)
       │
       ▼  (REST API / JWT Session Bearer)
FastAPI Backend (Python 3)
  ├── Teacher Authentication & Session Security (Argon2 + JWT)
  ├── Student Management Service (Account validation with GitHub REST)
  ├── Scope Management (Global public, Organizations, Repositories)
  ├── GitHub API Client (HTTPX, Rate-limit detection, Exponential backoff)
  ├── PR Discovery Engine (Search API qualifiers, Pagination, Date-range partitioning)
  ├── PR Processor & Deduplication (GitHub Node ID, Repo + PR# fallback)
  ├── Data Synchronization Engine (Idempotent worker, In-flight concurrency locks)
  └── Analytics & Reporting Engine (Real database aggregation, CSV export)
       │
       ▼  (SQLAlchemy 2.x + Alembic Migrations)
SQLite Database (PostgreSQL-compatible schema)
```

### Key Technical Characteristics:
- **Authorship Attribution**: Tracks PRs **authored** by students (using qualifier `is:pr author:USERNAME`). A student gets full credit for authoring a PR regardless of who reviews or merges it.
- **Strict Outcome Classification**:
  - `MERGED`: Verified `merged_at IS NOT NULL` from detailed GitHub PR endpoint.
  - `OPEN`: Current GitHub state is `"open"`.
  - `CLOSED_UNMERGED`: GitHub state is `"closed"` without merge timestamp.
  *(A closed PR is never assumed to be merged).*
- **Dual Tracking Modes**:
  - **Mode A (Global Public)**: Discovers student activity across all open-source repositories.
  - **Mode B (Selected Scopes)**: Filters or tracks specific GitHub Organizations or individual repositories.
  - Results are merged and deduplicated using GitHub's immutable `node_id` and unique `(repository_full_name, pr_number)` constraints.
- **GitHub API Defense**:
  - Handles 1,000-result search ceilings using automatic date-range partitioning (`created:YYYY-MM-DD..YYYY-MM-DD`).
  - Transparent coverage reporting: Flags incomplete or rate-limited scans with warnings instead of pretending scans are complete.
  - Thread-safe synchronization locks prevent overlapping sync jobs on the same student.
  - Full idempotency: Repeated sync runs refresh existing PR states without creating duplicate database rows.

---

## 2. Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, HTTPX, Pytest, PyJWT, Pwdlib (Argon2).
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Vitest, React Testing Library.
- **Database**: SQLite for development (fully compatible with PostgreSQL for production via SQLAlchemy dialect abstraction).

---

## 3. Project Structure

```
gitcrawl/
├── backend/
│   ├── alembic/              # Database migration environments & revisions
│   ├── app/
│   │   ├── api/              # REST API endpoints (auth, students, scopes, prs, dashboard, sync, reports)
│   │   ├── core/             # Configuration settings (pydantic-settings) & security (JWT, Argon2)
│   │   ├── database/         # SQLAlchemy engine and session providers
│   │   ├── models/           # SQLAlchemy 2.0 ORM models (Teacher, Student, PullRequest, Scope, SyncLog)
│   │   ├── schemas/          # Pydantic v2 validation and response models
│   │   ├── services/         # GitHubClient, DiscoveryEngine, PRProcessor, SyncService, AnalyticsService
│   │   └── main.py           # FastAPI entrypoint, middleware, lifespan data seeding
│   ├── tests/                # Comprehensive unit, integration, and E2E test suite
│   ├── pytest.ini            # Pytest configuration
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/       # MetricCard, StatusBadge, Header, Sidebar, AddStudentModal
│   │   ├── pages/            # Overview, Students, StudentDetail, PullRequests, Scopes, Reports, Login
│   │   ├── services/         # Typed API client connecting to FastAPI backend
│   │   ├── types/            # TypeScript interfaces
│   │   ├── App.tsx           # Main application routing and state
│   │   └── main.tsx          # React DOM entrypoint
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts        # Vite configuration with /api proxy to FastAPI
│   └── tailwind.config.js
├── .env.example              # Environment variables template
├── .gitignore
└── README.md
```

---

## 4. Getting Started Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ and npm

### Step 1: Environment Setup
Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` if you have a GitHub Personal Access Token (PAT). While unauthenticated GitHub requests work with lower rate limits (60 requests/hr), adding a GitHub PAT increases limits to 5,000 requests/hr:
```ini
GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
```

### Step 2: Backend Installation & Migrations
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://127.0.0.1:8000`.
Interactive Swagger API documentation: `http://127.0.0.1:8000/docs`.

### Step 3: Frontend Installation & Launch
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

## 5. Teacher Authentication & Initial Access

On initial startup, OpenTrack seeds a default teacher administrator:
- **Email**: `teacher@opentrack.edu`
- **Password**: `OpenTrack2026!`

*(You can change these in `.env` before initial startup or modify them via the user management API).*

---

## 6. Running Tests

### Backend Tests
Execute the full Pytest test suite (20 automated tests covering unit logic, rate limit handling, idempotency, models, and end-to-end flows):
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Frontend Tests & Typecheck
Execute Vitest and the production TypeScript build check:
```bash
cd frontend
npm test
npm run build
```

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service and database health check |
| `POST` | `/api/auth/login` | Authenticate teacher and issue JWT / session cookie |
| `POST` | `/api/auth/logout` | Clear teacher session |
| `GET` | `/api/auth/me` | Current teacher profile |
| `GET` | `/api/students` | List students with calculated PR counts and merge ratio |
| `POST` | `/api/students` | Validate GitHub account and register student |
| `GET` | `/api/students/{id}` | Student profile and computed metrics |
| `PATCH` | `/api/students/{id}` | Update student details or active status |
| `DELETE` | `/api/students/{id}` | Archive or delete student |
| `GET` | `/api/students/{id}/statistics` | Repository breakdown, org breakdown, additions/deletions |
| `GET` | `/api/scopes` | List tracking scopes (Global, Organization, Repository) |
| `POST` | `/api/scopes` | Add an Organization or Repository scope |
| `PATCH` | `/api/scopes/{id}` | Enable or disable scope |
| `DELETE` | `/api/scopes/{id}` | Remove scope |
| `POST` | `/api/students/{id}/sync` | Trigger discovery and detailed PR ingestion |
| `POST` | `/api/sync-all` | Bulk sync for all active students |
| `GET` | `/api/sync-logs` | Audit logs of sync runs with status and counts |
| `GET` | `/api/sync-status` | In-flight synchronization status |
| `GET` | `/api/pull-requests` | Filterable, paginated PR search across class |
| `GET` | `/api/dashboard/summary` | Class-wide summary metrics with date bounds |
| `GET` | `/api/dashboard/leaderboard` | Top students ranked by merged PRs or total PRs |
| `GET` | `/api/dashboard/activity` | Daily PR creation/merge timeline and top repos/orgs |
| `GET` | `/api/reports/csv` | Download real contribution records as a CSV file |

---

## 8. GitHub API Limitations & Mitigation Strategy

1. **GitHub Search Result Ceiling (1,000 Results Max)**:
   - GitHub's `/search/issues` returns a maximum of 1,000 results per query.
   - *Mitigation*: OpenTrack implements date-range partitioning (`PRDiscoveryEngine`) when result counts exceed 1,000, subdividing searches into temporal intervals to retrieve full history.
   - If a partition reports `incomplete_results`, OpenTrack records `is_complete=False` and surfaces a warning to the teacher.
2. **Search Rate Limits**:
   - The Search API has dedicated rate limits (30 requests/min for authenticated tokens, 10 requests/min unauthenticated).
   - *Mitigation*: OpenTrack's `GitHubClient` intercepts `x-ratelimit-remaining` and `x-ratelimit-reset` headers, pausing and backing off exponentially.
3. **Private Repositories**:
   - Global public search can only discover public repositories. If students contribute to private organization repositories, the teacher must supply a GitHub token with appropriate read permissions for that organization.

---

## 9. License

OpenTrack is distributed under the MIT License.
