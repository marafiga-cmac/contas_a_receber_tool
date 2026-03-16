"""Aba: Relatório de Recurso de Glosa."""

from __future__ import annotations

from datetime import date

import streamlit as st

from ...services.api import render_relatorio_recursos


def render() -> None:
    render_relatorio_recursos(
        df=st.session_state.get("recursos_df"),
        totals=st.session_state.get("recursos_totais") or {},
        selected_date=st.session_state.get("selected_date") or date.today(),
        selected_convenio=st.session_state.get("selected_convenio") or "",
        unidade=st.session_state.get("unidade") or "CMAP",
    )
