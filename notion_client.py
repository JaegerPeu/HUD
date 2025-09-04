# notion_client.py
from __future__ import annotations
from typing import Tuple, Optional
import requests
import json

NOTION_VERSION = "2022-06-28"

def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

def _normalize_id(i: str) -> str:
    return (i or "").replace("-", "").strip()

def push_code_block(block_id: str, content: str, token: str) -> Tuple[bool, str]:
    """Atualiza um code block existente (PATCH /v1/blocks/{id})."""
    try:
        payload = {
            "code": {
                "rich_text": [{"type":"text","text":{"content": content}}],
                "language": "plain text"
            }
        }
        url = f"https://api.notion.com/v1/blocks/{_normalize_id(block_id)}"
        r = requests.patch(url, headers=_headers(token), data=json.dumps(payload), timeout=30)
        if r.status_code == 200:
            return True, "Atualizado!"
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)
