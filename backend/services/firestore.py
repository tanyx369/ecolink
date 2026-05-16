import os
from google.cloud import firestore as gfs
from google.oauth2 import service_account

_client = None


def _db() -> gfs.Client:
    global _client
    if _client is not None:
        return _client

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./service-account.json")
    project = (
        os.environ.get("FIREBASE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )
    database = os.environ.get("FIRESTORE_DATABASE_ID", "(default)")

    credentials = service_account.Credentials.from_service_account_file(
        cred_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    _client = gfs.Client(project=project, credentials=credentials, database=database)
    print(f"[Firestore] Connected → project={project}, database={database}")
    return _client


def get_all_nodes() -> list[dict]:
    try:
        return [doc.to_dict() for doc in _db().collection("nodes").stream()]
    except Exception as e:
        print(f"[Firestore] get_all_nodes error: {e}")
        return []


def get_all_edges() -> list[dict]:
    try:
        return [doc.to_dict() for doc in _db().collection("edges").stream()]
    except Exception as e:
        print(f"[Firestore] get_all_edges error: {e}")
        return []


def get_node(node_id: str) -> dict | None:
    try:
        doc = _db().collection("nodes").document(node_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"[Firestore] get_node error: {e}")
        return None


def upsert_node(node: dict):
    try:
        _db().collection("nodes").document(node["id"]).set(node)
    except Exception as e:
        print(f"[Firestore] upsert_node error: {e}")
        raise


def upsert_edge(edge: dict):
    try:
        _db().collection("edges").document(edge["id"]).set(edge)
    except Exception as e:
        print(f"[Firestore] upsert_edge error: {e}")
        raise


def patch_edge(edge_id: str, patch: dict):
    try:
        _db().collection("edges").document(edge_id).update(patch)
    except Exception as e:
        print(f"[Firestore] patch_edge error: {e}")
        raise


def delete_edge(edge_id: str):
    try:
        _db().collection("edges").document(edge_id).delete()
    except Exception as e:
        print(f"[Firestore] delete_edge error: {e}")
        raise
