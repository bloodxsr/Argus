from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"
TARGETS = [
    ROOT / "test-website" / "src" / "contracts.ts",
    ROOT / "report-website" / "src" / "contracts.ts",
]


def main() -> int:
    schemas = sorted(CONTRACTS.glob("*.schema.json"))
    output = [
        "/* Generated from contracts/*.schema.json. Do not edit by hand. */",
        "",
    ]
    for schema_path in schemas:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        output.append(render_type(schema))
        output.append("")

    text = "\n".join(output).rstrip() + "\n"
    for target in TARGETS:
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)}")
    return 0


def render_type(schema: dict) -> str:
    title = schema["title"]
    required = set(schema.get("required", ()))
    lines = [f"export type {title} = { "]
    for key, value in schema.get("properties", {}).items():
        optional = "" if key in required else "?"
        lines.append(f"  {key}{optional}: {ts_type(value)};")
    lines.append("};")
    return "\n".join(lines)


def ts_type(schema: dict) -> str:
    if "$ref" in schema:
        return ref_name(schema["$ref"])
    value = schema.get("type", "object")
    if isinstance(value, list):
        return " | ".join("null" if item == "null" else ts_type({"type": item}) for item in value)
    if value == "string":
        return "string"
    if value in {"number", "integer"}:
        return "number"
    if value == "boolean":
        return "boolean"
    if value == "array":
        return f"{ts_type(schema.get('items', {'type': 'object'}))}[]"
    if value == "object":
        props = schema.get("properties")
        if not props:
            return "Record<string, unknown>"
        required = set(schema.get("required", ()))
        inner = []
        for key, value in props.items():
            optional = "" if key in required else "?"
            inner.append(f"{key}{optional}: {ts_type(value)}")
        return "{ " + "; ".join(inner) + " }"
    return "unknown"


def ref_name(ref: str) -> str:
    filename = Path(ref).name
    schema = json.loads((CONTRACTS / filename).read_text(encoding="utf-8"))
    return schema["title"]


if __name__ == "__main__":
    raise SystemExit(main())
