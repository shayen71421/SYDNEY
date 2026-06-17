import httpx
import xml.etree.ElementTree as ET
import json
import time
import re as regex
from typing import Optional
from pathlib import Path
from groq import Groq

from app.core.config import settings


class PubMedService:
    CACHE_DIR = Path("data/cache/pubmed")
    STUDY_TYPES = [
        "Clinical Trial", "Meta-Analysis", "Cohort Study", "Case Report",
        "Functional Study", "Genome-Wide Study", "Review", "Research Article",
    ]

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.base_url = settings.pubmed_base_url
        self.groq = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def _cache_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(" ", "_").replace(".", "_")
        return self.CACHE_DIR / f"{safe}.json"

    def _load_cache(self, key: str) -> Optional[list]:
        path = self._cache_path(key)
        if path.exists():
            age = time.time() - path.stat().st_mtime
            if age < settings.cache_ttl_hours * 3600:
                return json.loads(path.read_text())
        return None

    def _save_cache(self, key: str, data: list):
        self._cache_path(key).write_text(json.dumps(data, indent=2))

    def search_papers(self, gene: str, variant: str, disease: str = "breast cancer") -> list[dict]:
        cache_key = f"{gene}_{variant}_{disease}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached

        try:
            query = f"({gene}[Title/Abstract]) AND ({variant}[Title/Abstract] OR {variant.split('.')[-1]}[Text Word]) AND ({disease}[MeSH Terms] OR {disease}[Title/Abstract])"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": str(settings.max_pubmed_results),
                "retmode": "json",
                "sort": "relevance",
            }
            resp = httpx.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=15)
            if resp.status_code != 200:
                return []

            data = resp.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            papers = self._fetch_details(ids)
            self._save_cache(cache_key, papers)
            return papers

        except Exception as e:
            print(f"[PubMed] Error: {e}")
            return []

    def _fetch_details(self, pmids: list[str]) -> list[dict]:
        if not pmids:
            return []

        try:
            params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            }
            resp = httpx.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=15)
            if resp.status_code != 200:
                return []

            return self._parse_pubmed_xml(resp.text)

        except Exception as e:
            print(f"[PubMed] Fetch error: {e}")
            return []

    def _parse_pubmed_xml(self, xml_text: str) -> list[dict]:
        raw = []
        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                try:
                    pmid = article.findtext(".//PMID", "")
                    title = article.findtext(".//ArticleTitle", "")

                    authors = []
                    for author in article.findall(".//Author"):
                        last = author.findtext("LastName", "")
                        fore = author.findtext("ForeName", "")
                        if last:
                            authors.append(f"{last} {fore}".strip())

                    journal = article.findtext(".//Journal/Title", "")
                    year = article.findtext(".//PubDate/Year", "")
                    if not year:
                        year = article.findtext(".//PubDate/MedlineDate", "")
                    year = year[:4] if year else ""

                    abstract_parts = []
                    for abs_text in article.findall(".//AbstractText"):
                        label = abs_text.get("Label", "")
                        text = abs_text.text or ""
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                    abstract = " ".join(abstract_parts)

                    doi = ""
                    for eid in article.findall(".//ELocationID"):
                        if eid.get("EIdType") == "doi":
                            doi = eid.text or ""

                    keywords = []
                    for kw in article.findall(".//Keyword"):
                        if kw.text:
                            keywords.append(kw.text)

                    raw.append({
                        "pmid": pmid,
                        "title": title,
                        "authors": "; ".join(authors[:10]),
                        "journal": journal,
                        "year": int(year) if year.isdigit() else None,
                        "abstract": abstract,
                        "doi": doi,
                        "keywords": keywords,
                    })
                except Exception:
                    continue
        except ET.ParseError:
            pass

        if not raw:
            return []

        batched = self._batch_infer_study_types(raw)
        for i, paper in enumerate(raw):
            paper["study_type"] = batched[i] if i < len(batched) else self._infer_study_type(paper["abstract"], paper["keywords"])

        return raw

    def _batch_infer_study_types(self, papers: list[dict]) -> list[str]:
        if not self.groq or not papers:
            return [self._infer_study_type(p["abstract"], p["keywords"]) for p in papers]

        lines = []
        for i, p in enumerate(papers):
            title = (p.get("title") or "")[:200]
            abstract = (p.get("abstract") or "")[:500]
            lines.append(f"[{i}] Title: {title}\n    Abstract: {abstract}")

        prompt = (
            "Classify each paper below into one of these study types:\n"
            + ", ".join(self.STUDY_TYPES)
            + "\n\nReturn ONLY a valid JSON array of strings where the index matches the paper number. "
            "No explanation, no markdown, no extra text.\n\n"
            + "\n\n".join(lines)
        )

        try:
            resp = self.groq.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": "You are a biomedical research classifier. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            content = resp.choices[0].message.content.strip()
            content = regex.sub(r"^```(?:json)?\s*|\s*```$", "", content)
            types = json.loads(content)
            if isinstance(types, list) and len(types) == len(papers):
                return [t if t in self.STUDY_TYPES else self._infer_study_type(papers[i]["abstract"], papers[i]["keywords"]) for i, t in enumerate(types)]
        except Exception:
            pass

        return [self._infer_study_type(p["abstract"], p["keywords"]) for p in papers]

    def _infer_study_type(self, abstract: str, keywords: list[str]) -> str:
        text = (abstract + " " + " ".join(keywords)).lower()
        if any(w in text for w in ["clinical trial", "randomized", "phase i", "phase ii", "phase iii"]):
            return "Clinical Trial"
        if any(w in text for w in ["meta-analysis", "systematic review"]):
            return "Meta-Analysis"
        if any(w in text for w in ["case report", "case study"]):
            return "Case Report"
        if any(w in text for w in ["cohort", "case-control", "longitudinal"]):
            return "Cohort Study"
        if any(w in text for w in ["review", "overview"]):
            return "Review"
        if any(w in text for w in ["in vitro", "cell line", "functional study"]):
            return "Functional Study"
        if any(w in text for w in ["genome-wide", "gwas", "association study"]):
            return "Genome-Wide Study"
        return "Research Article"
