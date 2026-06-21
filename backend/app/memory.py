import json
import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

CHROMA_DIR = Path(__file__).resolve().parents[1] / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_client: Optional[chromadb.Client] = None


def _get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection(novel_id: str, embedding_function=None):
    client = _get_client()
    collection_name = f"novel_{novel_id}"
    try:
        return client.get_collection(name=collection_name, embedding_function=embedding_function)
    except Exception:
        return client.create_collection(name=collection_name, embedding_function=embedding_function)


def embed_section(novel_id: str, section_id: str, section_title: str, content: str):
    if len(content.strip()) < 50:
        return
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        embedding = model.encode(content).tolist()
        collection = _get_collection(novel_id)
        collection.upsert(
            ids=[section_id],
            embeddings=[embedding],
            metadatas=[{"title": section_title, "novel_id": novel_id}],
            documents=[content],
        )
    except Exception:
        pass


def search_sections(novel_id: str, query: str, top_k: int = 3) -> list[dict]:
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        query_emb = model.encode(query).tolist()
        collection = _get_collection(novel_id)
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, count),
        )
        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                doc = results["documents"][0][i] if results["documents"] else ""
                dist = results["distances"][0][i] if results["distances"] else 0
                output.append({
                    "id": doc_id,
                    "title": meta.get("title", ""),
                    "content": doc,
                    "score": 1.0 - dist,
                })
        return output
    except (ImportError, Exception):
        return []


def delete_novel_sections(novel_id: str):
    try:
        client = _get_client()
        collection_name = f"novel_{novel_id}"
        client.delete_collection(name=collection_name)
    except ValueError:
        pass
