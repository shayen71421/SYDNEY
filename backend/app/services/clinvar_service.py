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
        normalized_variant = variant
        if normalized_variant.startswith("p."):
            normalized_variant = normalized_variant[2:]

        cache_key = f"{gene}_{normalized_variant}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached

        try:
            search_terms = [
                f"{gene}[gene] AND ({normalized_variant}[variant] OR {normalized_variant}[All Fields])",
                f"{gene} {normalized_variant}",
            ]
            ids = []
            for term in search_terms:
                params = {
                    "db": "clinvar",
                    "term": term,
                    "retmax": "5",
                    "retmode": "json",
                }
                resp = httpx.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=15)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if ids:
                    break

            if not ids:
                return None

            vcv_ids = [f"VCV{id.zfill(9)}" for id in ids[:3]]

            fetch_params = {
                "db": "clinvar",
                "id": ",".join(vcv_ids),
                "rettype": "vcv",
                "retmode": "xml",
            }
            fetch_resp = httpx.get(f"{self.base_url}/efetch.fcgi", params=fetch_params, timeout=15)
            if fetch_resp.status_code != 200:
                return None

            result = self._parse_vcv_xml(fetch_resp.text, ids[0])
            self._save_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"[ClinVar] Error: {e}")
            return None

    def _parse_vcv_xml(self, xml_text: str, clinvar_id: str) -> dict:
        result = {
            "clinvar_id": clinvar_id,
            "clinical_significance": "Unknown",
            "review_status": "No assertion",
            "description": "",
            "diseases": [],
            "accession": f"VCV{clinvar_id}",
            "classification_history": [],
            "genomic_coordinates": None,
        }

        try:
            root = ET.fromstring(xml_text)

            for archive in root.iter("VariationArchive"):
                name = archive.get("VariationName")
                if name:
                    result["description"] = name
                accession = archive.get("Accession")
                if accession:
                    result["accession"] = accession

                archive_date = archive.get("DateCreated") or archive.get("DateLastUpdated") or ""

                for cls in archive.iter("GermlineClassification"):
                    desc = cls.find("Description")
                    rs = cls.find("ReviewStatus")
                    date_elem = cls.find("DateLastEvaluated")
                    cls_date = date_elem.text.strip() if date_elem is not None and date_elem.text else archive_date

                    if desc is not None and desc.text:
                        cls_sig = desc.text.strip()
                        cls_rs = rs.text.strip() if rs is not None and rs.text else "No assertion"

                        if result["clinical_significance"] == "Unknown":
                            result["clinical_significance"] = cls_sig
                        if result["review_status"] == "No assertion":
                            result["review_status"] = cls_rs

                        entry = {
                            "classification": cls_sig,
                            "review_status": cls_rs,
                            "date": cls_date,
                        }
                        if entry not in result["classification_history"]:
                            result["classification_history"].append(entry)

                for cls in archive.iter("OncogenicityClassification"):
                    if result["clinical_significance"] == "Unknown":
                        desc = cls.find("Description")
                        if desc is not None and desc.text:
                            result["clinical_significance"] = desc.text.strip()

                for trait_set in archive.iter("TraitSet"):
                    for trait in trait_set.iter("Trait"):
                        name_elem = trait.find("Name")
                        if name_elem is not None and name_elem.text and name_elem.text.strip():
                            disease = name_elem.text.strip()
                            if disease not in result["diseases"]:
                                result["diseases"].append(disease)

            for measure in root.iter("Measure"):
                sl = measure.find("SequenceLocation")
                if sl is not None:
                    loc_chr = sl.get("Chr")
                    loc_pos = sl.get("positionVCF")
                    loc_ref = sl.get("referenceAllele")
                    loc_alt = sl.get("alternateAllele")
                    if loc_chr and loc_pos and loc_ref and loc_alt:
                        result["genomic_coordinates"] = {
                            "chr": loc_chr,
                            "pos": int(loc_pos),
                            "ref": loc_ref.upper(),
                            "alt": loc_alt.upper(),
                        }
                        break

        except ET.ParseError:
            pass

        return result

    def fetch_by_clinvar_id(self, clinvar_id: str) -> Optional[dict]:
        return self.fetch_variant_data("", clinvar_id)
