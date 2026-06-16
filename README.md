# **S**ydney — **S**ystematic **Y**ielding of **D**isease-associated Ge**n**omic **E**vidence and Discover**Y**

**AI-Powered Biomedical Variant Intelligence Platform**

Sydney is a lightweight web application that helps researchers, students, and clinicians understand genetic variants by aggregating evidence from ClinVar, PubMed, and biomedical literature. It generates structured reports with confidence scoring, AI summaries, and research gap analysis — without hallucinating results.

**Supported genes (8):** BRCA1, BRCA2, TP53, CDH1, PALB2, CHEK2, ATM, PTEN — covering breast, ovarian, gastric, and related hereditary cancer syndromes.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Data Pipeline (End to End)](#data-pipeline-end-to-end)
- [Database Schema](#database-schema)
- [Features](#features)
- [API Reference](#api-reference)
- [Services Deep Dive](#services-deep-dive)
- [Quick Start](#quick-start)
- [Variant Format Reference](#variant-format-reference)
- [Testing Guide](#testing-guide)
- [Project Structure](#project-structure)
- [Adding New Genes](#adding-new-genes)
- [Environment Variables](#environment-variables)
- [Resource Usage](#resource-usage)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Next.js 15 App Router                                      │ │
│  │  • React 19 + TypeScript                                    │ │
│  │  • Tailwind CSS + Dark Mode                                 │ │
│  │  • React Query (caching, refetch)                           │ │
│  │  • Recharts (evidence charts)                               │ │
│  │  • SVG graph (knowledge relationships)                      │ │
│  └──────────────────────┬──────────────────────────────────────┘ │
└─────────────────────────┼────────────────────────────────────────┘
                          │ HTTP (localhost:3000 → localhost:8000)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                                │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │ API Routes   │───▶│ Services     │───▶│ Database           │  │
│  │ (routes.py)  │    │ (8 services) │    │ (SQLAlchemy/SQLite)│  │
│  └──────┬───────┘    └──────┬───────┘    └────────────────────┘  │
│         │                   │                                     │
│         │                   ├── ClinVar Service ──▶ NCBI E-utilities
│         │                   ├── PubMed Service  ──▶ NCBI E-utilities
│         │                   ├── AI Summary      ──▶ Groq API
│         │                   └── PDF Generator   ──▶ ReportLab
│         ▼
│  OpenAPI: /docs
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 15, TypeScript, Tailwind, React Query | Search UI, evidence dashboard, knowledge graph, PDF download |
| **Backend API** | FastAPI, Pydantic | REST endpoints, input validation, OpenAPI docs |
| **Business Logic** | Python services | Variant parsing, evidence scoring, confidence calculation |
| **Database** | SQLite (dev) / PostgreSQL (prod), SQLAlchemy | Variants, papers, evidence, reports |
| **External APIs** | NCBI E-utilities, Groq | ClinVar queries, PubMed search, AI summary generation |

---

## Data Pipeline (End to End)

When a user searches for a variant (e.g., `TP53 R175H`), the following pipeline executes:

### Step 1: Input Validation (VariantAnalysisService.parse_variant)
```
User Input: "TP53 R175H"
  ↓
Regex matching against 8 supported genes and 6 notation patterns:
  • c. notation:   BRCA1 c.5266dupC, CDH1 c.1901C>T
  • p. notation:   TP53 p.R175H
  • 1-letter code: TP53 R175H
  • 3-letter code: TP53 Arg175His
  • Legacy:        BRCA1 185delAG
  • Alias:         P53 R175H → TP53
  ↓
If no match → 400 error with helpful message
If match → { gene: "TP53", change: "R175H" }
```

### Step 2: Gene Resolution
```
Gene symbol "TP53" (or CDH1, PALB2, CHEK2, ATM, PTEN, BRCA1, BRCA2)
  ↓
Query genes table → if not found, create with metadata:
  • symbol, full_name, chromosome, description
```

### Step 3: Variant Lookup/Creation
```
gene + change
  ↓
Query variants table by HGVS c. or protein change
  ↓
If not found → Create variant record:
  • gene_id, hgvs_c, protein_change, variant_type
```

### Step 4: ClinVar Retrieval (ClinVarService)
```
gene + variant
  ↓
1. Check local disk cache (data/cache/clinvar/)
   ↓ if cache miss:
2. ESearch: NCBI E-utilities → get ClinVar ID
   • Query: "TP53[gene] AND R175H[variant] OR R175H[All Fields]"
   • Fallback: "TP53 R175H"
3. EFetch: rettype=vcv, retmode=xml
   • VCV accession (zero-padded to 9 digits): VCV000012374
4. Parse VCV XML for:
   • <GermlineClassification> → <Description> → "Pathogenic"
   • <ReviewStatus> → "reviewed by expert panel"
   • <VariationArchive VariationName="...">
   • <TraitSet> → disease names
5. Cache result as JSON
   ↓
Update variant record:
  • clinical_significance, clinvar_id, review_status, clinvar_data
```

### Step 5: PubMed Retrieval (PubMedService)
```
gene + variant + disease ("breast cancer")
  ↓
1. Check local disk cache (data/cache/pubmed/)
   ↓ if cache miss:
2. ESearch: "(TP53[Title/Abstract]) AND (R175H[Text Word]) AND (breast cancer[MeSH])"
   • Limit: 20 results, sorted by relevance
3. EFetch: Get XML with titles, authors, abstracts
4. Infer study type from abstract + keywords:
   • "clinical trial" → Clinical Trial (0.90)
   • "meta-analysis" → Meta-Analysis (0.95)
   • "case report" → Case Report (0.35)
   • Default → Research Article (0.50)
5. Cache results as JSON
   ↓
For each paper (all 8 genes share the same pipeline — no gene-specific logic needed beyond the symbol):
  • Create Paper record (pmid, title, authors, journal, year, abstract, study_type)
  • Create Evidence record (variant_id, paper_id, evidence_type="literature")
```

### Step 6: Evidence Scoring (EvidenceScoringService)
```
For each evidence item:
  ↓
relevance = keyword overlap between paper and variant (0.5 - 1.0)
study_quality = STUDY_QUALITY_MAP[paper.study_type]
  • Meta-Analysis: 0.95
  • Clinical Trial: 0.90
  • Cohort Study:   0.75
  • Case Report:    0.35
recency = max(0, 1.0 - (current_year - paper_year) * 0.05)
  ↓
evidence_score = (0.50 × relevance) + (0.30 × study_quality) + (0.20 × recency)
  ↓
Score range: 0.0 - 1.0 (displayed as 0-100)
```

### Step 7: Confidence Calculation (ConfidenceEngine)
```
All evidence items for variant
  ↓
evidence_volume = count of papers
  • 0 papers → 0.0
  • 1-2 papers → 0.2
  • 3-4 papers → 0.4
  • 5-9 papers → 0.6
  • 10-19 papers → 0.8
  • 20+ papers → 1.0
  ↓
evidence_quality = average study_quality_score across all papers
  ↓
study_agreement = consistency of clinical_significance across papers
  ↓
confidence_score = (0.30 × volume) + (0.40 × quality) + (0.30 × agreement)
  ↓
Level mapping:
  score >= 0.70 → High
  score >= 0.40 → Moderate
  score < 0.40 → Low
  score == 0   → Insufficient Evidence
```

### Step 8: Report Generation
```
variant + evidence + confidence
  ↓
Create Report record with all scores and metadata
  ↓
PDF generation (on demand):
  • ReportLab → professional scientific PDF
  • Sections: Executive Summary, Clinical Significance,
    Evidence Overview, Supporting Studies, Disease Associations,
    Confidence Assessment
```

### Step 9: AI Summary (optional, requires Groq API key)
```
variant + evidence + confidence
  ↓
Build context string with all paper titles, PMIDs, scores, findings
  ↓
Groq API call: Llama 3.3 70B
  • System prompt: evidence-based, no hallucinations, cite PMIDs
  • Temperature: 0.3 (low creativity, high accuracy)
  • Generates sections: Executive Summary, Clinical Significance,
    Disease Associations, Mechanism of Action, Evidence Overview,
    Confidence Assessment
```

### Step 10: Research Gap Detection (ResearchGapDetector)
```
Analyze evidence distribution
  ↓
Rule-based checks:
  • No clinical trials found?
  • No functional studies?
  • Fewer than 3 high-quality papers?
  • Total papers < 5?
  • Predominantly case reports?
  • No recent studies (post-2020)?
  ↓
Generate gap list + summary
  ↓
Optional AI analysis of research directions
```

---

## Database Schema

### Entity Relationship

```
┌───────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     genes     │       │    variants      │       │    evidence      │
├───────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)       │──1:N──│ id (PK)          │──1:N──│ id (PK)          │
│ symbol (UQ)   │       │ gene_id (FK)     │       │ variant_id (FK)  │
│ full_name     │       │ hgvs_c (idx)     │       │ paper_id (FK)    │
│ chromosome    │       │ hgvs_p (idx)     │       │ evidence_type    │
│ description   │       │ protein_change   │       │ relevance_score  │
│ created_at    │       │ variant_type     │       │ study_quality    │
└───────────────┘       │ description      │       │ recency_score    │
        │               │ clin_sig         │       │ evidence_score   │
        │               │ clinvar_id       │       │ key_findings     │
        │               │ clinvar_data(J)  │       │ source           │
        │               │ review_status    │       │ created_at       │
        │               │ created_at       │       └────────┬─────────┘
        │               │ updated_at       │                │
        │               └────────┬─────────┘                │
        │                        │                          │
        │               ┌────────┴─────────┐       ┌────────┴─────────┐
        │               │     reports      │       │     papers       │
        │               ├──────────────────┤       ├──────────────────┤
        │               │ id (PK)          │       │ id (PK)          │
        │               │ variant_id (FK)  │       │ pmid (UQ, idx)   │
        │               │ confidence_level │       │ title            │
        │               │ confidence_score │       │ authors          │
        │               │ evidence_volume  │       │ journal          │
        │               │ evidence_quality │       │ year             │
        │               │ study_agreement  │       │ abstract         │
        │               │ exec_summary     │       │ doi              │
        │               │ clin_sig         │       │ study_type       │
        │               │ disease_assoc(J) │       │ keywords (JSON)  │
        │               │ mechanism        │       │ created_at       │
        │               │ evidence_overview│       └──────────────────┘
        │               │ confidence_assess│
        │               │ research_gaps(J) │
        │               │ ai_summary       │
        │               │ report_data (J)  │
        │               │ created_at       │
        │               └──────────────────┘
        │
        ├─── gene_papers (M:N join) ─── papers
        │
        └─── disease_papers (M:N join) ─── papers

  ┌───────────────┐
  │   diseases    │
  ├───────────────┤
  │ id (PK)       │
  │ name (idx)    │
  │ mondo_id      │
  │ description   │
  │ created_at    │
  └───────────────┘
  (J) = JSON column
  (FK) = Foreign Key
  (PK) = Primary Key
  (UQ) = Unique
  (idx) = Indexed
```

---

## Features

### 1. Variant Search (Feature 1)

The search interface accepts multiple variant notation formats:

| Format | Example | Pattern |
|--------|---------|---------|
| HGVS coding | `BRCA1 c.5266dupC` | `gene + c.` prefix + position + change |
| HGVS protein | `TP53 p.R175H` | `gene + p.` prefix + amino acid change |
| 1-letter protein | `TP53 R175H` | `gene + [A-Z]\d+[A-Z*]` |
| 3-letter protein | `TP53 Arg175His` | `gene + [A-Z][a-z]{2}\d+[A-Za-z*]` |
| Legacy | `BRCA1 185delAG` | `gene + \d+del[A-Z]+` |
| Alias | `P53 R175H` | Auto-normalized to TP53 |

Invalid inputs return a 400 error with a helpful message: `"Could not parse variant. Use format like: BRCA1 c.5266dupC, TP53 R175H, BRCA2 c.5946delT, CDH1 c.1901C>T, PALB2 c.1592delT"`

Recent searches are stored in localStorage (client-side only) and displayed as clickable badges.

### 2. ClinVar Integration (Feature 3)

**Endpoint:** NCBI E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`)

**Flow:**
1. `esearch.fcgi` — Search for ClinVar records using `gene[variant]` query
2. `efetch.fcgi?rettype=vcv` — Fetch VCV XML (the modern ClinVar format, not the deprecated `rettype=variation`)
3. Parse XML for clinical significance, review status, disease names

**VCV Accession Format:**
- Numeric IDs from esearch are zero-padded to 9 digits
- Example: ID `12374` → `VCV000012374`
- This is required by NCBI's API

**Caching:**
- JSON responses cached to `data/cache/clinvar/`
- TTL: 24 hours (configurable via `CACHE_TTL_HOURS`)
- Cache key: `{gene}_{variant}` with special characters sanitized

**Parsed Fields:**
| XML Path | Field | Example |
|----------|-------|---------|
| `VariationArchive/@VariationName` | description | `NM_000546.6(TP53):c.524G>A (p.Arg175His)` |
| `VariationArchive/@Accession` | accession | `VCV000012374` |
| `GermlineClassification/Description` | clinical_significance | `Pathogenic` |
| `GermlineClassification/ReviewStatus` | review_status | `reviewed by expert panel` |
| `OncogenicityClassification/Description` | clinical_significance (fallback) | `Oncogenic` |
| `TraitSet/Trait/Name` | diseases (if non-empty) | `Li-Fraumeni syndrome` |

### 3. PubMed Retrieval (Feature 4)

**Endpoint:** NCBI E-utilities

**Search Query Construction:**
```
(gene[Title/Abstract]) AND (variant[Text Word]) AND (breast cancer[MeSH])
```

**Result Limit:** 20 papers (configurable via `MAX_PUBMED_RESULTS`)

**Parsed Fields:**
| XML Path | Field |
|----------|-------|
| `PMID` | pmid |
| `ArticleTitle` | title |
| `Author/LastName` + `ForeName` | authors (first 10) |
| `Journal/Title` | journal |
| `PubDate/Year` | year |
| `AbstractText` | abstract (with Label attributes) |
| `ELocationId[@EIdType="doi"]` | doi |
| `Keyword` | keywords array |

**Study Type Inference (Rule-Based):**
| Keywords in Abstract | Study Type | Quality Score |
|---------------------|------------|---------------|
| "clinical trial", "randomized", "phase I/II/III" | Clinical Trial | 0.90 |
| "meta-analysis", "systematic review" | Meta-Analysis | 0.95 |
| "case report", "case study" | Case Report | 0.35 |
| "cohort", "case-control", "longitudinal" | Cohort Study | 0.75 |
| "review", "overview" | Review | 0.50 |
| "in vitro", "cell line", "functional study" | Functional Study | 0.70 |
| "genome-wide", "gwas", "association study" | Genome-Wide Study | 0.80 |
| None of the above | Research Article | 0.50 |

**Caching:** Same scheme as ClinVar, stored in `data/cache/pubmed/` with 24-hour TTL.

### 4. Evidence Scoring Engine (Feature 6)

**Formula:**

```
EvidenceScore = 0.50 × relevance + 0.30 × study_quality + 0.20 × recency
```

**Components:**

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Relevance | 50% | Keyword overlap between paper keywords and variant key findings. Baseline: 0.5, bonus: up to +0.5 for keyword matches. Range: 0.5–1.0 |
| Study Quality | 30% | Mapped from study type (0.35 for Case Report up to 0.95 for Meta-Analysis) |
| Recency | 20% | `max(0, 1.0 - (current_year - paper_year) × 0.05)`. A paper from 2026 scores 1.0, from 2020 scores 0.7, from 2010 scores 0.2 |

**Score Display:** Scores are multiplied by 100 for the UI (0–100 scale).

### 5. Confidence Engine (Feature 10)

**Formula:**

```
ConfidenceScore = 0.30 × volume_score + 0.40 × quality_score + 0.30 × agreement_score
```

**Components:**

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Evidence Volume | 30% | Logarithmic scale based on paper count: 0 papers = 0.0, 1-2 = 0.2, 3-4 = 0.4, 5-9 = 0.6, 10-19 = 0.8, 20+ = 1.0 |
| Evidence Quality | 40% | Average `study_quality_score` across all papers (0.0–1.0) |
| Study Agreement | 30% | Proportion of papers with the same clinical significance classification (0.0–1.0) |

**Levels:**

| Score Range | Level | Meaning |
|------------|-------|---------|
| 0.70–1.00 | High | Well-characterized variant with strong, consistent evidence |
| 0.40–0.69 | Moderate | Some evidence available, but gaps remain |
| 0.01–0.39 | Low | Limited evidence, further studies needed |
| 0.00 | Insufficient Evidence | No supporting papers found; no hallucination |

### 6. AI Research Summary (Feature 9)

**Provider:** Groq API with Llama 3.3 70B (requires `GROQ_API_KEY`)

**Generation:** Triggered via `/api/v1/variants/{id}/summary`

**Prompt Engineering:**
- System prompt instructs the model to be evidence-based and cite specific PMIDs
- Context includes all paper titles, PMIDs, years, study types, evidence scores, and key findings
- Temperature set to 0.3 (minimal creativity, prioritizes accuracy)

**Output Sections:**
1. Executive Summary
2. Clinical Significance
3. Disease Associations
4. Mechanism of Action
5. Evidence Overview
6. Confidence Assessment

**Hallucination Prevention:**
- Model explicitly instructed: "Only use the provided evidence. Do not hallucinate."
- No retrieved evidence → model returns "No evidence available for this variant"
- All claims should reference supporting PMIDs

### 7. Knowledge Relationships View (Feature 8)

**Implementation:** Custom SVG-based graph visualization (no external graph library dependency)

**Entity Types (color-coded):**
| Type | Color | Description |
|------|-------|-------------|
| Gene | Blue (#3b82f6) | BRCA1, BRCA2, TP53, CDH1, PALB2, CHEK2, ATM, PTEN |
| Variant | Purple (#8b5cf6) | The specific mutation |
| Paper | Green (#059669) | PubMed articles |
| Disease | Amber (#d97706) | Associated conditions |

**Relationships:** `has variant`, `evidence`, `associated with`

**Layout:** Force-directed layout with gene at top, variant in center, papers and diseases arranged radially.

**Data Source:** `/api/v1/graph/{variant_id}` endpoint constructs nodes and edges from the database.

### 8. Research Gap Detection (Feature 11)

**Rule-Based Analysis (`ResearchGapDetector.analyze_gaps`):**

| Check | Condition | Gap Message |
|-------|-----------|-------------|
| Clinical trials | Count == 0 | "No clinical trials found for this variant" |
| Functional studies | Count == 0 | "Functional characterization studies are limited" |
| High-quality studies | Count < 3 | "Only N high-quality studies available (need 3+)" |
| Total evidence | Count < 5 | "Limited evidence volume (N papers)" |
| Case report dominance | Case reports > 50% of total | "Evidence is predominantly case reports; larger cohort studies needed" |
| Recent publications | Post-2020 papers < 2 | "Recent studies (post-2020) are lacking" |
| All checks pass | None triggered | "Relatively well-studied; further meta-analyses could strengthen evidence" |

**Output:** Gap list + well-studied boolean + summary text + study type distribution.

### 9. PDF Report Export (Feature 12)

**Library:** ReportLab

**Sections:**
1. **Variant Header** — Gene, HGVS notation, clinical significance, confidence level
2. **Executive Summary** — AI-generated or evidence overview
3. **Clinical Significance** — ClinVar data with review status
4. **Evidence Overview** — Volume, quality, agreement scores
5. **Supporting Studies** — Top 10 papers with titles, PMIDs, years, scores
6. **Disease Associations** — Disease names from ClinVar
7. **Confidence Assessment** — Level + score + detailed breakdown

**Generation:** Synchronous, returns PDF as download (~4KB for average reports).

---

## API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Health check | None |
| `GET` | `/dashboard` | Platform statistics | None |
| `POST` | `/variants/search` | Search and analyze a variant | None |
| `GET` | `/variants` | List all variants | None |
| `GET` | `/variants/{id}` | Variant detail with evidence | None |
| `GET` | `/variants/{id}/evidence` | Evidence list with scores | None |
| `GET` | `/variants/{id}/report` | Confidence report | None |
| `POST` | `/variants/{id}/summary` | Generate AI summary (Groq) | None |
| `GET` | `/variants/{id}/gaps` | Research gap analysis | None |
| `GET` | `/variants/{id}/evidence-provenance` | Per-paper score contribution breakdown | None |
| `GET` | `/variants/{id}/acmg` | ACMG/AMP variant classification | None |
| `GET` | `/variants/{id}/report/pdf` | Download PDF report | None |
| `GET` | `/graph/{id}` | Knowledge graph data | None |
| `POST` | `/compare` | Compare two variants side by side | None |

### Request/Response Examples

**POST /variants/search**
```json
// Request
{ "query": "TP53 R175H" }

// Response (200)
{
  "id": 1,
  "hgvs_c": null,
  "hgvs_p": null,
  "protein_change": "R175H",
  "gene": "TP53",
  "gene_full_name": "Tumor Protein P53",
  "variant_type": "snv",
  "clinical_significance": "Pathogenic",
  "clinvar_id": "12374",
  "review_status": "reviewed by expert panel",
  "diseases": ["Li-Fraumeni syndrome"]
}

// Response (400 - invalid)
{
  "detail": "Could not parse variant. Use format like: BRCA1 c.5266dupC, TP53 R175H, BRCA2 c.5946delT, CDH1 c.1901C>T, PALB2 c.1592delT"
}

// Response (400 - unsupported gene)
{
  "detail": "Could not parse variant. Use format like: BRCA1 c.5266dupC, TP53 R175H, BRCA2 c.5946delT, CDH1 c.1901C>T, PALB2 c.1592delT"
}
```

**GET /variants/{id}/report**
```json
{
  "id": 1,
  "variant_id": 1,
  "confidence_level": "High",
  "confidence_score": 0.76,
  "evidence_volume": 18,
  "evidence_quality": 0.55,
  "study_agreement": 0.89,
  "executive_summary": "TP53 R175H is a well-characterized pathogenic variant...",
  "clinical_significance": "Pathogenic",
  "disease_associations": [{"name": "Li-Fraumeni syndrome"}],
  "evidence_overview": "Found 18 supporting papers. Average evidence score: 0.55...",
  "confidence_assessment": "Based on 18 supporting papers; evidence volume score: 0.80...",
  "research_gaps": [],
  "ai_summary": "## Executive Summary\nThe TP53 R175H mutation...",
  "created_at": "2026-06-16T12:00:00"
}
```

**Full OpenAPI documentation** at http://localhost:8000/docs (Swagger UI) or http://localhost:8000/redoc (ReDoc).

---

## Services Deep Dive

### `VariantAnalysisService`

The orchestrator — coordinates all other services for a single variant analysis.

**Key Methods:**
- `parse_variant(query)` → Parses user input using regex patterns
- `get_or_create_gene(symbol)` → Returns existing gene or creates with metadata
- `analyze_variant(query)` → Full pipeline: parse → gene → variant → ClinVar → PubMed → evidence
- `get_variant_detail(variant_id)` → Returns variant + gene + evidence with scores

**Regex Patterns (in priority order):**
```python
r"^(GENE)\s+(c\.\d+[A-Za-z_>delinsup*]{1,30})$"     # HGVS c.
r"^(GENE)\s+(p\.[A-Za-z]{1,3}\d+[A-Za-z*]{1,5})$"   # HGVS p.
r"^(GENE)\s+([A-Z][a-z]{2}\d+[A-Za-z*]{1,5})$"      # 3-letter protein
r"^(GENE)\s+([A-Z]\d+[A-Z*]{1,3})$"                 # 1-letter protein
r"^(GENE)\s+(\d+del[A-Z]+)$"                         # Legacy del notation
r"^(GENE)\s+(\d+ins[A-Z]+)$"                         # Legacy ins notation
```

### `ClinVarService`

**Critical Implementation Details:**
- Uses `rettype=vcv` (not the deprecated `rettype=variation`)
- VCV IDs must be zero-padded to 9 digits: `str.zfill(9)`
- XML namespaces are NOT required (VCV XML doesn't use them)
- Falls back from `gene[variant]` query to `gene variant` plain text query
- Caches aggressively to avoid hitting NCBI rate limits

### `PubMedService`

**Critical Implementation Details:**
- Constructs complex query with `[Title/Abstract]`, `[Text Word]`, and `[MeSH Terms]` fields
- Study type inference is text-based (pattern matching on abstract + keywords)
- `_infer_study_type` checks keywords in priority order (Clinical Trial → Meta-Analysis → Case Report → ... → Research Article)
- Caches results with gene+variant+disease as composite key

### `EvidenceScoringService`

**Critical Implementation Details:**
- `score_evidence_for_variant(variant_id)` — Updates scores for ALL evidence linked to a variant
- Scores are stored in the database (not computed on-the-fly)
- Recency calculation: linear decay from current year (2026) backward

### `ConfidenceEngine`

**Critical Implementation Details:**
- `calculate_confidence(variant_id)` — Pure function, no side effects
- `generate_report(variant_id)` — Creates Report record if one doesn't exist
- Study agreement calculated by finding the most common clinical significance across all evidence

### `AISummaryService`

**Critical Implementation Details:**
- Requires `GROQ_API_KEY` in environment; returns fallback message if not set
- Context builder constructs structured text with all paper metadata
- System prompt explicitly prohibits hallucination
- Temperature locked at 0.3

### `ACMGService`

**Critical Implementation Details:**
- `classify(variant_id)` — Evaluates ACMG/AMP 2015 criteria against available variant data
- Detects null variants (PVS1) via variant_type + HGVS c. + protein_change pattern matching
- Uses ClinVar significance and review status for PS1, BS1, BP4, PM2
- Evidence volume thresholds trigger PP4 (≥5 papers) and PS4 (≥10 papers)
- Missense pathogenic variants trigger PP3
- Scoring: Very Strong=4, Strong=3, Moderate=2, Supporting=1
- Returns classification level: Pathogenic / Likely pathogenic / Uncertain significance / Likely benign / Benign

### `ResearchGapDetector`

**Critical Implementation Details:**
- `analyze_gaps(variant_id)` — Pure rule-based analysis
- `compare_variants(gene_symbol)` — Cross-variant comparison for a gene
- Gap rules designed to be conservative (avoid false positives)

### `PDFReportGenerator`

**Critical Implementation Details:**
- Uses ReportLab's `platypus` (Platform Independent Page Layout)
- Custom paragraph styles with Sydney color scheme (#1a365d, #2b6cb0)
- Returns raw bytes for HTTP response with `Content-Disposition: attachment`

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- 8GB RAM (system requirement, app uses ~350MB)
- Dual-core CPU
- Internet connection (for NCBI API calls)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure (minimal — works out of box for basic features)
echo "GROQ_API_KEY=gsk_your_key_here" > .env  # Optional, for AI summaries

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

### Docker Setup

```bash
docker compose up --build
```

### Single-Command Run

```bash
./run.sh
```

Starts both backend and frontend, kills existing processes on ports 8000/3000 automatically. Press Ctrl+C to stop both.

---

## Variant Format Reference

### Accepted Inputs

```
# BRCA1
BRCA1 c.5266dupC       → HGVS coding (duplication)
BRCA1 185delAG         → Legacy notation (deletion)
BRCA1 5382insC         → Legacy notation (insertion)

# BRCA2
BRCA2 c.5946delT       → HGVS coding (deletion)
BRCA2 6174delT         → Legacy notation

# TP53
TP53 R175H             → Protein change (1-letter code)
TP53 p.R175H           → Protein change (HGVS p. format)
TP53 Arg175His         → Protein change (3-letter code)
TP53 R273H             → Another common TP53 mutation
TP53 R248Q             → Another common TP53 mutation
P53 R175H              → Alias (auto-normalized to TP53)
TP53 R999X             → Nonsense mutation (rare/not in ClinVar)

# CDH1
CDH1 c.1901C>T         → HGVS coding (missense)

# PALB2
PALB2 c.1592delT       → HGVS coding (frameshift deletion)

# CHEK2
CHEK2 c.1100delC       → HGVS coding (frameshift deletion)

# ATM
ATM c.7271T>G          → HGVS coding (missense)

# PTEN
PTEN c.697C>T          → HGVS coding (nonsense)
```

### Rejected Inputs (400 Error)

```
EGFR T790M              → Unsupported gene (consider contributing)
KRAS G12D               → Unsupported gene
ALK F1174L              → Unsupported gene
hello world             → Not a variant
12345                   → Not a variant
TP53 mutation           → Too vague
BRCA1 cancer            → Not a variant
BRCA1'; DROP TABLE...   → SQL injection (rejected)
<script>alert(1)</script> → XSS (rejected)
```

---

## Testing Guide

### Backend Tests

```bash
cd backend
pytest ../tests/backend -v

# With coverage
pytest ../tests/backend -v --cov=app

# Specific test file
pytest ../tests/backend/test_services.py -v
pytest ../tests/backend/test_api.py -v
```

### Test Coverage

**33 tests covering:**

| Test Suite | Tests | What It Tests |
|------------|-------|---------------|
| `test_api.py` | 18 | Health, dashboard, search, 404 handling, evidence, report, graph, gaps, OpenAPI, compare, trends, why-matters, full pipeline |
| `test_services.py` | 15 | Variant parsing (7), gene lookup (2), evidence scoring (3), confidence engine (2), research gaps (1) |

### Manual QA Test Suite

Run the comprehensive test script:

```bash
# Test all variant formats
for q in "TP53 R175H" "TP53 p.R175H" "P53 R175H" "TP53 Arg175His" \
         "BRCA1 c.5266dupC" "BRCA1 185delAG" \
         "BRCA2 c.5946delT" \
         "CDH1 c.1901C>T" "PALB2 c.1592delT" "CHEK2 c.1100delC" \
         "ATM c.7271T>G" "PTEN c.697C>T" \
         "TP53 R999X" "EGFR T790M" "invalid"; do
  echo ">>> $q"
  curl -s -m 15 -X POST http://localhost:8000/api/v1/variants/search \
    -H 'Content-Type: application/json' \
    -d "{\"query\":\"$q\"}" | python3 -m json.tool 2>/dev/null
done
```

---

## Benchmark Suite

Regression test the full retrieval pipeline against known variants.

### `benchmark.json`

11 test cases across 8 genes with expected results:

| Variant | Min Papers | Expected Confidence | Expected Significance |
|---------|-----------|-------------------|----------------------|
| TP53 R175H | ≥15 | Moderate, High | Pathogenic |
| BRCA1 c.5266dupC | ≥15 | High | Pathogenic |
| BRCA2 c.5946delT | ≥10 | Moderate, High | Likely benign |
| TP53 R248W | ≥10 | Moderate, High | Pathogenic |
| TP53 R273H | ≥10 | Moderate, High | Pathogenic |
| TP53 R999X | 0 | Insufficient Evidence | null |
| CDH1 c.1901C>T | ≥2 | Low, Moderate | Pathogenic/Likely pathogenic |
| PALB2 c.1592delT | ≥3 | Moderate, High | Pathogenic |
| CHEK2 c.1100delC | ≥5 | Moderate, High | Conflicting classifications |
| ATM c.7271T>G | ≥3 | Moderate, High | Pathogenic |
| PTEN c.697C>T | 0 | Insufficient Evidence | Pathogenic/Likely pathogenic |

### `benchmark.py`

Runs the full pipeline (ClinVar + PubMed, evidence scoring, confidence engine) against each variant using a fresh SQLite database, validates against expectations, and prints a colored pass/fail report. Exit code is 0 only if all pass.

```bash
python benchmark.py                  # run all 11 variants
python benchmark.py --variant R175H  # run single variant
python benchmark.py --verbose        # show every check detail
python benchmark.py --variant CDH1   # run all CDH1 benchmark variants
```

The benchmark uses `sqlite:///./data/benchmark.db` and cleans up after itself.

---

## New Features (v0.2.0)

### Variant Comparison

Compare two variants side by side across key metrics.

**Backend:** `POST /api/v1/compare`

```json
{
  "query1": "TP53 R175H",
  "query2": "TP53 R273H"
}
```

Returns both variants' gene, paper count, confidence score/level, evidence volume/quality/agreement, and clinical significance.

**Frontend:** "Compare" tab on the variant detail page with two input fields and a comparison table.

### Confidence Breakdown

Decompose the confidence score into its weighted components so users can inspect what drives the score.

Displayed in the Overview tab below the confidence assessment cards:

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Evidence Volume | ×30% | `papers_count × 30` |
| Evidence Quality | ×40% | `avg_study_quality × 100 × 40` |
| Study Agreement | ×30% | `consensus_percent × 100 × 30` |
| **Total** | **100%** | Sum of all three |

Each component has a proportional bar and shows its raw value.

### Publication Trend Analysis

Visualize research activity over time for any variant.

**Backend:** `GET /api/v1/variants/{id}/publications/trends`

Groups evidence papers by year and returns a sorted list of `{year, count}` pairs.

**Frontend:** "Publication Trends" tab with:
- Recharts `BarChart` showing papers per year
- Summary cards: years of data, total papers, most recent year, papers in latest year

### Why This Variant Matters

Generate a plain-language biological explanation of a variant's significance.

**Backend:** `POST /api/v1/variants/{id}/why-matters`

Uses Groq (Llama 3.3 70B) with a focused "biomedical educator" prompt to produce a 2-4 sentence explanation covering biological mechanism, clinical impact, and disease relevance.

**Frontend:** Inline button inside the Clinical Significance card on the Overview tab. Clicking generates the explanation in-place.

### Evidence Provenance

Click the confidence score in the Overview tab to see exactly how each paper contributes to the total.

**Backend:** `GET /api/v1/variants/{id}/evidence-provenance`

Returns each paper with its contribution breakdown:

| Field | Description |
|-------|-------------|
| `evidence_score` | Combined score (0.50×relevance + 0.30×quality + 0.20×recency) |
| `volume_contrib` | Volume component = 0.30 × volume_score (normalized to the variant's evidence volume tier) |
| `quality_contrib` | Quality component = 0.40 × study_quality_score |
| `agreement_contrib` | Agreement component = 0.30 × study_agreement |
| `total_contrib` | Sum of all three components |
| `contribution_pct` | `(total_contrib / confidence_score) × 100` — percent of total confidence |

**Frontend:** The Score card in the Confidence Assessment section is clickable. Clicking opens a modal with:
- Per-paper contribution bars (color-coded by contribution %)
- Raw scores (relevance, quality, recency, evidence score)
- Contribution component details (volume ×30%, quality ×40%, agreement ×30%)
- Direct link to PubMed for each paper

### ACMG/AMP Classification

Automated variant interpretation using ACMG/AMP 2015 guidelines, adapted for the available evidence.

**Backend:** `GET /api/v1/variants/{id}/acmg`

**Implemented Criteria:**

| Code | Strength | Trigger | Points |
|------|----------|---------|--------|
| PVS1 | Very Strong | Null variant (frameshift, nonsense, del/ins/dup/* in HGVS or protein change) in a gene where LOF is known mechanism | 4 |
| PS1 | Strong | Pathogenic in ClinVar with expert panel or multi-submitter review status | 3 |
| PS4 | Strong | ≥10 supporting publications (well-studied variant) | 3 |
| PM2 | Moderate | Pathogenic in ClinVar without conflicting submitters | 2 |
| PM4 | Moderate | In-frame deletion/insertion (not frameshift) | 2 |
| PP3 | Supporting | Missense variant classified as pathogenic | 1 |
| PP4 | Supporting | ≥5 supporting publications | 1 |
| BS1 | Strong | ClinVar benign classification | 3 |
| BP4 | Supporting | ClinVar likely benign classification | 1 |

**Scoring System:**
```
pathogenic_score = sum of pathogenic criteria points
benign_score = sum of benign criteria points
net_score = pathogenic_score - benign_score

if net_score > 0:
    ≥10 → Pathogenic
    ≥6  → Likely pathogenic
    else → Uncertain significance
else:
    ≥6 benign → Benign
    ≥2 benign → Likely benign
    else → Uncertain significance
```

**Frontend:** "ACMG Classification" tab on the variant detail page showing:
- Overall classification badge (Pathogenic/Likely pathogenic/Uncertain significance/Likely benign/Benign)
- Pathogenic, benign, and net score cards
- Per-criteria breakdown with strength badges (color-coded by evidence level)
- Description and supporting evidence for each triggered criterion
- Criteria count

**Example (TP53 R175H):**
| Criteria | Strength | Evidence |
|----------|----------|---------|
| PP3 | Supporting | Missense variant classified as Pathogenic |
| PP4 | Supporting | Supported by 18 publications |
| PS4 | Strong | Well-studied variant with 18 publications |
| PS1 | Strong | ClinVar: Pathogenic, Review: reviewed by expert panel |
| **Result** | **Likely pathogenic** | **Pathogenic score: 8, Benign score: 0, Net: +8** |

---

## Project Structure

```
sydney/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry, CORS, migrations
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py              # Pydantic Settings (env vars)
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # SQLAlchemy models (8 tables)
│   │   │   └── schemas.py             # Pydantic API schemas
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py              # 14 REST endpoints
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── variant_service.py     # Variant parsing + pipeline orchestration
│   │   │   ├── clinvar_service.py     # ClinVar E-utilities + VCV XML parsing
│   │   │   ├── pubmed_service.py      # PubMed E-utilities + XML parsing
│   │   │   ├── evidence_scoring.py    # Evidence score formula (0-100)
│   │   │   ├── confidence_engine.py   # Confidence levels (High/Moderate/Low)
│   │   │   ├── ai_summary.py          # Groq API integration (Llama 3.3 70B)
│   │   │   ├── research_gaps.py       # Rule-based gap detection
│   │   │   ├── acmg_service.py        # ACMG/AMP variant classification
│   │   │   └── report_generator.py    # ReportLab PDF generation
│   │   │
│   │   └── db/
│   │       ├── __init__.py
│   │       └── migrations.py          # Auto-create tables on startup
│   │
│   ├── Dockerfile                     # Python 3.12-slim
│   ├── requirements.txt
│   └── .env                           # Environment variables (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout with Header
│   │   │   ├── page.tsx               # Home: variant search
│   │   │   ├── providers.tsx          # React Query provider
│   │   │   ├── globals.css            # Tailwind + custom styles
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx           # Dashboard with stats
│   │   │   └── variants/
│   │   │       ├── page.tsx           # Variants list
│   │   │       └── [id]/
│   │   │           └── page.tsx       # Variant detail (tabs)
│   │   │
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Badge.tsx          # Status badges
│   │   │   │   ├── Button.tsx         # Variants + loading state
│   │   │   │   ├── Card.tsx           # Card container
│   │   │   │   └── Tabs.tsx           # Tab navigation
│   │   │   ├── variant/
│   │   │   │   │   │   ├── ConfidenceBreakdown.tsx # Weighted component bars
│   │   │   │   ├── EvidenceChart.tsx       # Recharts bar chart
│   │   │   │   ├── EvidenceTable.tsx       # Sortable evidence table
│   │   │   │   ├── KnowledgeGraph.tsx      # SVG relationship graph
│   │   │   │   ├── GapsAnalysis.tsx        # Research gaps view
│   │   │   │   ├── PublicationTrends.tsx   # Recharts year-by-year chart
│   │   │   │   ├── VariantCompare.tsx      # Side-by-side comparison
│   │   │   │   ├── WhyMatters.tsx          # AI biological explanation
│   │   │   │   ├── EvidenceProvenanceModal.tsx  # Per-paper contribution modal
│   │   │   │   └── ACMGClassification.tsx       # ACMG/AMP criteria display
│   │   │   └── layout/
│   │   │       ├── Header.tsx         # Nav header
│   │   │       └── ThemeToggle.tsx    # Dark/light mode
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client (fetch wrapper)
│   │   │   ├── hooks.ts               # React Query hooks
│   │   │   └── utils.ts              # cn(), formatScore(), etc.
│   │   │
│   │   └── types/
│   │       └── index.ts               # TypeScript interfaces
│   │
│   ├── Dockerfile                     # Node 20-alpine multi-stage
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── next.config.js
│   └── .env.local
│
├── tests/
│   ├── backend/
│   │   ├── test_api.py                # 13 API integration tests
│   │   └── test_services.py           # 14 unit tests
│   └── frontend/
│
├── data/                              # Database + cache (gitignored)
│   └── .gitkeep
│
├── docker-compose.yml                 # Backend + Frontend
├── .dockerignore
├── .gitignore
├── pyproject.toml                     # Pytest config
├── run.sh                             # Single-command launcher
├── benchmark.json                     # 11 benchmark test cases (8 genes)
├── benchmark.py                       # Regression test runner
└── README.md
```

---

## Adding New Genes

### Step 1: Add Gene Metadata

In `backend/app/services/variant_service.py`, add to the gene metadata dictionary in `get_or_create_gene`:

```python
gene_data = {
    "BRCA1": ("BRCA1", "Breast Cancer Gene 1",                              "17", "Tumor suppressor involved in DNA repair"),
    "BRCA2": ("BRCA2", "Breast Cancer Gene 2",                              "13", "Tumor suppressor involved in DNA repair"),
    "TP53":  ("TP53",  "Tumor Protein P53",                                 "17", "Tumor suppressor regulating cell cycle"),
    "CDH1":  ("CDH1",  "Cadherin 1",                                        "16", "Cell adhesion; germline → hereditary diffuse gastric cancer"),
    "PALB2": ("PALB2", "Partner And Localizer of BRCA2",                    "16", "Fanconi anemia group N; BRCA2-interacting DNA repair"),
    "CHEK2": ("CHEK2", "Checkpoint Kinase 2",                               "22", "Cell cycle checkpoint kinase; DNA damage response"),
    "ATM":   ("ATM",   "ATM Serine/Threonine Kinase",                       "11", "DNA damage response kinase; double-strand break repair"),
    "PTEN":  ("PTEN",  "Phosphatase and Tensin Homolog",                    "10", "Tumor suppressor phosphatase; PI3K/AKT pathway"),
    # Add your new gene here:
}
```

### Step 2: Add Gene Alias (optional)

```python
GENE_ALIASES = {
    "brca1": "BRCA1", "brca1": "BRCA1",
    "brca2": "BRCA2", "brca2": "BRCA2",
    "tp53":  "TP53",  "tp53": "TP53",  "p53": "TP53",
    "cdh1":  "CDH1",  "cdh1": "CDH1",
    "palb2": "PALB2", "palb2": "PALB2",
    "chek2": "CHEK2", "chek2": "CHEK2",
    "atm":   "ATM",   "atm": "ATM",
    "pten":  "PTEN",  "pten": "PTEN",
    # Add your new gene alias here:
}
```

### Step 3: Update Regex Validation (frontend)

In `frontend/src/app/page.tsx`, update the validation regex:

```typescript
const valid = /^(BRCA1|BRCA2|TP53|P53|CDH1|PALB2|CHEK2|ATM|PTEN)\s/i.test(trimmed);
```

### Step 4: Add Example Suggestions (optional)

In the same file, add clickable examples:

```typescript
<span onClick={() => setQuery("CDH1 c.1901C>T")}>CDH1 c.1901C>T</span>
<span onClick={() => setQuery("PALB2 c.1592delT")}>PALB2 c.1592delT</span>
```

**That's it.** The architecture automatically handles:
- Gene creation in the database
- ClinVar queries with the new gene symbol
- PubMed searches with the new gene
- Evidence scoring and confidence calculation
- Knowledge graph relationships

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./data/sydney.db` | No | Database connection string. Use `postgresql://user:pass@host/db` for PostgreSQL |
| `GROQ_API_KEY` | `` | No | Groq API key for AI summaries. Without it, the summary feature shows "unavailable" |
| `DEBUG` | `true` | No | Enable SQLAlchemy echo and FastAPI debug |

### Frontend (`frontend/.env.local`)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | No | Backend API URL (used by the API client) |

---

## Resource Usage

| Resource | Usage | Notes |
|----------|-------|-------|
| **RAM (backend)** | ~200 MB | Python + SQLAlchemy + httpx |
| **RAM (frontend)** | ~150 MB | Node.js + Next.js dev server |
| **RAM (total)** | ~350 MB | Runs comfortably on 8GB systems |
| **CPU** | < 5% idle | Spikes during API calls (1-3 seconds) |
| **Storage** | ~50 MB | SQLite database + JSON caches |
| **Network** | Minimal | Only NCBI E-utilities + optional Groq API |

---

## Troubleshooting

### ClinVar Returns "Unknown"

1. Check internet connectivity (NCBI API required)
2. Clear cache: `rm -rf data/cache/clinvar/`
3. Ensure VCV ID format: ID should be zero-padded to 9 digits
4. Check NCBI E-utilities status (rare downtime)

### PubMed Returns 0 Papers

1. The variant may genuinely have no literature
2. Try a broader query (the service uses restrictive field tags)
3. Clear cache: `rm -rf data/cache/pubmed/`

### AI Summary Not Working

1. Verify `GROQ_API_KEY` is set in `.env`
2. Check Groq API status
3. The service returns a message if key is missing

### Port Already in Use

The `run.sh` script automatically kills processes on ports 8000 and 3000 before starting. If running manually:

```bash
kill $(lsof -ti:8000) 2>/dev/null
kill $(lsof -ti:3000) 2>/dev/null
```

### Database Errors

Delete the SQLite database to reset:

```bash
rm -f data/sydney.db
```

The database is automatically recreated with all tables on next startup.

---

## License

MIT
