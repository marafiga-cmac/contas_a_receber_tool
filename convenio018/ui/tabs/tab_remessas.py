"""Aba: Relatório de Remessas."""

from __future__ import annotations

from datetime import date

import streamlit as st

from ...services.api import render_relatorio_remessas


def render() -> None:
    render_relatorio_remessas(
        df=st.session_state.get("remessas_df"),
        totals=st.session_state.get("remessas_totais") or {},
        selected_date=st.session_state.get("selected_date") or date.today(),
        selected_convenio=st.session_state.get("selected_convenio") or "",
        json_path=st.session_state.get("json_path"),
        modelo_csv=st.session_state.get("modelo_csv"),
        df_recursos=st.session_state.get("recursos_df"),
        recursos_totais=st.session_state.get("recursos_totais"),
        unidade=st.session_state.get("unidade") or "CMAP",
    )
