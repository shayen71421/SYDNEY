from typing import Optional
from groq import Groq

from app.core.config import settings


class AISummaryService:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    def generate_summary(self, variant: str, gene: str, clinical_significance: str,
                         evidence_list: list[dict], confidence: dict) -> Optional[str]:
        if not self.client:
            return "AI summary unavailable: Groq API key not configured."

        context = self._build_context(variant, gene, clinical_significance, evidence_list, confidence)

        try:
            completion = self.client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a biomedical research assistant. Generate concise, evidence-based summaries of genetic variants. Only use the provided evidence. Do not hallucinate. Cite papers by PMID where possible."
                    },
                    {
                        "role": "user",
                        "content": f"Generate a structured research summary for the following variant:\n\n{context}\n\nFormat the response with these sections:\n1. Executive Summary\n2. Clinical Significance\n3. Disease Associations\n4. Mechanism of Action\n5. Evidence Overview\n6. Confidence Assessment\n\nCite specific papers where relevant using [PMID:xxxxx] format."
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return completion.choices[0].message.content

        except Exception as e:
            return f"AI summary generation failed: {str(e)}"

    def _build_context(self, variant: str, gene: str, clinical_significance: str,
                       evidence_list: list[dict], confidence: dict) -> str:
        lines = [f"Variant: {variant}", f"Gene: {gene}", f"Clinical Significance: {clinical_significance}"]
        lines.append(f"\nConfidence Level: {confidence.get('level', 'Unknown')}")
        lines.append(f"Evidence Volume: {confidence.get('evidence_volume', 0)} papers")
        lines.append(f"Evidence Quality: {confidence.get('evidence_quality', 0):.2f}")
        lines.append(f"Study Agreement: {confidence.get('study_agreement', 0):.2f}")

        if evidence_list:
            lines.append(f"\nSupporting Evidence ({len(evidence_list)} papers):")
            for i, ev in enumerate(evidence_list[:10], 1):
                lines.append(f"\n  Paper {i}:")
                lines.append(f"  Title: {ev.get('title', 'Unknown')}")
                lines.append(f"  PMID: {ev.get('pmid', 'N/A')}")
                lines.append(f"  Year: {ev.get('year', 'Unknown')}")
                lines.append(f"  Study Type: {ev.get('study_type', 'Unknown')}")
                lines.append(f"  Evidence Score: {ev.get('evidence_score', 0):.2f}")
                lines.append(f"  Key Findings: {ev.get('key_findings', 'N/A')[:300]}")
                if ev.get('abstract'):
                    lines.append(f"  Abstract: {ev['abstract'][:500]}")

        return "\n".join(lines)

    def generate_research_gaps(self, variant: str, gene: str, evidence_count: int,
                                evidence_list: list[dict]) -> Optional[str]:
        if not self.client:
            return "Research gap analysis unavailable: Groq API key not configured."

        context = f"Variant: {variant}\nGene: {gene}\n"
        context += f"Total supporting papers found: {evidence_count}\n\n"
        if evidence_list:
            context += "Available evidence:\n"
            for ev in evidence_list[:5]:
                context += f"- {ev.get('title', '')} ({ev.get('year', '')}) - Score: {ev.get('evidence_score', 0):.2f}\n"

        try:
            completion = self.client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a biomedical research analyst. Identify research gaps and suggest future research directions based on available evidence."
                    },
                    {
                        "role": "user",
                        "content": f"Based on the following evidence for {variant} in {gene}, identify:\n1. What is well-studied about this variant\n2. What is poorly understood\n3. Potential future research areas\n\nContext:\n{context}"
                    }
                ],
                temperature=0.3,
                max_tokens=800,
            )
            return completion.choices[0].message.content

        except Exception as e:
            return f"Research gap analysis failed: {str(e)}"
