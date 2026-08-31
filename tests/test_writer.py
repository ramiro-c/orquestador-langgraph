"""Writer por tema: slug de la consulta, path derivado y creación de outputs/."""

from __future__ import annotations

from agents.writer import OUTPUTS_DIR, make_writer_node, output_path_for, topic_slug
from state import initial_fields


def test_topic_slug_de_query_conocida():
    assert topic_slug("Redis vs Kafka") == "redis-vs-kafka"


def test_topic_slug_normaliza_acentos_y_signos():
    assert topic_slug("¿Qué se dice de LangGraph esta semana?") == (
        "que-se-dice-de-langgraph-esta-semana"
    )


def test_topic_slug_query_vacia_es_consulta():
    assert topic_slug("") == "consulta"
    assert topic_slug("   ") == "consulta"
    assert topic_slug("¿¡?!") == "consulta"


def test_topic_slug_trunca_a_max_len():
    query = "palabra " * 20
    slug = topic_slug(query, max_len=20)
    assert len(slug) <= 20
    assert not slug.endswith("-")


def test_output_path_for_dos_queries_distintas_dan_dos_paths():
    p1 = output_path_for("Redis vs Kafka")
    p2 = output_path_for("LangGraph vs CrewAI")
    assert p1 != p2
    assert p1.parent == OUTPUTS_DIR == p2.parent
    assert p1.name == "redis-vs-kafka.md"
    assert p2.name == "langgraph-vs-crewai.md"


def test_writer_node_crea_outputs_si_falta(tmp_path):
    from langchain_core.messages import HumanMessage

    dest = tmp_path / "outputs" / "tema.md"
    assert not dest.parent.exists()

    node = make_writer_node(dest)
    result = node(
        {
            **initial_fields(),
            "messages": [HumanMessage(content="¿Qué se dice de LangGraph?")],
            "research_notes": "hallazgos",
            "analysis": "positivo",
        }
    )

    assert dest.exists()
    assert result["output_path"] == str(dest)
