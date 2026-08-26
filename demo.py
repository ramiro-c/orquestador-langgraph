"""Demo del orquestador jerárquico (pre-entrega 6).

CLI:
    python demo.py          # REPL: una consulta por turno, 'salir' para terminar
    python demo.py --trace  # mismo REPL + hops, traces/ y output.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TRACES_DIR = Path(__file__).resolve().parent / "traces"

TRACE_QUERY = (
    "¿Qué se dice esta semana de LangGraph frente a CrewAI para equipos chicos, "
    "y cuál es el sentimiento general?"
)

_COMANDOS_SALIDA = {"salir", "exit", "quit", "q", "s"}


def _content_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for block in content:
            if isinstance(block, str):
                partes.append(block)
            elif isinstance(block, dict) and block.get("text"):
                partes.append(str(block["text"]))
        return "\n".join(partes)
    return str(content)


def _verificar_credenciales() -> None:
    """Falla con mensaje claro antes de pegarle a la red."""
    from config import (
        GEMINI_API_KEY,
        GOOGLE_APPLICATION_CREDENTIALS,
        GOOGLE_CLOUD_LOCATION,
        GOOGLE_CLOUD_PROJECT,
        LLM_PROVIDER,
        OPENROUTER_API_KEY,
        TAVILY_API_KEY,
    )

    faltantes: list[str] = []
    if not TAVILY_API_KEY:
        faltantes.append("TAVILY_API_KEY")
    if LLM_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        faltantes.append("OPENROUTER_API_KEY")
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        if not GOOGLE_APPLICATION_CREDENTIALS:
            faltantes.append("GOOGLE_APPLICATION_CREDENTIALS")
        elif not Path(GOOGLE_APPLICATION_CREDENTIALS).is_file():
            faltantes.append(
                "GOOGLE_APPLICATION_CREDENTIALS (el archivo del service account no existe)"
            )
        if not GOOGLE_CLOUD_PROJECT:
            faltantes.append("GOOGLE_CLOUD_PROJECT")
        if not GOOGLE_CLOUD_LOCATION:
            faltantes.append("GOOGLE_CLOUD_LOCATION")
    if faltantes:
        raise SystemExit(
            "No se puede correr la demo: faltan "
            + ", ".join(faltantes)
            + ". Completá pre-entrega-6/.env (ver .env.example)."
        )


def _imprimir_resultado(hops: list[str], result: dict) -> None:
    print("\n--- Delegación ---")
    print(" → ".join(hops) if hops else "(sin hops)")
    if result.get("last_error"):
        print("\n--- last_error ---")
        print(result["last_error"])
    print("\n--- research_notes ---")
    print(result.get("research_notes") or "(vacío)")
    print("\n--- analysis ---")
    print(result.get("analysis") or "(vacío)")
    last = result["messages"][-1] if result.get("messages") else None
    print("\n--- Último mensaje ---")
    print(_content_str(getattr(last, "content", last)))
    if result.get("last_agent") == "writer":
        from agents.writer import OUTPUT_PATH

        print(f"\nBrief escrito en {OUTPUT_PATH}")


def _guardar_trazas(query: str, hops: list[str], result: dict) -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "hops": hops,
        "next_agent": result.get("next_agent"),
        "step_count": result.get("step_count"),
        "last_agent": result.get("last_agent"),
        "last_error": result.get("last_error") or "",
        "research_notes": result.get("research_notes") or "",
        "analysis": result.get("analysis") or "",
        "messages": [
            {
                "type": getattr(m, "type", "?"),
                "name": getattr(m, "name", None),
                "content": _content_str(getattr(m, "content", "")),
            }
            for m in result.get("messages") or []
        ],
    }
    json_path = TRACES_DIR / "delegation.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log_path = TRACES_DIR / "delegation.log"
    lines = [
        f"Consulta: {query}",
        f"Delegación: {' → '.join(hops)}",
        f"step_count={result.get('step_count')} next_agent={result.get('next_agent')}",
        f"last_error={payload['last_error'] or '(ninguno)'}",
        "",
        "=== research_notes ===",
        payload["research_notes"],
        "",
        "=== analysis ===",
        payload["analysis"],
    ]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nTrazas guardadas en {json_path} y {log_path}")


def _correr(graph, query: str, *, guardar: bool, echo_query: bool = True) -> None:
    from graph import stream_query

    if echo_query:
        print(f"\nConsulta: {query}\n")
    hops, result = stream_query(
        graph, query, on_hop=lambda node: print(f"→ {node}", flush=True)
    )
    _imprimir_resultado(hops, result)
    if guardar:
        _guardar_trazas(query, hops, result)


def _repl(graph, *, guardar: bool) -> int:
    if guardar:
        print(
            "Demo orquestador pre-entrega-6 (trace). "
            "Escribí una consulta, Enter vacío para la demo LangGraph vs CrewAI, "
            "o 'salir'."
        )
    else:
        print("Demo orquestador pre-entrega-6 — escribí una consulta o 'salir'.")
    while True:
        try:
            texto = input("\nConsulta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return 0
        if texto.lower() in _COMANDOS_SALIDA:
            print("Hasta luego.")
            return 0
        if not texto:
            if not guardar:
                continue
            texto = TRACE_QUERY
            print(f"(demo) {texto}\n")
        try:
            _correr(graph, texto, guardar=guardar, echo_query=False)
        except Exception as exc:
            print(f"\nError al invocar el grafo: {type(exc).__name__}: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demo del orquestador multi-agente.")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="REPL interactivo: hops en vivo, pisa traces/ y output.md",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    _verificar_credenciales()
    from graph import build_graph

    graph = build_graph()
    return _repl(graph, guardar=args.trace)


if __name__ == "__main__":
    sys.exit(main())
