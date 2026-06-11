from __future__ import annotations

import argparse
from typing import Optional, Any

try:
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - optional deps
    QdrantClient = None  # type: ignore


def connect_client(host: str, port: int) -> Any:
    if QdrantClient is None:
        print("qdrant-client not installed; CLI commands are no-ops")
        return None
    try:
        return QdrantClient(host=host, port=port)
    except Exception as e:
        print("Failed to connect to Qdrant:", e)
        return None


def create_collection(client: Any, name: str) -> None:
    if client is None:
        return
    try:
        client.recreate_collection(collection_name=name, vectors_config={"size": 384, "distance": "Cosine"})
        print("Created or recreated collection:", name)
    except Exception as e:
        print("Error creating collection:", e)


def delete_collection(client: Any, name: str) -> None:
    if client is None:
        return
    try:
        client.delete_collection(collection_name=name)
        print("Deleted collection:", name)
    except Exception as e:
        print("Error deleting collection:", e)


def list_collections(client: Any) -> None:
    if client is None:
        return
    try:
        cols = client.get_collections()
        print(cols)
    except Exception as e:
        print("Error listing collections:", e)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=6333)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    c = sub.add_parser("create")
    c.add_argument("name")
    d = sub.add_parser("delete")
    d.add_argument("name")
    args = p.parse_args(argv)

    client = connect_client(args.host, args.port)
    if args.cmd == "list":
        list_collections(client)
    elif args.cmd == "create":
        create_collection(client, args.name)
    elif args.cmd == "delete":
        delete_collection(client, args.name)
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
