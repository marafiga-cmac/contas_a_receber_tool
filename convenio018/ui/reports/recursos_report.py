"""Renderização do relatório de recursos."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ...services.exports_service import gerar_csv_recursos_bytes
from .print_templates import LOGO_PATH, _build_print_html, _df_for_print, _fmt_brl, _path_to_data_uri

def render_relatorio_recursos(
    df: pd.DataFrame,
    totals: dict,
    selected_date: date,
    selected_convenio: str,
    unidade: str,
):
    st.subheader("Relatório — Recurso de Glosa")

    if df is None or len(df) == 0:
        st.info("Nenhum dado para a data informada.")
        return

    try:
        st.dataframe(
            df, hide_index=True, use_container_width=True,
            column_config={
                "Valor recursado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor glosado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor pago": st.column_config.NumberColumn(format="R$ %.2f"),
                "Imposto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Glosa mantida": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Valor total de Glosa", _fmt_brl(totals.get("total_glosa", 0)))
        st.metric("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0)))
    with c2:
        st.metric("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0)))
        st.metric("Valor total pago", _fmt_brl(totals.get("total_pago", 0)))
    with c3:
        st.metric("Número de remessas", f"{len(df)}")

    st.markdown("---")
    st.markdown("### Exportar lançamentos de recebimento de recurso de glosa")

    rem_df_ss = st.session_state.get("remessas_df")
    rem_totais_ss = st.session_state.get("remessas_totais") or {}

    fname_rec, csv_bytes_rec = gerar_csv_recursos_bytes(
        df_recursos=df,
        rec_totals=totals,
        df_remessas=rem_df_ss,
        rem_totals=rem_totais_ss,
        selected_date=selected_date,
        selected_convenio=selected_convenio,
        add_debito_if_only_resources=True,
    )

    st.download_button(
        f"⬇️ Baixar CSV de recursos ({selected_convenio})",
        data=csv_bytes_rec,
        file_name=fname_rec,
        mime="text/csv",
        use_container_width=True,
        key="dl_csv_recursos",
    )

    st.markdown("### Versão para impressão")
    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(
            st.session_state.get("logo_path") or LOGO_PATH
        )
    dfp = _df_for_print(
        df,
        ["Valor recursado", "Valor glosado", "Valor pago", "Imposto", "Glosa mantida"],
    )
    table_html = dfp.to_html(index=False, border=0, escape=False)

    total_pairs = [
        ("Valor total de Glosa", _fmt_brl(totals.get("total_glosa", 0))),
        ("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0))),
        ("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0))),
        ("Valor total pago", _fmt_brl(totals.get("total_pago", 0))),
        ("Número de remessas", f"{len(df)}"),
    ]

    html = _build_print_html(
        titulo="Relatório — Recurso de Glosa",
        convenio=selected_convenio,
        data_str=selected_date.strftime("%d/%m/%Y"),
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=800, scrolling=True)

