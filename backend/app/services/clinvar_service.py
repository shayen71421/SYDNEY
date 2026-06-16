import httpx
import xml.etree.ElementTree as ET
import json
import time
from typing import Optional
from pathlib import Path

from app.core.config import settings


class ClinVarService:
    CACHE_DIR = Path("data/cache/clinvar")

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.base_url = settings.clinvar_base_url

    def _cache_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(" ", "_").replace(".", "_")
        return self.CACHE_DIR / f"{safe}.json"

    def _load_cache(self, key: str) -> Optional[dict]:
        path = self._cache_path(key)
        if path.exists():
            age = time.time() - path.stat().st_mtime
            if age < settings.cache_ttl_hours * 3600:
                return json.loads(path.read_text())
        return None

    def _save_cache(self, key: str, data: dict):
        self._cache_path(key).write_text(json.dumps(data, indent=2))

    def fetch_variant_data(self, gene: str, variant: str) -> Optional[dict]:
        cache_key = f"{gene}_{variant}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached

        try:
            term = f"{gene}[gene] AND {variant}[variant]"
            params = {
                "db": "clinvar",
                "term": term,
                "retmax": "5",
                "retmode": "json",
            }
            resp = httpx.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=15)
            if resp.status_code != 200:
                return None

            data = resp.json()
            ids = data.get("esearchresult", {}).get("idlist", [])
            if not ids:
                return None

            fetch_params = {
                "db": "clinvar",
                "id": ",".join(ids[:3]),
                "rettype": "variation",
                "retmode": "xml",
            }
            fetch_resp = httpx.get(f"{self.base_url}/efetch.fcgi", params=fetch_params, timeout=15)
            if fetch_resp.status_code != 200:
                return None

            result = self._parse_clinvar_xml(fetch_resp.text, ids[0])
            self._save_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"[ClinVar] Error: {e}")
            return None

    def _parse_clinvar_xml(self, xml_text: str, clinvar_id: str) -> dict:
        result = {
            "clinvar_id": clinvar_id,
            "clinical_significance": "Unknown",
            "review_status": "No assertion",
            "description": "",
            "diseases": [],
            "accession": clinvar_id,
        }

        try:
            root = ET.fromstring(xml_text)
            ns = {
                "clinvar": "http://www.ncbi.nlm.nih.gov/ns/clinvar",
            }

            for cln_var in root.iter("ClinVarSet"):
                for ref in cln_var.iter("ReferenceClinVarAssertion"):
                    for sig in ref.iter("ClinicalSignificance"):
                        desc = sig.find("Description")
                        if desc is not None and desc.text:
                            result["clinical_significance"] = desc.text
                        status = sig.find("ReviewStatus")
                        if status is not None and status.text:
                            result["review_status"] = status.text

                    for trait_set in ref.iter("TraitSet"):
                        for trait in trait_set.iter("Trait"):
                            name = trait.find("Name")
                            if name is not None and name.text:
                                result["diseases"].append(name.text)
                                if not result["description"]:
                                    result["description"] = name.text

                for var in cln_var.iter("VariationArchive"):
                    name = var.get("VariationName")
                    if name:
                        result["description"] = name

        except ET.ParseError:
            pass

        return result

    def fetch_by_clinvar_id(self, clinvar_id: str) -> Optional[dict]:
        return self.fetch_variant_data("", clinvar_id)
