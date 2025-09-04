# renderer.py
from __future__ import annotations
from typing import Dict

def render_template(template: str, mapping: Dict[str, str]) -> str:
    """Substitui {{PLACEHOLDER}} por valores em mapping. Ausentes viram '—'."""
    out = template
    for k, v in mapping.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    # placeholders não preenchidos -> traço
    import re
    out = re.sub(r"\{\{[A-Z0-9_]+\}\}", "—", out)
    return out
