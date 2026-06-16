#!/usr/bin/env python3
"""Benchmark suite for Sydney variant retrieval pipeline.

Usage:
    python benchmark.py                   # runs all tests
    python benchmark.py --variant R175H   # run specific variant
    python benchmark.py --verbose         # show details for each check
"""

import json
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

os.environ["DATABASE_URL"] = "sqlite:///./data/benchmark.db"
os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")

from sqlalchemy.orm import Session
from app.models.database import engine, Base, Variant, Gene, Evidence, Paper, Report
from app.services.variant_service import VariantAnalysisService
from app.services.evidence_scoring import EvidenceScoringService
from app.services.confidence_engine import ConfidenceEngine
from app.services.acmg_service import ACMGService

Base.metadata.create_all(bind=engine)
from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(bind=engine)


PASS = "PASS"
FAIL = "FAIL"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def color(s, c):
    return f"{c}{s}{RESET}"


def run_benchmark(variant_filter=None, verbose=False):
    bm_path = Path(__file__).resolve().parent / "benchmark.json"
    with open(bm_path) as f:
        cases = json.load(f)

    results = {"pass": 0, "fail": 0, "total": 0, "checks": 0, "details": []}

    for case in cases:
        query = case["variant"]
        expected = case["expected"]

        if variant_filter and variant_filter.lower() not in query.lower():
            continue

        results["total"] += 1
        case_result = {"variant": query, "checks": [], "pass": True}
        db: Session = SessionLocal()

        try:
            service = VariantAnalysisService(db)
            analysis = service.analyze_variant(query)

            if not analysis:
                print(f"  {color('ERROR', RED)} Could not parse variant: {query}")
                case_result["pass"] = False
                case_result["checks"].append({"check": "parse", "status": FAIL, "detail": "Parsing failed"})
                results["fail"] += 1
                results["details"].append(case_result)
                continue

            variant = analysis["variant"]
            gene = analysis["gene"]

            scoring = EvidenceScoringService(db)
            scoring.score_evidence_for_variant(variant.id)

            engine = ConfidenceEngine(db)
            confidence = engine.calculate_confidence(variant.id)
            evidence_count = db.query(Evidence).filter(Evidence.variant_id == variant.id).count()

            checks = []

            min_p = expected["min_papers"]
            passed = evidence_count >= min_p
            checks.append({
                "check": f"papers >= {min_p}",
                "status": PASS if passed else FAIL,
                "got": evidence_count,
            })
            if not passed:
                case_result["pass"] = False

            cl = confidence["level"]
            passed_cl = cl in expected["confidence"]
            checks.append({
                "check": f"confidence in {expected['confidence']}",
                "status": PASS if passed_cl else FAIL,
                "got": cl,
            })
            if not passed_cl:
                case_result["pass"] = False

            cs = variant.clinical_significance
            ecs = expected["clinical_significance"]
            if ecs is None:
                passed_cs = cs is None or cs == ""
            else:
                passed_cs = (cs or "").lower() == ecs.lower()
            checks.append({
                "check": f"clinical_significance == '{ecs}'",
                "status": PASS if passed_cs else FAIL,
                "got": cs or "",
            })
            if not passed_cs:
                case_result["pass"] = False

            checks.append({
                "check": "confidence_score",
                "status": PASS,
                "got": f"{confidence['score']:.3f}",
            })
            checks.append({
                "check": "evidence_volume",
                "status": PASS,
                "got": confidence["evidence_volume"],
            })
            checks.append({
                "check": "evidence_quality",
                "status": PASS,
                "got": f"{confidence['evidence_quality']:.3f}",
            })

            acmg = ACMGService(db)
            acmg_result = acmg.classify(variant.id)
            eacmg = expected.get("acmg_classification", None)
            if eacmg:
                passed_acmg = acmg_result["classification"] in eacmg if isinstance(eacmg, list) else acmg_result["classification"] == eacmg
                checks.append({
                    "check": f"ACMG classification == {eacmg}",
                    "status": PASS if passed_acmg else FAIL,
                    "got": acmg_result["classification"],
                })
                if not passed_acmg:
                    case_result["pass"] = False
                checks.append({
                    "check": "ACMG criteria count",
                    "status": PASS,
                    "got": len(acmg_result["criteria"]),
                })

            case_result["checks"] = checks
            results["checks"] += len(checks)

            if case_result["pass"]:
                results["pass"] += 1
            else:
                results["fail"] += 1

            results["details"].append(case_result)

        except Exception as e:
            print(f"  {color('ERROR', RED)} Exception for {query}: {e}")
            case_result["pass"] = False
            case_result["checks"].append({"check": "exception", "status": FAIL, "detail": str(e)})
            results["fail"] += 1
            results["details"].append(case_result)
        finally:
            db.close()

    return results


def print_report(results, verbose=False):
    print()
    print(f"{BOLD} Sydney Benchmark Results{RESET}")
    print(f"{'=' * 60}")

    for detail in results["details"]:
        variant = detail["variant"]
        status = color("PASS", GREEN) if detail["pass"] else color("FAIL", RED)
        print(f"\n  {status} {color(variant, BOLD)}")
        for c in detail["checks"]:
            s = color(c["status"], GREEN if c["status"] == PASS else RED)
            got = c.get("got", "")
            detail_str = f"  {s} {c['check']}"
            if got:
                detail_str += f"  →  {color(got, CYAN)}"
            if c.get("detail"):
                detail_str += f"  ({c['detail']})"
            if verbose or c["status"] == FAIL:
                print(detail_str)

    print()
    print(f"{'=' * 60}")
    total = results["pass"] + results["fail"]
    pct = (results["pass"] / total * 100) if total > 0 else 0
    print(f"  {color(results['pass'], GREEN)} passed  {color(results['fail'], RED)} failed  "
          f"({results['checks']} checks across {total} variants)")
    print(f"  Overall: {color(f'{pct:.0f}%', GREEN if pct >= 80 else YELLOW if pct >= 50 else RED)}")

    if results["fail"] > 0:
        print(f"\n  {color('FAILED variants:', RED)}")
        for d in results["details"]:
            if not d["pass"]:
                print(f"    {color(d['variant'], BOLD)}")
        print()
        sys.exit(1)
    else:
        print(f"  {color('All benchmarks passed.', GREEN)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sydney Benchmark Suite")
    parser.add_argument("--variant", help="Run only variants matching this string (case-insensitive)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all check details")
    args = parser.parse_args()

    print(f"{BOLD}Running Sydney benchmark suite...{RESET}")
    print(f"  Database: sqlite:///./data/benchmark.db")
    results = run_benchmark(variant_filter=args.variant, verbose=args.verbose)
    print_report(results, verbose=args.verbose)
