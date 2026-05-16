"""
Run once: python seed.py
Seeds Firestore with realistic Malaysian/SEA ecosystem actors,
generates Vertex AI embeddings (with graceful fallback), writes lat/lng for Maps.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from services.firestore import upsert_node, upsert_edge
from services.vertex import embed_actor

NODES = [
    # ── 8 Mentors ────────────────────────────────────────────────────────────
    {
        "id": "mentor_ahmad", "type": "mentor", "name": "Ahmad Razif",
        "sectors": ["fintech", "b2b"], "expertise_tags": ["fundraising", "product-market-fit"],
        "country": "MY", "city": "Kuala Lumpur", "lat": 3.1390, "lng": 101.6869,
        "bio": "10 years in fintech, ex-Grab, angel investor",
    },
    {
        "id": "mentor_priya", "type": "mentor", "name": "Priya Sundaram",
        "sectors": ["deeptech", "hardware"], "expertise_tags": ["R&D", "IP strategy", "grants"],
        "country": "MY", "city": "Cyberjaya", "lat": 2.9225, "lng": 101.6496,
        "bio": "Ex-MIMOS, deeptech commercialisation specialist",
    },
    {
        "id": "mentor_wei", "type": "mentor", "name": "Wei Liang Tan",
        "sectors": ["edtech", "saas"], "expertise_tags": ["growth", "SEA expansion", "B2C"],
        "country": "MY", "city": "Penang", "lat": 5.4141, "lng": 100.3288,
        "bio": "Founded two edtech companies, one acquired by Coursera partner",
    },
    {
        "id": "mentor_siti", "type": "mentor", "name": "Siti Rahimah",
        "sectors": ["healthtech", "medtech"], "expertise_tags": ["regulatory", "MOH", "clinical"],
        "country": "MY", "city": "Kuala Lumpur", "lat": 3.1478, "lng": 101.7057,
        "bio": "15 years in healthcare, ex-KKM policy advisor",
    },
    {
        "id": "mentor_rajesh", "type": "mentor", "name": "Rajesh Nair",
        "sectors": ["agritech", "sustainability"], "expertise_tags": ["supply chain", "rural tech"],
        "country": "MY", "city": "Johor Bahru", "lat": 1.4927, "lng": 103.7414,
        "bio": "Led agritech programmes across MY and ID",
    },
    {
        "id": "mentor_farhana", "type": "mentor", "name": "Farhana Zulkifli",
        "sectors": ["fintech", "islamic-finance"], "expertise_tags": ["compliance", "waqf tech"],
        "country": "MY", "city": "Kuala Lumpur", "lat": 3.1319, "lng": 101.6841,
        "bio": "Shariah-compliant fintech pioneer, ex-Bank Negara",
    },
    {
        "id": "mentor_david", "type": "mentor", "name": "David Loh",
        "sectors": ["logistics", "ecommerce"], "expertise_tags": ["last-mile", "operations"],
        "country": "MY", "city": "Petaling Jaya", "lat": 3.1073, "lng": 101.6067,
        "bio": "Scaled logistics ops for Lazada MY, advisor to 6 startups",
    },
    {
        "id": "mentor_nurul", "type": "mentor", "name": "Nurul Ain Hassan",
        "sectors": ["saas", "hrtech"], "expertise_tags": ["enterprise sales", "SEA GTM"],
        "country": "MY", "city": "Kuala Lumpur", "lat": 3.1580, "lng": 101.7120,
        "bio": "VP Sales ex-WorkplaceAI, closed Fortune 500 accounts in SEA",
    },
    # ── 10 Companies ─────────────────────────────────────────────────────────
    {
        "id": "company_payflow", "type": "company", "name": "PayFlow",
        "sectors": ["fintech"], "expertise_tags": ["payment", "SME", "B2B"],
        "stage": "seed", "country": "MY", "city": "Kuala Lumpur", "lat": 3.1569, "lng": 101.7123,
        "description": "B2B payment infrastructure for SMEs",
    },
    {
        "id": "company_agrovision", "type": "company", "name": "AgroVision",
        "sectors": ["agritech"], "expertise_tags": ["IoT", "crop monitoring", "rural"],
        "stage": "pre-seed", "country": "MY", "city": "Johor Bahru", "lat": 1.5000, "lng": 103.7500,
        "description": "IoT crop monitoring for smallholder farmers",
    },
    {
        "id": "company_medlink", "type": "company", "name": "MedLink",
        "sectors": ["healthtech"], "expertise_tags": ["telemedicine", "clinic", "rural health"],
        "stage": "seed", "country": "MY", "city": "Kuala Lumpur", "lat": 3.1200, "lng": 101.6700,
        "description": "Telemedicine platform for rural clinics",
    },
    {
        "id": "company_skillup", "type": "company", "name": "SkillUp",
        "sectors": ["edtech"], "expertise_tags": ["upskilling", "B2B", "LMS"],
        "stage": "series-a", "country": "MY", "city": "Penang", "lat": 5.4200, "lng": 100.3300,
        "description": "Corporate LMS and upskilling platform",
    },
    {
        "id": "company_halalpay", "type": "company", "name": "HalalPay",
        "sectors": ["fintech", "islamic-finance"], "expertise_tags": ["shariah", "e-wallet"],
        "stage": "seed", "country": "MY", "city": "Kuala Lumpur", "lat": 3.1400, "lng": 101.6900,
        "description": "Shariah-compliant digital wallet",
    },
    {
        "id": "company_logiq", "type": "company", "name": "LogiQ",
        "sectors": ["logistics"], "expertise_tags": ["last-mile", "B2B", "fleet"],
        "stage": "pre-seed", "country": "MY", "city": "Petaling Jaya", "lat": 3.1000, "lng": 101.6100,
        "description": "Fleet management SaaS for logistics SMEs",
    },
    {
        "id": "company_farmchain", "type": "company", "name": "FarmChain",
        "sectors": ["agritech", "sustainability"], "expertise_tags": ["supply chain", "blockchain"],
        "stage": "pre-seed", "country": "MY", "city": "Johor Bahru", "lat": 1.4800, "lng": 103.7300,
        "description": "Blockchain-based agri supply chain traceability",
    },
    {
        "id": "company_nurseai", "type": "company", "name": "NurseAI",
        "sectors": ["healthtech", "medtech"], "expertise_tags": ["AI diagnostics", "nursing"],
        "stage": "pre-seed", "country": "MY", "city": "Cyberjaya", "lat": 2.9300, "lng": 101.6500,
        "description": "AI-assisted clinical documentation for nurses",
    },
    {
        "id": "company_hirex", "type": "company", "name": "HireX",
        "sectors": ["hrtech", "saas"], "expertise_tags": ["recruitment", "AI screening"],
        "stage": "seed", "country": "MY", "city": "Kuala Lumpur", "lat": 3.1600, "lng": 101.7000,
        "description": "AI-powered recruitment platform for SEA",
    },
    {
        "id": "company_deeplearn", "type": "company", "name": "DeepLearn",
        "sectors": ["edtech", "deeptech"], "expertise_tags": ["adaptive learning", "AI tutor"],
        "stage": "pre-seed", "country": "MY", "city": "Penang", "lat": 5.4100, "lng": 100.3200,
        "description": "Adaptive AI tutoring for secondary school students",
    },
    # ── 3 Programmes ─────────────────────────────────────────────────────────
    {
        "id": "prog_cbip2025", "type": "programme", "name": "CBIP 2025",
        "sectors": [], "expertise_tags": [], "country": "MY",
        "city": "Kuala Lumpur", "lat": 3.1390, "lng": 101.6869,
        "description": "Cradle Business Improvement Programme 2025",
    },
    {
        "id": "prog_cbip2026", "type": "programme", "name": "CBIP 2026",
        "sectors": [], "expertise_tags": [], "country": "MY",
        "city": "Kuala Lumpur", "lat": 3.1395, "lng": 101.6875,
        "description": "Cradle Business Improvement Programme 2026",
    },
    {
        "id": "prog_catalyser", "type": "programme", "name": "CIP Catalyser",
        "sectors": [], "expertise_tags": [], "country": "MY",
        "city": "Kuala Lumpur", "lat": 3.1385, "lng": 101.6860,
        "description": "Cradle Investment Programme Catalyser",
    },
    # ── 2 Partners ───────────────────────────────────────────────────────────
    {
        "id": "partner_mdec", "type": "partner", "name": "MDEC",
        "sectors": [], "expertise_tags": ["digitalisation", "grants", "labs"],
        "country": "MY", "city": "Cyberjaya", "lat": 2.9225, "lng": 101.6496,
        "description": "Malaysia Digital Economy Corporation",
    },
    {
        "id": "partner_mdigital", "type": "partner", "name": "Malaysia Digital",
        "sectors": [], "expertise_tags": ["policy", "digital infrastructure"],
        "country": "MY", "city": "Putrajaya", "lat": 2.9264, "lng": 101.6964,
        "description": "National digital transformation agency",
    },
]

EDGES = [
    # MENTORS linkages with outcome history
    {"id": "e001", "source": "mentor_ahmad", "target": "company_payflow", "type": "MENTORS",
     "fit_score": 0.91, "sessions_completed": 8, "outcome_rating": 4.5,
     "programme": "prog_cbip2025", "status": "active", "reusable": True},
    {"id": "e002", "source": "mentor_ahmad", "target": "company_halalpay", "type": "MENTORS",
     "fit_score": 0.85, "sessions_completed": 6, "outcome_rating": 4.8,
     "programme": "prog_cbip2025", "status": "completed", "reusable": True},
    {"id": "e003", "source": "mentor_priya", "target": "company_nurseai", "type": "MENTORS",
     "fit_score": 0.78, "sessions_completed": 5, "outcome_rating": 3.9,
     "programme": "prog_catalyser", "status": "completed", "reusable": True},
    {"id": "e004", "source": "mentor_wei", "target": "company_skillup", "type": "MENTORS",
     "fit_score": 0.88, "sessions_completed": 10, "outcome_rating": 4.7,
     "programme": "prog_cbip2025", "status": "completed", "reusable": True},
    {"id": "e005", "source": "mentor_wei", "target": "company_deeplearn", "type": "MENTORS",
     "fit_score": 0.76, "sessions_completed": 4, "outcome_rating": 3.5,
     "programme": "prog_catalyser", "status": "active", "reusable": True},
    {"id": "e006", "source": "mentor_siti", "target": "company_medlink", "type": "MENTORS",
     "fit_score": 0.93, "sessions_completed": 12, "outcome_rating": 4.9,
     "programme": "prog_cbip2025", "status": "completed", "reusable": True},
    {"id": "e007", "source": "mentor_rajesh", "target": "company_agrovision", "type": "MENTORS",
     "fit_score": 0.87, "sessions_completed": 7, "outcome_rating": 4.3,
     "programme": "prog_cbip2025", "status": "active", "reusable": True},
    {"id": "e008", "source": "mentor_rajesh", "target": "company_farmchain", "type": "MENTORS",
     "fit_score": 0.81, "sessions_completed": 5, "outcome_rating": 4.0,
     "programme": "prog_catalyser", "status": "completed", "reusable": True},
    {"id": "e009", "source": "mentor_farhana", "target": "company_halalpay", "type": "MENTORS",
     "fit_score": 0.95, "sessions_completed": 9, "outcome_rating": 5.0,
     "programme": "prog_cbip2026", "status": "active", "reusable": True},
    {"id": "e010", "source": "mentor_david", "target": "company_logiq", "type": "MENTORS",
     "fit_score": 0.89, "sessions_completed": 6, "outcome_rating": 4.2,
     "programme": "prog_cbip2025", "status": "completed", "reusable": True},
    {"id": "e011", "source": "mentor_nurul", "target": "company_hirex", "type": "MENTORS",
     "fit_score": 0.84, "sessions_completed": 8, "outcome_rating": 4.6,
     "programme": "prog_cbip2026", "status": "active", "reusable": True},
    {"id": "e012", "source": "mentor_priya", "target": "company_deeplearn", "type": "MENTORS",
     "fit_score": 0.72, "sessions_completed": 3, "outcome_rating": 3.2,
     "programme": "prog_catalyser", "status": "completed", "reusable": False},
    # ENROLLED edges
    {"id": "e013", "source": "company_payflow", "target": "prog_cbip2025",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e014", "source": "company_skillup", "target": "prog_cbip2025",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e015", "source": "company_medlink", "target": "prog_cbip2025",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e016", "source": "company_agrovision", "target": "prog_cbip2025",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e017", "source": "company_halalpay", "target": "prog_cbip2026",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e018", "source": "company_hirex", "target": "prog_cbip2026",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e019", "source": "company_nurseai", "target": "prog_catalyser",
     "type": "ENROLLED", "status": "active", "reusable": False},
    {"id": "e020", "source": "company_farmchain", "target": "prog_catalyser",
     "type": "ENROLLED", "status": "active", "reusable": False},
    # SUPPORTS edges (partners → programmes)
    {"id": "e021", "source": "partner_mdec", "target": "prog_cbip2025",
     "type": "SUPPORTS", "status": "active", "reusable": True},
    {"id": "e022", "source": "partner_mdec", "target": "prog_cbip2026",
     "type": "SUPPORTS", "status": "active", "reusable": True},
    {"id": "e023", "source": "partner_mdigital", "target": "prog_catalyser",
     "type": "SUPPORTS", "status": "active", "reusable": True},
]


def seed():
    print("=" * 60)
    print("EcoLink AI — Firestore seeder")
    print("=" * 60)
    print(f"Seeding {len(NODES)} nodes and {len(EDGES)} edges...")
    print()

    for node in NODES:
        print(f"  [{node['type']:9s}] {node['name']} — embedding...", end=" ", flush=True)
        node["embedding"] = embed_actor(node)
        node["created_at"] = datetime.utcnow().isoformat()
        upsert_node(node)
        print("✓")

    print()
    print(f"  Writing {len(EDGES)} edges...", end=" ", flush=True)
    for edge in EDGES:
        edge["created_at"] = datetime.utcnow().isoformat()
        upsert_edge(edge)
    print("✓")

    print()
    print(f"Done. {len(NODES)} nodes, {len(EDGES)} edges written to Firestore.")
    print("You can now start the app: ./start.sh")


if __name__ == "__main__":
    seed()
