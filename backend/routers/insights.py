from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.firestore import get_all_nodes, get_all_edges, get_node
from services.graph import get_communities_and_centrality, get_sector_gaps, get_enhanced_metrics
from services.claude import generate_session_prep

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/communities")
def communities():
    """Community detection + super-connector centrality for the graph overlay."""
    nodes = get_all_nodes()
    edges = get_all_edges()
    visible_edges = [e for e in edges if e.get("status") not in ("archived",)]
    return get_communities_and_centrality(nodes, visible_edges)


@router.get("/sector-gaps")
def sector_gaps():
    """Sectors ranked by mentor shortage relative to company demand."""
    nodes = get_all_nodes()
    return {"gaps": get_sector_gaps(nodes)}


@router.get("/health")
def health_scorecard():
    """Extended metrics for the ecosystem health scorecard."""
    nodes = get_all_nodes()
    edges = get_all_edges()
    return get_enhanced_metrics(nodes, edges)


class SessionPrepRequest(BaseModel):
    mentor_id: str
    company_id: str


@router.post("/session-prep")
def session_prep(req: SessionPrepRequest):
    """Generate a Claude-powered pre-session preparation card."""
    mentor = get_node(req.mentor_id)
    company = get_node(req.company_id)
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor '{req.mentor_id}' not found")
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{req.company_id}' not found")
    return generate_session_prep(mentor, company)


@router.get("/outcome-attribution/{company_id}")
def outcome_attribution(company_id: str):
    """
    For a given company, return all mentors who had active/completed linkages
    and their contribution — used to attribute outcomes to mentoring relationships.
    """
    nodes = get_all_nodes()
    edges = get_all_edges()
    nodes_map = {n["id"]: n for n in nodes}

    if company_id not in nodes_map:
        raise HTTPException(status_code=404, detail="Company not found")

    mentor_edges = [
        e for e in edges
        if e.get("target") == company_id and e.get("type") == "MENTORS"
    ]

    attributions = []
    for e in mentor_edges:
        mentor = nodes_map.get(e.get("source", ""))
        if not mentor:
            continue
        attributions.append({
            "mentor_id": mentor["id"],
            "mentor_name": mentor.get("name", mentor["id"]),
            "mentor_sectors": mentor.get("sectors", []),
            "mentor_expertise": mentor.get("expertise_tags", []),
            "status": e.get("status"),
            "sessions_completed": e.get("sessions_completed") or 0,
            "outcome_rating": e.get("outcome_rating"),
            "fit_score": e.get("fit_score"),
            "programme": e.get("programme"),
            "created_at": e.get("created_at"),
        })

    attributions.sort(key=lambda x: (x["outcome_rating"] or 0), reverse=True)
    return {
        "company_id": company_id,
        "company_name": nodes_map[company_id].get("name", company_id),
        "mentor_contributions": attributions,
        "total_sessions": sum(a["sessions_completed"] for a in attributions),
        "avg_outcome": round(
            sum(a["outcome_rating"] for a in attributions if a["outcome_rating"] is not None)
            / max(sum(1 for a in attributions if a["outcome_rating"] is not None), 1),
            2,
        ),
    }
