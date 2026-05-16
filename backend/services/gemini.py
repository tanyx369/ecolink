import os
import json

_gemini = None


def _get_client():
    global _gemini
    if _gemini is None:
        try:
            import google.generativeai as genai
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
            else:
                # Fall back to Application Default Credentials (ADC) via Vertex AI
                genai.configure()
            _gemini = genai.GenerativeModel("gemini-1.5-pro")
        except Exception as e:
            print(f"[Gemini] init error: {e}")
            _gemini = None
    return _gemini


GEMINI_SYSTEM = """You are an expertise-alignment analyst for an innovation ecosystem matching platform in Southeast Asia.
You receive a focused mentor-company profile containing: both entities' bio/background text, sectors, expertise tags, and quantitative background match scores (sector_overlap, expertise_overlap, bio_keyword_overlap, semantic_score).

Evaluate whether this mentor's background and expertise genuinely addresses this company's needs.
Return a JSON object with exactly these keys:
{
  "structural_score": 0.0-1.0,
  "pattern_insight": "1-2 sentences: name a specific aspect of the mentor's bio or expertise tags that maps to the company's sector/stage/needs, then cite the strongest numeric score that supports this",
  "risk_flag": "one specific gap in this mentor's background relative to this company's needs — e.g. 'No direct [specific sector] experience despite strong [adjacent sector] background', 'Based in [City A] while company is in [City B]', 'No prior mentoring history recorded' — or null"
}

Rules:
- structural_score: weight sector_overlap×0.30 + expertise_overlap×0.30 + bio_keyword_overlap×0.15 + semantic_score×0.15 + outcome_history×0.10
- pattern_insight must reference the mentor's actual expertise tag names or bio content — no generic statements
- risk_flag must identify a specific gap, not a vague concern
- Return ONLY valid JSON. No markdown fences, no text outside the JSON object."""


def analyse_subgraph(serialised_mentor_context: str, mentor_id: str) -> dict:
    client = _get_client()
    if client is None:
        return _fallback_analysis(mentor_id)
    try:
        prompt = (
            f"{GEMINI_SYSTEM}\n\n"
            f"Mentor-company compatibility profile:\n\n"
            f"{serialised_mentor_context}"
        )
        response = client.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[Gemini] analyse_subgraph error for {mentor_id}: {e}")
        return _fallback_analysis(mentor_id)


def _fallback_analysis(mentor_id: str) -> dict:
    return {
        "structural_score": 0.65,
        "pattern_insight": f"Mentor {mentor_id} shows moderate connectivity in the ecosystem graph.",
        "risk_flag": None,
    }
