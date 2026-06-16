# Sydney

**AI-Powered Biomedical Variant Intelligence Platform**

Sydney is a lightweight web application that helps researchers, students, and clinicians understand genetic variants by aggregating evidence from ClinVar, PubMed, and biomedical literature. It generates structured reports with confidence scoring, AI summaries, and research gap analysis.

**Scope:** BRCA1, BRCA2, TP53 variants associated with breast and ovarian cancer.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Next.js 15 │────▶│  FastAPI     │────▶│  SQLite/     │
│  Frontend   │     │  Backend     │     │  PostgreSQL  │
│  :3000      │     │  :8000       │     │              │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  External    │
                    │  APIs        │
                    │              │
                    │  • ClinVar   │
                    │  • PubMed    │
                    │  • Groq      │
                    └──────────────┘
```

### Database Schema

```
genes ──┬── variants ──┬── evidence ──┬── papers
        │              │              │
        │              │              └── diseases
        │              │
        │              └── reports
        │
        └── gene_papers ──┐
                          ├── disease_papers
                          └── papers
```

---

## Features

### 1. Variant Search
Parse and normalize variant notation (HGVS c., protein change). Supports BRCA1, BRCA2, TP53.

### 2. ClinVar Integration
Retrieves clinical significance, review status, and disease associations with local caching.

### 3. PubMed Retrieval
Searches for relevant papers by gene, variant, and disease. Stores metadata locally. Limits to top relevant results.

### 4. Evidence Scoring
Each paper scored on a 0-100 scale using:
- **50%** Relevance score
- **30%** Study quality (e.g., Meta-Analysis=0.95, Case Report=0.35)
- **20%** Recency (newer papers score higher)

### 5. Confidence Engine
Aggregate confidence level based on:
- Evidence volume (number of papers)
- Evidence quality (average study quality)
- Study agreement (consistency across papers)

Outputs: **High**, **Moderate**, **Low**, or **Insufficient Evidence**

### 6. AI Research Summary
Generates structured summaries using Groq API (Llama 3.3 70B) with:
- Executive Summary
- Clinical Significance
- Disease Associations
- Mechanism of Action
- Evidence Overview
- Confidence Assessment

### 7. Knowledge Graph
Lightweight relationship visualization showing connections between genes, variants, papers, and diseases.

### 8. Research Gap Detection
Rule-based analysis identifying poorly studied variants, missing study types, and potential research areas.

### 9. PDF Report Export
Professional scientific report generation with ReportLab.

### 10. Dashboard
Overview of platform statistics and recent variant analyses.

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- 8GB RAM
- Dual-core CPU

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your Groq API key (optional, for AI summaries)
export GROQ_API_KEY=gsk_your_key_here

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Docker Setup

```bash
docker compose up --build
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/dashboard` | GET | Dashboard statistics |
| `/api/v1/variants/search` | POST | Search and analyze a variant |
| `/api/v1/variants` | GET | List all variants |
| `/api/v1/variants/{id}` | GET | Variant detail with evidence |
| `/api/v1/variants/{id}/evidence` | GET | Evidence list with scores |
| `/api/v1/variants/{id}/report` | GET | Confidence report |
| `/api/v1/variants/{id}/summary` | POST | Generate AI summary |
| `/api/v1/variants/{id}/gaps` | GET | Research gap analysis |
| `/api/v1/variants/{id}/report/pdf` | GET | Download PDF report |
| `/api/v1/graph/{id}` | GET | Knowledge graph data |

Full OpenAPI docs at http://localhost:8000/docs

---

## Variant Format Examples

```
BRCA1 c.5266dupC
BRCA2 c.5946delT
TP53 R175H
TP53 p.R175H
BRCA1 185delAG
P53 R273H
```

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/sydney.db` | Database connection string |
| `GROQ_API_KEY` | `` | Groq API key for AI summaries |
| `DEBUG` | `true` | Enable debug mode |

### Frontend (`frontend/.env.local`)
| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

---

## Testing

```bash
# Backend tests
cd backend
pytest ../tests/backend -v

# With coverage
pytest ../tests/backend -v --cov=app
```

---

## Development Guide

### Project Structure

```
sydney/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/config.py       # Configuration
│   │   ├── models/database.py   # SQLAlchemy models
│   │   ├── models/schemas.py    # Pydantic schemas
│   │   ├── api/routes.py        # API routes
│   │   ├── services/
│   │   │   ├── variant_service.py    # Variant parsing & analysis
│   │   │   ├── clinvar_service.py    # ClinVar API integration
│   │   │   ├── pubmed_service.py     # PubMed API integration
│   │   │   ├── evidence_scoring.py   # Evidence scoring engine
│   │   │   ├── confidence_engine.py  # Confidence calculation
│   │   │   ├── ai_summary.py         # Groq AI summary
│   │   │   ├── research_gaps.py      # Gap detection
│   │   │   └── report_generator.py   # PDF generation
│   │   └── db/migrations.py     # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Home search page
│   │   │   ├── dashboard/       # Dashboard page
│   │   │   ├── variants/        # Variants list & detail
│   │   │   └── providers.tsx    # React Query provider
│   │   ├── components/
│   │   │   ├── ui/              # Reusable UI components
│   │   │   ├── variant/         # Variant-specific components
│   │   │   └── layout/          # Layout components
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── hooks.ts         # React Query hooks
│   │   │   └── utils.ts         # Utility functions
│   │   └── types/index.ts       # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

### Adding a New Gene

1. Add gene to `GENE_ALIASES` in `backend/app/services/variant_service.py`
2. Add gene metadata in `get_or_create_gene` method
3. Add to frontend validation regex in `frontend/src/app/page.tsx`
4. That's it — the architecture supports extending the gene list

---

## Resource Usage

- **RAM:** ~200MB (backend) + ~150MB (frontend) = ~350MB total
- **CPU:** Minimal usage during idle; spikes during PubMed/ClinVar API calls
- **Storage:** ~50MB for SQLite database and API caches
- **Network:** Only external calls to ClinVar, PubMed, and Groq APIs

---

## License

MIT
