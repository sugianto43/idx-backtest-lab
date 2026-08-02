import hashlib
import json
from typing import Any


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def compute_checksum(data: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(data)).hexdigest()
