"""Aba: Identificação Unimed.

Fluxo:
1) Upload XLSX + CSV
2) Executar: gera JSON e mantém na sessão
3) Editor: permite ajustar Entidade e salvar no JSON
4) Export: download JSON + CSV de lançamentos
"""

from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

from ...services.api import (
    gerar_csv_lancamentos_unimed_bytes,
    processar_identificacao_unimed,
)


def render() -> None:
    st.subheader("Identificação Unimed")

    col1, col2 = st.columns(2)

    with col1:
        up_xlsx = st.file_uploader(
            "Envie a planilha base (XLSX)",
            type=["xlsx"],
            key="unimed_xlsx",
        )

    with col2:
        up_csv = st.file_uploader(
            "Envie o arquivo de referência (CSV)",
            type=["csv"],
            key="unimed_csv",
        )

    threshold = st.slider(
        "Similaridade mínima",
        min_value=0.60,
        max_value=0.95,
        value=0.78,
        step=0.01,
        key="unimed_threshold",
    )

    # 1) BOTÃO: gera JSON e guarda payload na sessão
    if st.button("Executar", type="primary", key="btn_exec_unimed"):
        if up_xlsx is None or up_csv is None:
            st.warning("Envie os dois arquivos (XLSX e CSV) antes de executar.")
        else:
            try:
                payload = processar_identificacao_unimed(
                    xlsx_file=up_xlsx,
                    csv_file=up_csv,
                    threshold=float(threshold),
                )

                st.session_state["unimed_payload"] = payload

                # limpa editor antigo (porque gerou um JSON novo)
                st.session_state.pop("unimed_df_edit", None)

                st.success("✅ Tabela Unimed processada e carregada para edição!")

            except Exception as e:
                st.error(f"Erro ao processar Identificação Unimed: {e}")

    st.markdown("---")

    # 2) EDITOR: fora do botão para não sumir ao clicar
    payload = st.session_state.get("unimed_payload")

    if payload:
        st.caption(
            f"Preenchidos: {payload['meta']['entidades_preenchidas']} / "
            f"{payload['meta']['total_linhas_xlsx']} (threshold={payload['meta']['threshold']})"
        )

        df_from_payload = pd.DataFrame(
            [
                {
                    "linha_xlsx": it.get("linha_xlsx"),
                    "Titular": it.get("Titular"),
                    "Entidade": it.get("Entidade"),
                    "Match?": it.get("match", {}).get("encontrou"),
                    "Score": it.get("match", {}).get("score"),
                }
                for it in (payload.get("items") or [])
            ]
        )

        df_base = st.session_state.get("unimed_df_edit", df_from_payload)

        st.write("Edite a coluna **Entidade** e depois clique em **Atualizar JSON**:")

        edited_df = st.data_editor(
            df_base,
            use_container_width=True,
            hide_index=True,
            disabled=["linha_xlsx", "Titular", "Match?", "Score"],
            key="unimed_editor",
        )

        st.session_state["unimed_df_edit"] = edited_df

        colA, colB = st.columns(2)

        with colA:
            if st.button("💾 Atualizar JSON com edições", type="primary", key="btn_save_unimed"):
                entidade_map = dict(zip(edited_df["linha_xlsx"], edited_df["Entidade"]))

                for it in payload.get("items", []):
                    lx = it.get("linha_xlsx")
                    if lx in entidade_map:
                        it["Entidade"] = "" if entidade_map[lx] is None else str(entidade_map[lx]).strip()
                        if isinstance(it.get("row_xlsx"), dict) and "Entidade" in it["row_xlsx"]:
                            it["row_xlsx"]["Entidade"] = it["Entidade"]

                preenchidas = sum(1 for it in payload.get("items", []) if str(it.get("Entidade") or "").strip() != "")
                payload["meta"]["entidades_preenchidas"] = int(preenchidas)

                st.session_state["unimed_payload"] = payload
                st.session_state["unimed_df_edit"] = edited_df

                st.success("✅ Memória atualizada com as alterações!")
                st.rerun()

        with colB:
            st.download_button(
                "⬇️ Baixar JSON atualizado",
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="saida_identificacao_unimed.json",
                mime="application/json",
                use_container_width=True,
                key="dl_json_unimed",
            )

        nome_csv, csv_bytes = gerar_csv_lancamentos_unimed_bytes(payload)

        st.download_button(
            "⬇️ Baixar CSV de lançamentos (Unimed)",
            data=csv_bytes,
            file_name=nome_csv,
            mime="text/csv",
            use_container_width=True,
            key="dl_lanc_unimed",
        )

    else:
        st.info("Envie os arquivos e clique em **Executar Identificação** para gerar e editar.")
