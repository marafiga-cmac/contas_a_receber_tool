"""Renderização do relatório de remessas."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ...services.exports_service import gerar_csv_lancamentos_bytes
from .print_templates import LOGO_PATH, _build_print_html, _df_for_print, _fmt_brl, _path_to_data_uri

def render_relatorio_remessas(
    df: pd.DataFrame,
    totals: dict,
    selected_date: date,
    selected_convenio: str,
    json_path: str | None,
    modelo_csv: str | None,
    df_recursos: pd.DataFrame | None,
    recursos_totais: dict | None,
    unidade: str,
):
    st.subheader("Relatório — Pagamento de Remessas")

    if df is None or len(df) == 0:
        st.info("Nenhum dado para a data informada.")
        return

    try:
        st.dataframe(
            df, hide_index=True, use_container_width=True,
            column_config={
                "Valor envio XML - Remessa": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor pgto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Valor glosado": st.column_config.NumberColumn(format="R$ %.2f"),
                "Imposto": st.column_config.NumberColumn(format="R$ %.2f"),
                "Glosa mantida": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    except Exception:
        st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Valor total envio XML", _fmt_brl(totals.get("total_envio_xml", 0)))
        st.metric("Valor total glosado", _fmt_brl(totals.get("total_glosado", 0)))
    with c2:
        st.metric("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0)))
        st.metric("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0)))
    with c3:
        st.metric("Valor total pago", _fmt_brl(totals.get("total_pago", 0)))
        st.metric("Número de remessas", f"{len(df)}")

    st.session_state["remessas_df"] = df
    st.session_state["remessas_totais"] = totals
    st.markdown("---")
    st.markdown("### Exportar lançamentos contábeis")

    if df_recursos is None:
        df_recursos = pd.DataFrame()
    if recursos_totais is None:
        recursos_totais = {}

    fname, csv_bytes = gerar_csv_lancamentos_bytes(
        df_remessas=df,
        rem_totals=totals,
        df_recursos=df_recursos,
        rec_totals=recursos_totais,
        selected_date=selected_date,
        selected_convenio=selected_convenio,
        modelo_csv_path=modelo_csv or "",
    )

    st.download_button(
        f"⬇️ Baixar CSV ({selected_convenio})",
        data=csv_bytes,
        file_name=fname,
        mime="text/csv",
        use_container_width=True,
        key="dl_csv_convenio",
    )

    st.markdown("### Versão para impressão")
    if not st.session_state.get("logo_data_uri"):
        st.session_state["logo_data_uri"] = _path_to_data_uri(
            st.session_state.get("logo_path") or LOGO_PATH
        )

    dfp = _df_for_print(
        df,
        ["Valor envio XML - Remessa", "Valor pgto", "Valor glosado", "Imposto", "Glosa mantida"],
    )
    table_html = dfp.to_html(index=False, border=0, escape=False)

    total_pairs = [
        ("Valor total envio XML", _fmt_brl(totals.get("total_envio_xml", 0))),
        ("Valor total glosado", _fmt_brl(totals.get("total_glosado", 0))),
        ("Valor total imposto", _fmt_brl(totals.get("total_imposto", 0))),
        ("Valor total glosa mantida", _fmt_brl(totals.get("total_glosa_mantida", 0))),
        ("Valor total pago", _fmt_brl(totals.get("total_pago", 0))),
        ("Número de remessas", f"{len(df)}"),
    ]

    html = _build_print_html(
        titulo="Relatório — Pagamento de Remessas",
        convenio=selected_convenio,
        data_str=selected_date.strftime("%d/%m/%Y"),
        table_html=table_html,
        total_pairs=total_pairs,
        logo_data_uri=st.session_state.get("logo_data_uri"),
    )
    components.html(html, height=800, scrolling=True)

