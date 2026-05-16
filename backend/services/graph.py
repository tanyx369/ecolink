import networkx as nx
from services.vertex import cosine_similarity
from datetime import datetime, timedelta


def build_graph(nodes: list[dict], edges: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "embedding"})
    for e in edges:
        G.add_edge(e["source"], e["target"], **e)
    return G


def k_hop_neighbors(
    G: nx.DiGraph,
    start: str,
    k: int = 2,
    edge_types: list[str] | None = None,
) -> set[str]:
    visited: set[str] = set()
    frontier: set[str] = {start}
    for _ in range(k):
        next_f: set[str] = set()
        for node in frontier:
            for nb in G.neighbors(node):
                data = G[node][nb]
                if edge_types is None or data.get("type") in edge_types:
                    if nb not in visited and nb not in frontier:
                        next_f.add(nb)
        visited |= frontier
        frontier = next_f
    return visited | frontier


def get_mentor_candidates(
    nodes: list[dict], edges: list[dict], company_id: str
) -> list[dict]:
    nodes_map = {n["id"]: n for n in nodes}
    if company_id not in nodes_map:
        return []

    company = nodes_map[company_id]
    G = build_graph(nodes, edges)

    neighbor_ids = k_hop_neighbors(G, company_id, k=2)
    mentors = [
        nodes_map[nid]
        for nid in neighbor_ids
        if nid in nodes_map and nodes_map[nid].get("type") == "mentor"
    ]

    # Also include all mentors not yet in neighbors (cold start fallback)
    all_mentors = [n for n in nodes if n.get("type") == "mentor"]
    mentor_ids_in_result = {m["id"] for m in mentors}
    for m in all_mentors:
        if m["id"] not in mentor_ids_in_result:
            mentors.append(m)

    _STOPWORDS = {
        "the", "a", "an", "and", "or", "in", "of", "to", "for", "is", "are",
        "was", "with", "at", "by", "as", "on", "that", "this", "it", "be",
        "from", "have", "has", "had", "not", "he", "she", "we", "i", "his",
        "her", "their", "our", "been", "also", "who", "which", "will", "can",
    }

    def _bio_words(node: dict) -> set:
        text = (node.get("bio") or node.get("description", "")).lower()
        return {w.strip(".,;:()") for w in text.split() if len(w) > 2} - _STOPWORDS

    def _jaccard(a: set, b: set) -> float:
        return len(a & b) / max(len(a | b), 1)

    company_sectors = set(company.get("sectors", []))
    company_expertise = set(company.get("expertise_tags", []))
    company_bio_words = _bio_words(company)
    c_emb = company.get("embedding", [])

    results = []
    for mentor in mentors:
        # ── Sector match (same industry) ──────────────────────────────────────
        mentor_sectors = set(mentor.get("sectors", []))
        sector_overlap = _jaccard(company_sectors, mentor_sectors)

        # ── Expertise tag match (direct skill alignment) ─────────────────────
        mentor_expertise = set(mentor.get("expertise_tags", []))
        expertise_overlap = _jaccard(company_expertise, mentor_expertise)

        # ── Bio keyword match (background narrative overlap) ──────────────────
        mentor_bio_words = _bio_words(mentor)
        bio_overlap = _jaccard(company_bio_words, mentor_bio_words)

        # ── Vertex AI semantic similarity (may be fallback noise if unavailable)
        m_emb = mentor.get("embedding", [])
        semantic_score = cosine_similarity(c_emb, m_emb) if c_emb and m_emb else 0.0
        # Clamp negative cosine values to 0 (fallback embeddings can go negative)
        semantic_score = max(0.0, semantic_score)

        # ── Past outcome track record ─────────────────────────────────────────
        past_edges = [
            e
            for e in edges
            if e.get("source") == mentor["id"]
            and e.get("type") == "MENTORS"
            and e.get("outcome_rating") is not None
        ]
        avg_outcome = (
            sum(e["outcome_rating"] for e in past_edges) / len(past_edges)
            if past_edges
            else None
        )
        outcome_score = (avg_outcome or 3.5) / 5.0

        # ── Combined score — background/expertise-first weighting ─────────────
        # Sectors 30% + expertise tags 30% + bio keywords 15% + semantic 15% + track record 10%
        combined = (
            sector_overlap * 0.30
            + expertise_overlap * 0.30
            + bio_overlap * 0.15
            + semantic_score * 0.15
            + outcome_score * 0.10
        )

        results.append(
            {
                "mentor": mentor,
                "past_edges": past_edges,
                "avg_outcome": avg_outcome,
                "sector_overlap": sector_overlap,
                "expertise_overlap": expertise_overlap,
                "bio_overlap": bio_overlap,
                "semantic_score": semantic_score,
                "tag_overlap": expertise_overlap,   # kept for backwards compat with serialisers
                "combined_score": combined,
            }
        )

    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results[:6]


def serialise_subgraph(
    nodes: list[dict],
    edges: list[dict],
    company_id: str,
    candidates: list[dict],
) -> str:
    nodes_map = {n["id"]: n for n in nodes}
    company = nodes_map.get(company_id, {})

    company_bio = company.get("bio") or company.get("description", "")
    company_tags = ", ".join(company.get("expertise_tags", []))
    lines = [
        "TARGET COMPANY:",
        f"- Name: {company.get('name', '?')}",
        f"- Stage: {company.get('stage', '?')} | City: {company.get('city', '?')}",
        f"- Sectors: {', '.join(company.get('sectors', []))}",
        f"- Expertise / needs: {company_tags if company_tags else '(not specified)'}",
        f"- Description: {company_bio}",
        "",
        "CANDIDATE MENTORS:",
    ]

    for c in candidates:
        m = c["mentor"]
        mentor_bio = m.get("bio") or m.get("description", "")
        lines.append(f"\nMentor: {m['name']} (id: {m['id']})")
        lines.append(f"- City: {m.get('city', '?')} | Country: {m.get('country', '?')}")
        lines.append(f"- Sectors: {', '.join(m.get('sectors', []))}")
        lines.append(f"- Expertise tags: {', '.join(m.get('expertise_tags', []))}")
        lines.append(f"- Bio / background: {mentor_bio}")
        lines.append(f"- Sector overlap score: {c['sector_overlap']:.3f}  (same-industry match)")
        lines.append(f"- Expertise tag overlap: {c['expertise_overlap']:.3f}  (direct skill match)")
        lines.append(f"- Bio keyword overlap: {c['bio_overlap']:.3f}  (background narrative similarity)")
        lines.append(f"- Vertex AI semantic similarity: {c['semantic_score']:.3f}")
        lines.append(f"- Combined background score: {c['combined_score']:.3f}")
        if c["past_edges"]:
            lines.append(
                f"- Past mentoring: {len(c['past_edges'])} companies, "
                f"avg outcome {c['avg_outcome']:.1f}/5"
            )
            for e in c["past_edges"][:3]:
                target = nodes_map.get(e.get("target", ""), {})
                target_sectors = ", ".join(target.get("sectors", []))
                lines.append(
                    f"  · {target.get('name', '?')} [{target_sectors}] → "
                    f"outcome {e.get('outcome_rating', '?')}/5, "
                    f"{e.get('sessions_completed', '?')} sessions"
                )
        else:
            lines.append("- Past mentoring: none recorded in this ecosystem")

    return "\n".join(lines)


def serialise_mentor_subgraph(
    nodes: list[dict],
    edges: list[dict],
    company: dict,
    candidate: dict,
) -> str:
    """Focused single-mentor context for Gemini per-mentor analysis."""
    nodes_map = {n["id"]: n for n in nodes}
    m = candidate["mentor"]
    past_edges = candidate.get("past_edges", [])
    avg = candidate.get("avg_outcome")

    company_bio = company.get("bio") or company.get("description", "")
    mentor_bio = m.get("bio") or m.get("description", "")
    company_tags = ", ".join(company.get("expertise_tags", [])) or "(not specified)"
    lines = [
        "COMPANY SEEKING MENTORSHIP:",
        f"  Name: {company.get('name', '?')}",
        f"  Stage: {company.get('stage', '?')} | City: {company.get('city', '?')}",
        f"  Sectors: {', '.join(company.get('sectors', []))}",
        f"  Expertise / needs: {company_tags}",
        f"  Background: {company_bio}",
        "",
        "CANDIDATE MENTOR:",
        f"  Name: {m['name']} (id: {m['id']})",
        f"  City: {m.get('city', '?')} | Country: {m.get('country', '?')}",
        f"  Sectors: {', '.join(m.get('sectors', []))}",
        f"  Expertise tags: {', '.join(m.get('expertise_tags', []))}",
        f"  Bio / background: {mentor_bio}",
        "",
        "BACKGROUND & EXPERTISE MATCH SCORES:",
        f"  Sector overlap (same-industry match): {candidate['sector_overlap']:.3f}",
        f"  Expertise tag overlap (skill alignment): {candidate['expertise_overlap']:.3f}",
        f"  Bio keyword overlap (narrative similarity): {candidate['bio_overlap']:.3f}",
        f"  Vertex AI semantic similarity: {candidate['semantic_score']:.3f}",
        f"  Combined background score: {candidate['combined_score']:.3f}",
    ]

    if past_edges:
        lines.append(
            f"\nPAST MENTORING ({len(past_edges)} engagements"
            + (f", avg outcome {avg:.1f}/5" if avg is not None else "")
            + "):"
        )
        for e in past_edges[:4]:
            target = nodes_map.get(e.get("target", ""), {})
            lines.append(
                f"  · Mentored {target.get('name', '?')} → "
                f"outcome {e.get('outcome_rating', '?')}/5, "
                f"{e.get('sessions_completed', '?')} sessions"
            )
    else:
        lines.append("\nPAST MENTORING: None — first engagement in this ecosystem.")

    return "\n".join(lines)


def get_graph_data(nodes: list[dict], edges: list[dict]) -> dict:
    """Return nodes + links in react-force-graph-2d format with full metadata."""
    graph_nodes = [
        {
            "id": n["id"],
            "name": n.get("name", n["id"]),
            "type": n.get("type", "unknown"),
            "city": n.get("city", ""),
            "country": n.get("country", "MY"),
            "sectors": n.get("sectors", []),
            "expertise_tags": n.get("expertise_tags", []),
            "bio": n.get("bio") or n.get("description", ""),
            "stage": n.get("stage"),
        }
        for n in nodes
    ]
    graph_links = [
        {
            "id": e.get("id", ""),
            "source": e["source"],
            "target": e["target"],
            "type": e.get("type", ""),
            "status": e.get("status", ""),
            "fit_score": e.get("fit_score"),
            "sessions_completed": e.get("sessions_completed"),
            "outcome_rating": e.get("outcome_rating"),
            "programme": e.get("programme"),
        }
        for e in edges
        if e.get("source") and e.get("target")
    ]
    return {"nodes": graph_nodes, "links": graph_links}


def get_communities_and_centrality(nodes: list[dict], edges: list[dict]) -> dict:
    """Detect communities and identify super-connector nodes."""
    G = build_graph(nodes, edges)
    if len(G.nodes) == 0:
        return {"communities": {}, "centrality": {}, "super_connectors": [], "community_count": 0}

    undirected = G.to_undirected()

    # Community detection — try Louvain first (NetworkX 3+), fall back to greedy modularity
    try:
        from networkx.algorithms.community import louvain_communities
        communities_list = louvain_communities(undirected, seed=42)
    except Exception:
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities_list = list(greedy_modularity_communities(undirected))
        except Exception:
            communities_list = [{n} for n in undirected.nodes]

    community_map: dict[str, int] = {}
    for i, comm in enumerate(communities_list):
        for node_id in comm:
            community_map[str(node_id)] = i

    # Betweenness centrality — how often each node sits on shortest paths
    centrality = nx.betweenness_centrality(undirected, normalized=True)
    centrality_str = {str(k): round(v, 4) for k, v in centrality.items()}

    # Super-connectors: nodes in the top 15% by centrality with a minimum threshold
    if centrality:
        sorted_scores = sorted(centrality.values(), reverse=True)
        cutoff_idx = max(0, int(len(sorted_scores) * 0.15) - 1)
        threshold = max(0.05, sorted_scores[cutoff_idx])
        super_connectors = [str(nid) for nid, score in centrality.items() if score >= threshold]
    else:
        super_connectors = []

    return {
        "communities": community_map,
        "centrality": centrality_str,
        "super_connectors": super_connectors,
        "community_count": len(communities_list),
    }


def get_sector_gaps(nodes: list[dict]) -> list[dict]:
    """Return sectors ranked by mentor shortage relative to company demand."""
    mentor_count: dict[str, int] = {}
    company_count: dict[str, int] = {}
    for n in nodes:
        for s in n.get("sectors", []):
            if n.get("type") == "mentor":
                mentor_count[s] = mentor_count.get(s, 0) + 1
            elif n.get("type") == "company":
                company_count[s] = company_count.get(s, 0) + 1

    all_sectors = set(mentor_count) | set(company_count)
    gaps = []
    for sector in all_sectors:
        m = mentor_count.get(sector, 0)
        c = company_count.get(sector, 0)
        ratio = m / max(c, 1)
        status = "critical" if ratio < 0.3 else "low" if ratio < 0.7 else "balanced" if ratio < 1.5 else "surplus"
        gaps.append({"sector": sector, "mentors": m, "companies": c, "ratio": round(ratio, 2), "status": status})

    gaps.sort(key=lambda x: x["ratio"])
    return gaps


def get_enhanced_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    """Enriched metrics for the health scorecard."""
    mentors = [n for n in nodes if n.get("type") == "mentor"]
    companies = [n for n in nodes if n.get("type") == "company"]
    mentoring_edges = [e for e in edges if e.get("type") == "MENTORS" and e.get("status") not in ("archived",)]

    # Companies with at least one active or completed linkage
    linked_companies = {e["target"] for e in mentoring_edges if e.get("status") in ("active", "completed")}
    pct_companies_linked = round(len(linked_companies) / max(len(companies), 1) * 100, 1)

    # Mentor-to-company ratio
    mentor_company_ratio = round(len(mentors) / max(len(companies), 1), 2)

    # Unique sector count (ecosystem diversity)
    all_sectors: set[str] = set()
    for n in nodes:
        all_sectors.update(n.get("sectors", []))
    sector_diversity = len(all_sectors)

    # Linkages created in the last 30 days
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    new_this_month = sum(1 for e in mentoring_edges if (e.get("created_at") or "") >= cutoff)

    # Average sessions per active linkage
    active = [e for e in mentoring_edges if e.get("status") == "active"]
    avg_sessions = round(
        sum(e.get("sessions_completed") or 0 for e in active) / max(len(active), 1), 1
    )

    # Outcome trend: last 5 rated linkages
    rated = sorted(
        [e for e in mentoring_edges if e.get("outcome_rating") is not None],
        key=lambda e: e.get("created_at") or "",
        reverse=True,
    )[:5]
    recent_avg = round(sum(e["outcome_rating"] for e in rated) / max(len(rated), 1), 2) if rated else 0.0

    return {
        "pct_companies_linked": pct_companies_linked,
        "mentor_company_ratio": mentor_company_ratio,
        "sector_diversity": sector_diversity,
        "new_linkages_this_month": new_this_month,
        "avg_sessions_per_active": avg_sessions,
        "recent_avg_outcome": recent_avg,
        "sector_gaps": get_sector_gaps(nodes),
    }
