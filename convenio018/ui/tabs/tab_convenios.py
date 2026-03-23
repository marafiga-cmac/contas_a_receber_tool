"""Aba: Convênios 018.

Mantém o fluxo principal do app:
- Seleção de convênio + data
- Processamento (busca nas planilhas 2025 e 2026) e cache em session_state
- Fluxo especial CABERGS (CMAP)

Observação:
- A maior parte das regras de negócio permanece em `convenio018.services.api`.
"""

from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import streamlit as st

from ...config import SHEET_IDS
from ...services.api import (
    make_recursos_df,
    make_remessas_df,
    compute_totals_recursos,
    compute_totals_remessas,
    marcar_encontrados_csv,
    processar_cabergs_arquivos,
    processar_convenio,
    processar_csv_analise,
    render_form,
)


def render() -> None:
    st.header("Selecionar Convênio e Data de Pagamento")

    # Form principal (usa unidade da sidebar, já salva em session_state)
    result = render_form()

    # ------------------------------------------------------------------
    # CABERGS (CMAP): fluxo automático (sem botões do Google Sheets)
    # ------------------------------------------------------------------
    unidade = st.session_state.get("unidade") or "CMAP"
    is_cabergs = (unidade == "CMAP") and (
        str(result.get("convenio") or "").strip().lower() == "cabergs id"
    )

    if is_cabergs:
        cabergs_files = result.get("cabergs_xls_files") or []

        if cabergs_files:
            try:
                df_cabergs = processar_cabergs_arquivos(cabergs_files)
                st.subheader("Prévia do CABERGS (cabeçalho ajustado)")
                st.caption("Aplicado: B→C, AB→AF, AQ→AR | Extraído: G5 (Remessa) e X5 (Competência)")
                st.dataframe(df_cabergs, use_container_width=True)
                st.session_state["cabergs_df_xls"] = df_cabergs
            except Exception as e:
                st.error(f"Erro ao processar CABERGS: {e}")
                st.session_state["cabergs_df_xls"] = pd.DataFrame()
        else:
            st.info("Anexe o(s) arquivo(s) XLS/XLSX do CABERGS para exibir a tabela.")
            st.session_state["cabergs_df_xls"] = pd.DataFrame()

        st.markdown("---")
        st.subheader("Arquivo CSV para Análise (automático)")

        csv_file = st.file_uploader("Envie o arquivo CSV", type=["csv"], key="cabergs_csv_upload")

        if csv_file is not None:
            try:
                df_csv = processar_csv_analise(csv_file)
                st.session_state["cabergs_df_csv"] = df_csv
            except Exception as e:
                st.error(f"Erro ao processar CSV: {e}")
                st.session_state["cabergs_df_csv"] = pd.DataFrame()
        else:
            st.session_state["cabergs_df_csv"] = st.session_state.get("cabergs_df_csv") or pd.DataFrame()

        # Marcação no CSV — só após clicar em "Executar"
        df_xls_ss = st.session_state.get("cabergs_df_xls")
        df_csv_ss = st.session_state.get("cabergs_df_csv")

        st.markdown("---")

        if st.button("Executar", type="primary", key="btn_exec_mark_csv"):
            st.session_state["cabergs_exec_mark"] = True

        if st.session_state.get("cabergs_exec_mark"):
            if (
                isinstance(df_xls_ss, pd.DataFrame)
                and not df_xls_ss.empty
                and isinstance(df_csv_ss, pd.DataFrame)
                and not df_csv_ss.empty
            ):
                try:
                    df_csv_marked = marcar_encontrados_csv(df_xls_ss, df_csv_ss, flag_col="Encontrado")
                    st.session_state["cabergs_df_csv"] = df_csv_marked
                except Exception as e:
                    st.error(f"Erro ao marcar encontrados no CSV: {e}")
            else:
                st.warning("Anexe e processe os dois arquivos (XLS/XLSX e CSV) antes de executar.")

        # Sempre mostra a prévia do CSV (com checkbox)
        df_csv_show = st.session_state.get("cabergs_df_csv")
        if isinstance(df_csv_show, pd.DataFrame) and not df_csv_show.empty:
            if "Encontrado" not in df_csv_show.columns:
                df_csv_show = df_csv_show.copy()
                df_csv_show.insert(0, "Encontrado", False)

            disabled_cols = [c for c in df_csv_show.columns if c not in ("Encontrado", "Remessa (G5)", "Valor MV")]

            st.subheader("Prévia do CSV tratado")
            st.data_editor(
                df_csv_show,
                use_container_width=True,
                hide_index=True,
                disabled=disabled_cols,  # só a checkbox fica editável
                key="csv_preview_editor",
            )
            st.session_state["cabergs_df_csv"] = df_csv_show

        # CABERGS não segue para o fluxo de Google Sheets
        st.stop()

    # ------------------------------------------------------------------
    # Fluxo padrão (Google Sheets) para os convênios
    # ------------------------------------------------------------------
    if result.get("submitted"):
        if not result.get("convenio"):
            st.warning("Por favor, selecione um convênio.")
            return

        try:
            unidade = st.session_state.get("unidade") or "CMAP"
            sheets = SHEET_IDS[unidade]

            output_dir = "."
            token_full_path = os.path.join(output_dir, "token.json")

            items: list[dict] = []
            out_paths: list[str] = []
            anos_com_dados: list[str] = []

            # Busca em 2025 e 2026 e junta
            erros_por_ano = []

            for ano in ("2025", "2026"):
                try:
                    tmp_items = processar_convenio(
                        spreadsheet_id=sheets[ano],
                        sheet_name=result["convenio"],
                        data_pagamento=result["data_pagamento"],
                        client_secrets_path=st.session_state.get("client_secret_path") or "client_secret.json",
                        token_path=token_full_path,
                    )

                    if tmp_items:
                        items.extend(tmp_items)
                        anos_com_dados.append(ano)

                except Exception as e:
                    erros_por_ano.append(f"{ano}: {e}")

            if erros_por_ano:
                for err in erros_por_ano:
                    st.warning(f"Falha ao ler planilha: {err}")

            if not items:
                st.warning("⚠️ Nenhum dado encontrado nem em 2025 nem em 2026.")
                return

            st.info(f"📄 Pagamentos encontrados em: {', '.join(anos_com_dados)}")

            # DataFrames filtrados pela data
            df_rem = make_remessas_df(items, result["data_pagamento"])
            df_rec = make_recursos_df(items, result["data_pagamento"])

            # Totais
            rem_totals = compute_totals_remessas(df_rem)
            rec_totals = compute_totals_recursos(df_rec)

            # Guarda em sessão (para uso nas outras abas)
            st.session_state["selected_convenio"] = result["convenio"]
            st.session_state["selected_date"] = result["data_pagamento"]

            st.session_state["remessas_df"] = df_rem
            st.session_state["remessas_totais"] = rem_totals

            st.session_state["recursos_df"] = df_rec
            st.session_state["recursos_totais"] = rec_totals

            st.session_state["modelo_csv"] = result.get("modelo_csv", "")

            st.success("✅ Dados processados! Abra as abas de relatório para visualizar / imprimir / exportar CSV.")

        except Exception as e:
            st.error(f"Erro ao processar: {e}")
