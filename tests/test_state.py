"""Defaults del estado compartido."""

from __future__ import annotations

from state import initial_fields


def test_initial_fields_incluye_output_path_vacio():
    assert initial_fields()["output_path"] == ""
