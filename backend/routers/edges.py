from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import EdgeCreate, EdgePatch
from services.firestore import get_all_edges, upsert_edge, patch_edge, delete_edge

router = APIRouter()


@router.get("/edges")
def list_edges():
    return get_all_edges()


@router.post("/edges", status_code=201)
def create_edge(payload: EdgeCreate):
    edge = payload.model_dump()
    edge["created_at"] = datetime.utcnow().isoformat()
    upsert_edge(edge)
    return edge


@router.patch("/edges/{edge_id}")
def update_edge(edge_id: str, payload: EdgePatch):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow().isoformat()
    patch_edge(edge_id, updates)
    return {"id": edge_id, **updates}


@router.delete("/edges/{edge_id}", status_code=204)
def remove_edge(edge_id: str):
    """Permanently delete an edge from Firestore."""
    delete_edge(edge_id)


@router.post("/edges/{edge_id}/clone")
def clone_edge(edge_id: str, programme_id: str):
    """Clone a completed linkage to a new programme."""
    edges = get_all_edges()
    original = next((e for e in edges if e["id"] == edge_id), None)
    if original is None:
        raise HTTPException(status_code=404, detail="Edge not found")

    new_edge = {**original}
    new_edge["id"] = f"{edge_id}_clone_{programme_id}"
    new_edge["programme"] = programme_id
    new_edge["status"] = "proposed"
    new_edge["sessions_completed"] = 0
    new_edge["outcome_rating"] = None
    new_edge["created_at"] = datetime.utcnow().isoformat()
    upsert_edge(new_edge)
    return new_edge
