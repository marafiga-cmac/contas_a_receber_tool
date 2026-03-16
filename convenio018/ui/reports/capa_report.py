"""Renderização do relatório de capa."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .print_templates import _build_print_html_capa

def render_relatorio_capa(items: list[dict], data_emissao: date):
    """Renderiza a Capa: NFSe / Convênio / Valor."""
    import streamlit.components.v1 as components

    st.subheader("NFSe Emitidas - Faturamento")

    if not items:
        st.info("Nenhuma NFS-e encontrada para esta data.")
        return

    df = pd.DataFrame(items).copy()
    for c in ["NFSe", "Convenio", "Valor"]:
        if c not in df.columns:
            df[c] = None
    df = df[["NFSe", "Convenio", "Valor"]]

    def _fmt_brl(x):
        try:
            v = float(x)
        except Exception:
            v = 0.0
        s = f"{v:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"

    df_show = df.copy()
    df_show["Valor"] = df_show["Valor"].apply(_fmt_brl)

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    table_html = (
        "<table>"
        "<thead><tr>"
        "<th class='col-nfse'>NFSe</th>"
        "<th class='col-convenio'>Convênio</th>"
        "<th class='col-valor'>Valor</th>"
        "</tr></thead><tbody>"
    )
    for _, r in df_show.iterrows():
        table_html += (
            f"<tr>"
            f"<td class='col-nfse'>{r['NFSe']}</td>"
            f"<td class='col-convenio'>{r['Convenio']}</td>"
            f"<td class='col-valor'>{r['Valor']}</td>"
            f"</tr>"
        )
    table_html += "</tbody></table>"

    titulo = "NFSe EMITIDAS - FATURAMENTO"
    data_str = data_emissao.strftime("%d/%m/%Y") if hasattr(data_emissao, "strftime") else str(data_emissao)
    html = _build_print_html_capa(
        titulo=titulo,
        data_str=data_str,
        table_html=table_html,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=850, scrolling=True)

