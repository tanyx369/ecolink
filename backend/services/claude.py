import os
import json
from typing import AsyncGenerator

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            import anthropic
            _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        except Exception as e:
            print(f"[Claude] init error: {e}")
            _client = None
    return _client


CLAUDE_SYSTEM = """You are an expert ecosystem match-maker for an innovation programme in Southeast Asia.

PRIMARY MATCHING CRITERION: background and expertise alignment — not graph network position.
Rank and justify matches based on whether the mentor's actual professional background, industry experience, and expertise genuinely address the company's specific needs.

You receive for each candidate mentor:
- Their bio/background text
- Their sectors and expertise tags
- Individual background scores: sector_overlap (industry match), expertise_overlap (skill match), bio_keyword_overlap (narrative similarity)
- Vertex AI semantic similarity
- Past mentoring outcome history
- Gemini structural analysis

TASK: Select the TOP 3 mentors. Write reasoning that reads like an expert human recruiter — grounded in what the mentor has actually done and why that specifically helps this company.

Each JSON entry must have:
- mentor_id: exact id string from the context
- mentor_name: exact name from the context
- fit_score: float 0.0–1.0 — weight: sector_overlap×0.30 + expertise_overlap×0.30 + bio_keyword_overlap×0.15 + semantic_score×0.15 + (avg_outcome/5 or 0.70)×0.10
- reasoning: exactly 3 sentences:
    S1 — WHO: Open with the mentor's name. Describe their professional background from their bio text — their industry, career history, or specific domain experience. Narrate who they are, do not just list tags. Bad: "Ahmad has expertise in FinTech and Fundraising." Good: "Ahmad spent eight years at CIMB structuring SME financing deals before co-founding a B2B payments startup."
    S2 — WHY it fits: Explicitly connect their background to the company's stage, sector, or stated needs. Name the company. Use words like "addresses", "directly relevant to", "fills the gap in". Bad: "He aligns well with the company." Good: "This directly addresses PayLink's need for banking relationship expertise as a Seed-stage FinTech seeking its first institutional partnership."
    S3 — EVIDENCE: Cite at least two numeric data points — sector_overlap, expertise_overlap, bio_keyword_overlap, outcome ratings, or session counts. Bad: "The data supports this match." Good: "A sector overlap of 0.80 and expertise overlap of 0.67 confirm strong background alignment, backed by 3 prior engagements averaging 4.2/5."
- caveat: ONE specific concern tied to this mentor's actual profile. Examples: "No prior mentoring history recorded — first engagement risk.", "Based in Penang while company is in KL — remote coordination required.", "Expertise tags show no direct e-commerce experience despite strong FinTech background." Never write a generic caveat. Write null only if there is genuinely no concern.

ABSOLUTE RULES:
- Every sentence must differ completely between the three entries — no shared phrases, no parallel structure
- Every claim must trace back to data in the context (bio text, tag names, numeric scores)
- NEVER write standalone phrases like "extensive experience", "proven track record", "strong alignment" — always name the specific thing
- If a mentor has no past mentoring history, acknowledge it explicitly in the caveat

Output ONLY a valid JSON array — no markdown, no explanation, nothing before or after the array:
[{"mentor_id":"...","mentor_name":"...","fit_score":0.0,"reasoning":"...","caveat":"..."}]"""


async def stream_match_proposal(
    context: str, gemini_analyses: dict
) -> AsyncGenerator[str, None]:
    client = _get_client()
    if client is None:
        yield f"data: {json.dumps({'chunk': _fallback_proposal(gemini_analyses)})}\n\n"
        yield "data: [DONE]\n\n"
        return

    gemini_section = "\n".join(
        f"  {mid}:\n"
        f"    structural_score={a.get('structural_score', 'N/A')}\n"
        f"    pattern_insight={a.get('pattern_insight', '')}\n"
        f"    risk_flag={a.get('risk_flag', 'null')}"
        for mid, a in gemini_analyses.items()
    )
    full_context = (
        f"{context}\n\n"
        "GEMINI STRUCTURAL ANALYSIS PER MENTOR:\n"
        + gemini_section
    )

    print(f"[Claude] Sending context ({len(full_context)} chars) to claude-sonnet-4-6")
    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=CLAUDE_SYSTEM,
            messages=[{"role": "user", "content": full_context}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'chunk': text})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"[Claude] stream error ({type(e).__name__}): {e}")
        yield f"data: {json.dumps({'chunk': _fallback_proposal(gemini_analyses)})}\n\n"
        yield "data: [DONE]\n\n"


def generate_session_prep(mentor: dict, company: dict) -> dict:
    """Synchronous Claude call — generates a pre-session prep card."""
    client = _get_client()
    prompt = (
        f"Generate a focused mentoring session prep card.\n\n"
        f"MENTOR: {mentor.get('name')}\n"
        f"Background: {mentor.get('bio') or mentor.get('description', '')}\n"
        f"Expertise: {', '.join(mentor.get('expertise_tags', []))}\n"
        f"Sectors: {', '.join(mentor.get('sectors', []))}\n\n"
        f"COMPANY: {company.get('name')}\n"
        f"Stage: {company.get('stage', '?')} | City: {company.get('city', '?')}\n"
        f"Sectors: {', '.join(company.get('sectors', []))}\n"
        f"Needs: {', '.join(company.get('expertise_tags', []))}\n"
        f"Description: {company.get('description') or company.get('bio', '')}\n\n"
        "Return ONLY valid JSON (no markdown):\n"
        '{"questions":["3 specific diagnostic questions the mentor should ask"],'
        '"topics":["3-4 focused topics to cover based on expertise vs needs"],'
        '"success_metric":"One measurable outcome the startup should reach by next session",'
        '"mentor_angle":"One sentence on the unique perspective this specific mentor brings"}'
    )
    if client is None:
        return _fallback_prep(mentor, company)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1][4:] if parts[1].startswith("json") else parts[1]
        return json.loads(text)
    except Exception as e:
        print(f"[Claude] session_prep error: {e}")
        return _fallback_prep(mentor, company)


def _fallback_prep(mentor: dict, company: dict) -> dict:
    sectors = ", ".join(company.get("sectors", ["your sector"]))
    return {
        "questions": [
            f"What is {company.get('name', 'your company')}'s biggest challenge in {sectors} right now?",
            "What have you already tried, and what were the results?",
            "What does success look like for you in the next 90 days?",
        ],
        "topics": [
            f"Applying {mentor.get('name', 'mentor')}'s expertise in {', '.join(mentor.get('expertise_tags', ['strategy']))}",
            "Identifying the highest-leverage action for this stage",
            "Relevant network connections and resources",
        ],
        "success_metric": f"Define one clear 30-day milestone aligned with {company.get('stage', 'current')} stage priorities.",
        "mentor_angle": (
            f"{mentor.get('name', 'Your mentor')}'s background in "
            f"{', '.join(mentor.get('sectors', ['this sector']))} gives direct insight into your current challenges."
        ),
    }


def _fallback_proposal(gemini_analyses: dict) -> str:
    results = []
    for mid, analysis in list(gemini_analyses.items())[:3]:
        results.append({
            "mentor_id": mid,
            "mentor_name": mid.replace("mentor_", "").replace("_", " ").title(),
            "fit_score": round(analysis.get("structural_score", 0.65), 2),
            "reasoning": (
                f"Based on graph analysis: {analysis.get('pattern_insight', 'Good structural fit')}. "
                "Historical mentoring data suggests alignment with company needs."
            ),
            "caveat": analysis.get("risk_flag"),
        })
    return json.dumps(results)
