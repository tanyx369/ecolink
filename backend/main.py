import os
import traceback
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import nodes, edges, match, seed, insights
from services.graph import get_graph_data
from services.firestore import get_all_nodes, get_all_edges

app = FastAPI(title="EcoLink AI API", version="1.0.0")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"[ERROR] {request.method} {request.url}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router, tags=["nodes"])
app.include_router(edges.router, tags=["edges"])
app.include_router(match.router, tags=["match"])
app.include_router(seed.router, tags=["seed"])
app.include_router(insights.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "EcoLink AI"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/graph")
def graph_data():
    """Return the full ecosystem graph in react-force-graph-2d format."""
    nodes = get_all_nodes()
    edges = get_all_edges()
    visible_edges = [e for e in edges if e.get("status") not in ("archived",)]
    return get_graph_data(nodes, visible_edges)


@app.get("/metrics")
def metrics():
    """Dashboard summary metrics."""
    nodes = get_all_nodes()
    edges = get_all_edges()

    total_nodes = len(nodes)
    mentors = sum(1 for n in nodes if n.get("type") == "mentor")
    companies = sum(1 for n in nodes if n.get("type") == "company")
    programmes = sum(1 for n in nodes if n.get("type") == "programme")
    partners = sum(1 for n in nodes if n.get("type") == "partner")

    active_linkages = sum(1 for e in edges if e.get("status") == "active")
    completed_linkages = sum(1 for e in edges if e.get("status") == "completed")

    rated = [e.get("outcome_rating") for e in edges if e.get("outcome_rating") is not None]
    avg_outcome = round(sum(rated) / len(rated), 2) if rated else 0.0

    return {
        "total_nodes": total_nodes,
        "mentors": mentors,
        "companies": companies,
        "programmes": programmes,
        "partners": partners,
        "active_linkages": active_linkages,
        "completed_linkages": completed_linkages,
        "avg_outcome_rating": avg_outcome,
        "total_edges": len(edges),
    }
