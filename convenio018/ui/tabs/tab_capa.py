"""Aba: Relatório Capa.

Gera a capa consolidada por data de emissão de NFS-e, varrendo todos os
convênios da unidade, em 2025 e 2026.
"""

from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import streamlit as st

from ...config import SHEET_IDS
from ...services.api import (
    gerar_capa_nfse_por_data,
    get_convenios_por_unidade,
    render_relatorio_capa,
)


def render() -> None:
    st.subheader("Relatório Capa")

    unidade = st.session_state.get("unidade") or "CMAP"
    convenios, _ = get_convenios_por_unidade(unidade)

    data_capa = st.date_input("Data Emissão NFS-e", value=date.today(), key="capa_data")

    if st.button("Gerar Capa", type="primary"):
        try:
            output_dir = st.session_state.get("output_dir") or "."
            token_path = os.path.join(output_dir, "token.json")
            client_secret_path = st.session_state.get("client_secret_path") or "client_secret.json"

            sheets = SHEET_IDS[unidade]

            itens_total: list[dict] = []

            for ano in ("2025", "2026"):
                try:
                    out_path_tmp = gerar_capa_nfse_por_data(
                        spreadsheet_id=sheets[ano],
                        sheet_names=convenios,
                        data_emissao=str(data_capa),
                        output_dir=output_dir,
                        client_secrets_path=client_secret_path,
                        token_path=token_path,
                    )

                    with open(out_path_tmp, "r", encoding="utf-8") as f:
                        tmp_items = json.load(f) or []

                    if tmp_items:
                        st.info(f"📄 Capa: encontrados {len(tmp_items)} itens em {ano}")
                        itens_total.extend(tmp_items)

                except Exception as e:
                    st.warning(f"⚠️ Falha lendo {ano}: {e}")

            if not itens_total:
                st.warning("⚠️ Nenhuma NFS-e encontrada nem em 2025 nem em 2026.")
                st.stop()

            # Dedup e consolidação (se NFSe repetir)
            df_all = pd.DataFrame(itens_total)
            for c in ["NFSe", "Convenio", "Valor"]:
                if c not in df_all.columns:
                    df_all[c] = None

            df_all["Valor"] = pd.to_numeric(df_all["Valor"], errors="coerce").fillna(0.0)

            df_final = (
                df_all.groupby(["NFSe", "Convenio"], as_index=False)["Valor"]
                .sum()
                .sort_values(["Convenio", "NFSe"])
            )

            render_relatorio_capa(df_final.to_dict("records"), data_capa)

        except Exception as e:
            st.error(f"Erro ao gerar capa: {e}")
