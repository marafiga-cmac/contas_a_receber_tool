"""Aba: Relatório NFS-e.

- Permite localizar por data de emissão ou por número da NFS-e.
- Busca em 2025 e 2026 e consolida no mesmo relatório.
"""

from __future__ import annotations

import json
import os
from datetime import date

import streamlit as st

from ...config import SHEET_IDS
from ...services.api import (
    get_convenios_por_unidade,
    processar_nfse_para_json,
    render_relatorio_nfse_para_impressao,
)


def render() -> None:
    st.subheader("Relatório NFS-e")

    convenios, label = get_convenios_por_unidade(st.session_state.get("unidade") or "CMAP")
    convenio = st.selectbox(
        label,
        options=convenios,
        index=0 if convenios else None,
        key="nfse_convenio",
    )

    modo = st.radio(
        "Como deseja localizar?",
        ["Por data de emissão", "Por número da NFS-e"],
        horizontal=True,
    )

    col1, col2 = st.columns(2)
    data_emissao = None
    numero_nf = None

    with col1:
        if modo == "Por data de emissão":
            data_emissao = st.date_input("Data envio NF", value=date.today())
    with col2:
        if modo == "Por número da NFS-e":
            numero_nf = st.text_input("Número da NFS-e").strip()

    if st.button("Gerar Relatório", type="primary"):
        try:
            unidade = st.session_state.get("unidade") or "CMAP"
            sheets = SHEET_IDS[unidade]
            output_dir = st.session_state.get("output_dir") or "."

            token_path = os.path.join(output_dir, "token.json")
            client_secret_path = st.session_state.get("client_secret_path") or "client_secret.json"

            # UI -> backend
            if modo == "Por data de emissão":
                if not data_emissao:
                    st.warning("Informe a data de emissão.")
                    st.stop()

                modo_nfse = "data"
                valor_busca = str(data_emissao)  # YYYY-MM-DD

                st.session_state["nfse_ctx_convenio"] = convenio
                st.session_state["nfse_context"] = f"Data Emissão: {data_emissao.strftime('%d/%m/%Y')}"
                st.session_state["nfse_modo"] = "data"

            else:
                if not numero_nf:
                    st.warning("Informe o número da NFS-e.")
                    st.stop()

                modo_nfse = "numero"
                valor_busca = numero_nf.strip()

                st.session_state["nfse_ctx_convenio"] = convenio
                st.session_state["nfse_context"] = f"NFS-e: {numero_nf}"
                st.session_state["nfse_modo"] = "numero"

            # Busca em 2025 e 2026 e junta
            items_nfse: list[dict] = []
            anos_com_dados: list[str] = []

            for ano in ("2025", "2026"):
                try:
                    out_path_tmp = processar_nfse_para_json(
                        spreadsheet_id=sheets[ano],
                        sheet_name=convenio,
                        modo=modo_nfse,
                        valor=valor_busca,
                        output_dir=output_dir,
                        client_secrets_path=client_secret_path,
                        token_path=token_path,
                    )

                    with open(out_path_tmp, "r", encoding="utf-8") as fjson:
                        tmp_items = json.load(fjson) or []

                    if tmp_items:
                        items_nfse.extend(tmp_items)
                        anos_com_dados.append(ano)

                except Exception:
                    continue

            if not items_nfse:
                st.warning("⚠️ NFS-e não encontrada em 2025 nem em 2026.")
                st.stop()

            st.success(f"✅ Relatório gerado com dados de: {', '.join(anos_com_dados)}")

            render_relatorio_nfse_para_impressao(items_nfse)

        except Exception as e:
            st.error(f"Erro ao gerar Relatório NFS-e: {e}")
