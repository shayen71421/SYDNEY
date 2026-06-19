import httpx
import json
import time
from typing import Optional
from pathlib import Path

from app.core.config import settings


class GnomadService:
    CACHE_DIR = Path("data/cache/gnomad")
    API_URL = "https://gnomad.broadinstitute.org/api"

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_path(key).write_text(json.dumps(data, indent=2))

    def fetch_frequency(self, gene: str, variant: str, clinvar_data: Optional[dict] = None) -> Optional[dict]:
        cache_key = f"{gene}_{variant}"
        cached = self._load_cache(cache_key)
        if cached:
            return cached

        coords = self._extract_coordinates(clinvar_data) if clinvar_data else None
        if not coords:
            return {"_no_coordinates": True}

        variant_id = f"{coords['chr']}-{coords['pos']}-{coords['ref']}-{coords['alt']}"

        query = """
        query VariantFrequency($datasetId: DatasetId!, $variantId: String!) {
          variant(variantId: $variantId, dataset: $datasetId) {
            variant_id
            genome {
              af
              ac
              an
              homozygote_count
              populations {
                id
                ac
                an
              }
            }
            exome {
              af
              ac
              an
              homozygote_count
              populations {
                id
                ac
                an
              }
            }
          }
        }
        """

        variables = {
            "datasetId": "gnomad_r4",
            "variantId": variant_id,
        }

        try:
            resp = httpx.post(
                self.API_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            variant_data = data.get("data", {}).get("variant")
            if not variant_data:
                self._save_cache(cache_key, {"_not_found": True})
                return {"_not_found": True}

            genome = variant_data.get("genome") or {}
            exome = variant_data.get("exome") or {}

            genome_af = genome.get("af")
            exome_af = exome.get("af")
            # Use genome AF if available, else exome AF, else None
            allele_frequency = genome_af if genome_af is not None else exome_af

            populations = {}
            pop_source = genome if genome.get("populations") else exome
            for pop in (pop_source.get("populations") or []):
                pop_id = pop.get("id", "unknown")
                ac = pop.get("ac")
                an = pop.get("an")
                populations[pop_id] = {
                    "af": ac / an if ac is not None and an and an > 0 else None,
                    "ac": ac,
                    "an": an,
                }

            result = {
                "allele_frequency": allele_frequency,
                "allele_count": genome.get("ac") if genome.get("ac") is not None else exome.get("ac"),
                "allele_number": genome.get("an") if genome.get("an") is not None else exome.get("an"),
                "homozygote_count": genome.get("homozygote_count") if genome.get("homozygote_count") is not None else exome.get("homozygote_count"),
                "population_frequencies": populations,
                "gnomad_variant_id": variant_data.get("variant_id"),
            }

            self._save_cache(cache_key, result)
            return result

        except Exception as e:
            print(f"[gnomAD] Error: {e}")
            return None

    def _extract_coordinates(self, clinvar_data: dict) -> Optional[dict]:
        try:
            info = clinvar_data.get("genomic_coordinates")
            if info and all(k in info for k in ("chr", "pos", "ref", "alt")):
                return info
        except Exception:
            pass
        return None
