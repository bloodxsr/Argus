"""Ingest a simplified MITRE techniques JSON into Qdrant via the retriever.

Accepts either:
- a JSON array of objects with {"id", "name", "description", "mitre_id"}
- a STIX bundle JSON (it will attempt to extract "name" and "description" fields)

If Qdrant or embedding model is not available, the script will fall back and print a message.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ai.core.retriever import QdrantRetriever
from ai.core.knowledge import KnowledgeSnippet


def load_items(path: Path) -> List[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items: List[dict] = []
    if isinstance(data, dict) and "objects" in data:
        # STIX bundle
        for obj in data["objects"]:
            t = obj.get("type")
            if t in ("attack-pattern", "course-of-action", "tool", "intrusion-set"):
                name = obj.get("name") or obj.get("title") or ""
                desc = obj.get("description") or obj.get("short_description") or ""
                mitre_ids = []
                for er in obj.get("external_references", []):
                    if isinstance(er, dict) and er.get("external_id"):
                        mitre_ids.append(er.get("external_id"))
                items.append({"name": name, "description": desc, "mitre_id": mitre_ids})
        # dedupe by name
        seen = set()
        unique = []
        for it in items:
            key = (it.get("name") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(it)
        return unique
    if isinstance(data, list):
        # assume list of simple items
        for obj in data:
            if isinstance(obj, dict) and (obj.get("name") or obj.get("title")):
                name = obj.get("name") or obj.get("title")
                desc = obj.get("description") or ""
                mitre = obj.get("mitre_id") or obj.get("mitre") or []
                items.append({"name": name, "description": desc, "mitre_id": mitre})
        return items
    return []


def to_snippets(items: List[dict]) -> List[KnowledgeSnippet]:
    out = []
    for it in items:
        title = it.get("name") or it.get("title") or "technique"
        summary = it.get("description") or ""
        mitre = tuple(it.get("mitre_id", ()))
        out.append(KnowledgeSnippet(title=title, summary=summary, markers=tuple(), mitre_techniques=mitre, recommended_action="recommend"))
    return out


def main(bundle_path: str) -> int:
    p = Path(bundle_path)
    if not p.exists():
        print("Bundle not found:", bundle_path)
        return 2
    items = load_items(p)
    snippets = to_snippets(items)
    retriever = QdrantRetriever()
    retriever.ingest_snippets(snippets)
    print(f"Attempted to ingest {len(snippets)} snippets (Qdrant may be unavailable).")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python train/ingest_mitre.py path/to/mitre.json")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
