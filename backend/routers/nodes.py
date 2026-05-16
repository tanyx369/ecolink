from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import NodeCreate
from services.firestore import get_all_nodes, get_node, upsert_node
from services.vertex import embed_actor

router = APIRouter()


@router.get("/nodes")
def list_nodes():
    return get_all_nodes()


@router.get("/nodes/{node_id}")
def get_one_node(node_id: str):
    node = get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/nodes", status_code=201)
def create_node(payload: NodeCreate):
    existing = get_node(payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Node already exists")

    node = payload.model_dump()
    node["embedding"] = embed_actor(node)
    node["created_at"] = datetime.utcnow().isoformat()
    upsert_node(node)
    # Don't return the full 768-dim embedding in the response
    node_out = {k: v for k, v in node.items() if k != "embedding"}
    return node_out
