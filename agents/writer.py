"""Nodo sink: escribe el research (notes + analysis) en ``outputs/{tema}.md``."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from langchain_core.messages import AIMessage

from agents.context import user_query
from config import BASE_DIR
from state import OrchestratorState

OUTPUTS_DIR = BASE_DIR / "outputs"

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def topic_slug(query: str, *, max_len: int = 60) -> str:
    """Slug de archivo para el tema de ``query``: NFKD → ascii → lower → hyphen."""
    normalized = unicodedata.normalize("NFKD", query or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _NON_ALNUM.sub("-", ascii_only.lower()).strip("-")
    slug = slug[:max_len].strip("-")
    return slug or "consulta"


def output_path_for(query: str) -> Path:
    return OUTPUTS_DIR / f"{topic_slug(query)}.md"


def render_brief(state: OrchestratorState) -> str:
    query = user_query(state.get("messages") or []) or "(sin consulta)"
    notes = (state.get("research_notes") or "").strip() or "(vacío)"
    analysis = (state.get("analysis") or "").strip() or "(vacío)"
    last_error = (state.get("last_error") or "").strip()
    parts = [
        "# Research",
        "",
        "## Consulta",
        "",
        query,
        "",
        "## research_notes",
        "",
        notes,
        "",
        "## analysis",
        "",
        analysis,
        "",
    ]
    if last_error:
        parts.extend(["## last_error", "", last_error, ""])
    return "\n".join(parts)


def writer_turn(state: OrchestratorState, path: Path) -> dict:
    path.write_text(render_brief(state), encoding="utf-8")
    return {
        "messages": [AIMessage(content=f"Research escrito en {path.name}", name="writer")],
        "last_agent": "writer",
    }


def make_writer_node(path: Path | None = None):
    def writer_node(state: OrchestratorState) -> dict:
        dest = path or output_path_for(user_query(state.get("messages") or []))
        dest.parent.mkdir(parents=True, exist_ok=True)
        result = writer_turn(state, dest)
        result["output_path"] = str(dest)
        return result

    return writer_node
