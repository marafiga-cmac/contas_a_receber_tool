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
    processar_convenio,
    render_form,
)


def render() -> None:
    st.header("Selecionar Convênio e Data de Pagamento")

    # Form principal (usa unidade da sidebar, já salva em session_state)
    result = render_form()



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
