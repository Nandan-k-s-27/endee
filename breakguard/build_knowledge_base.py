"""
BreakGuard - Build Knowledge Base
Loads API documentation, generates embeddings, and stores them in Endee.
"""

import json
import os
import sys

from endee import Endee, Precision
from embeddings.embedding_engine import EmbeddingEngine


# ─── Configuration ──────────────────────────────────────────────
ENDEE_BASE_URL = os.getenv("ENDEE_URL", "http://localhost:8080/api/v1")


def get_auth_token() -> str:
    """Return the auth token from supported environment variables."""
    return os.getenv("ENDEE_AUTH_TOKEN") or os.getenv("NDD_AUTH_TOKEN", "")


ENDEE_AUTH_TOKEN = get_auth_token()
INDEX_NAME = "api_versions"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_api_data(filepath: str) -> list:
    """Load API data from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_knowledge_base():
    """
    Main function to build the API knowledge base.

    1. Initializes Endee client
    2. Creates the vector index
    3. Loads React 17 & 18 API data
    4. Generates embeddings for each API
    5. Upserts vectors into Endee
    """
    print("=" * 60)
    print("  BreakGuard - Building API Knowledge Base")
    print("=" * 60)

    # ─── Step 1: Initialize Endee client ────────────────────────
    print("\n[1/5] Connecting to Endee server...")
    if ENDEE_AUTH_TOKEN:
        client = Endee(ENDEE_AUTH_TOKEN)
    else:
        client = Endee()
    client.set_base_url(ENDEE_BASE_URL)
    print(f"  Connected to: {ENDEE_BASE_URL}")

    # ─── Step 2: Initialize Embedding Engine ────────────────────
    print("\n[2/5] Initializing embedding engine...")
    engine = EmbeddingEngine()
    dimension = engine.dimension

    # ─── Step 3: Create or recreate index ───────────────────────
    print(f"\n[3/5] Creating index '{INDEX_NAME}' (dimension={dimension})...")
    try:
        existing = client.list_indexes()
        if INDEX_NAME in existing:
            print(f"  Index '{INDEX_NAME}' already exists. Deleting...")
            client.delete_index(INDEX_NAME)
            print(f"  Deleted.")
    except Exception as e:
        print(f"  Note: Could not check existing indexes: {e}")

    client.create_index(
        name=INDEX_NAME,
        dimension=dimension,
        space_type="cosine",
        precision=Precision.FLOAT32,
    )
    print(f"  Index '{INDEX_NAME}' created successfully.")

    index = client.get_index(name=INDEX_NAME)

    # ─── Step 4: Load and process API data ──────────────────────
    api_files = {
        "react17": os.path.join(DATA_DIR, "react17_api.json"),
        "react18": os.path.join(DATA_DIR, "react18_api.json"),
    }

    total_stored = 0

    for version_key, filepath in api_files.items():
        print(f"\n[4/5] Processing {version_key}...")

        if not os.path.exists(filepath):
            print(f"  WARNING: File not found: {filepath}")
            continue

        apis = load_api_data(filepath)
        print(f"  Loaded {len(apis)} API entries.")

        # Generate embeddings for all APIs
        texts = [engine.api_to_text(api) for api in apis]
        vectors = engine.encode_batch(texts)

        # Prepare upsert data
        upsert_data = []
        for api, vector in zip(apis, vectors):
            version = api.get("version", version_key.replace("react", ""))
            func_name = api["function"]

            # Create a clean ID
            safe_name = func_name.replace(".", "_").replace(" ", "_")
            vector_id = f"react{version}_{safe_name}"

            # Build metadata
            meta = {
                "library": "react",
                "version": version,
                "function": func_name,
                "signature": api.get("signature", ""),
                "description": api.get("description", ""),
                "category": api.get("category", ""),
                "deprecated": api.get("deprecated", False),
            }

            # Add replacement info if available
            if api.get("replaces"):
                meta["replaces"] = api["replaces"]
            if api.get("replacedBy"):
                meta["replacedBy"] = api["replacedBy"]
            if api.get("migrateTo"):
                meta["migrateTo"] = api["migrateTo"]
            if api.get("importPath"):
                meta["importPath"] = api["importPath"]

            # Build filter for Endee queries
            # Encode version as integer for $eq filter
            version_num = int(version)
            filter_data = {
                "library": "react",
                "version": version_num,
            }

            upsert_data.append(
                {
                    "id": vector_id,
                    "vector": vector,
                    "meta": meta,
                    "filter": filter_data,
                }
            )

        # Upsert in batches
        batch_size = 50
        for i in range(0, len(upsert_data), batch_size):
            batch = upsert_data[i : i + batch_size]
            index.upsert(batch)
            print(f"  Upserted batch {i // batch_size + 1}: {len(batch)} vectors")

        total_stored += len(upsert_data)
        print(f"  Stored {len(upsert_data)} vectors for {version_key}")

    # ─── Step 5: Verify ─────────────────────────────────────────
    print(f"\n[5/5] Verification...")
    info = index.describe()
    print(f"  Index info: {info}")
    print(f"\n  Total vectors stored: {total_stored}")
    print("\n" + "=" * 60)
    print("  Knowledge base built successfully!")
    print("=" * 60)


if __name__ == "__main__":
    build_knowledge_base()
