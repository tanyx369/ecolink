from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from models import MatchRequest, EdgeCreate
from services.firestore import get_all_nodes, get_all_edges, upsert_edge
from services.graph import get_mentor_candidates, serialise_subgraph, serialise_mentor_subgraph
from services.gemini import analyse_subgraph
from services.claude import stream_match_proposal

router = APIRouter()


@router.post("/match")
async def match(req: MatchRequest):
    nodes = get_all_nodes()
    edges = get_all_edges()

    nodes_map = {n["id"]: n for n in nodes}
    if req.company_id not in nodes_map:
        raise HTTPException(status_code=404, detail=f"Company '{req.company_id}' not found")

    candidates = get_mentor_candidates(nodes, edges, req.company_id)
    if not candidates:
        raise HTTPException(status_code=404, detail="No mentor candidates found")

    context = serialise_subgraph(nodes, edges, req.company_id, candidates)

    company_node = nodes_map[req.company_id]
    gemini_analyses = {}
    for c in candidates[:6]:
        mid = c["mentor"]["id"]
        mentor_ctx = serialise_mentor_subgraph(nodes, edges, company_node, c)
        gemini_analyses[mid] = analyse_subgraph(mentor_ctx, mid)

    return StreamingResponse(
        stream_match_proposal(context, gemini_analyses),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/match/approve")
def approve_match(mentor_id: str, company_id: str, programme_id: str, fit_score: float = 0.0):
    """Write a proposed edge to Firestore when admin approves a match."""
    edge_id = f"edge_{mentor_id}_{company_id}_{int(datetime.utcnow().timestamp())}"
    edge = EdgeCreate(
        id=edge_id,
        source=mentor_id,
        target=company_id,
        type="MENTORS",
        fit_score=fit_score,
        sessions_completed=0,
        programme=programme_id,
        status="active",
        reusable=True,
    )
    edge_dict = edge.model_dump()
    edge_dict["created_at"] = datetime.utcnow().isoformat()
    upsert_edge(edge_dict)
    return {"created": edge_id, "edge": edge_dict}
