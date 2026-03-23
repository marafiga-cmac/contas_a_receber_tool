"""Formulário principal do fluxo de convênios."""

from __future__ import annotations

from datetime import date

import streamlit as st

from ...domain.convenio_rules import (
    CONVENIOS_CMAP,
    CMAC_GLOSA_TO_3303,
    CSV_HEADER_FIRST_ROW,
    DEPOSITO_SUBCONTA_BANCO,
    get_csv_convenio_overrides,
)
from ..reports.print_templates import LOGO_PATH, _path_to_data_uri, ensure_logo_defaults

ensure_logo_defaults()

def render_form():
    unidade = st.session_state.get("unidade") or "CMAP"

    # prefs para CSV conforme unidade
    header_cols = CSV_HEADER_FIRST_ROW.get(unidade, CSV_HEADER_FIRST_ROW["CMAP"])
    deposito_subconta = DEPOSITO_SUBCONTA_BANCO.get(
        unidade,
        DEPOSITO_SUBCONTA_BANCO["CMAP"]
    )

    st.session_state["csv_prefs"] = {
        "header_first_row": header_cols,
        "deposito_subconta_banco": deposito_subconta,
    }

    # convênios e overrides por unidade
    csv_convenio_overrides = get_csv_convenio_overrides(unidade)
    if unidade == "CMAP":
        convenios = sorted(CONVENIOS_CMAP, key=lambda s: s.lower())
    else:
        convenios = sorted(csv_convenio_overrides.keys(), key=lambda s: s.lower())

    st.session_state["csv_convenio_overrides"] = csv_convenio_overrides

    st.markdown("Selecione o **convênio** e a **data de pagamento**.")

    convenio = st.selectbox(
        "Convênio",
        options=[""] + convenios,
        index=(
            ([""] + convenios).index(
                st.session_state.get("selected_convenio") or ""
            )
            if (st.session_state.get("selected_convenio") or "") in ([""] + convenios)
            else 0
        ),
    )

    # --- REGRA (UI): CABERGS no CMAP -> permitir upload XLS/XLSX ---
    is_cabergs = (str(convenio or "").strip().lower() == "cabergs id")
    is_cmap = (str(unidade or "").strip().upper() == "CMAP")

    if is_cmap and is_cabergs:
        st.markdown("---")
        st.subheader("Arquivo adicional (CABERGS)")
        st.caption("Envie o arquivo XLS/XLSX do CABERGS para aplicarmos regras específicas (vamos tratar isso depois).")

        cabergs_xls_files = st.file_uploader(
        "Enviar arquivo(s) CABERGS (XLS/XLSX)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
        key="cabergs_xls_uploader",
        )

        st.session_state["cabergs_xls_files"] = cabergs_xls_files
    else:
        # limpa quando troca de convênio/unidade (evita ficar arquivo antigo na sessão)
        st.session_state["cabergs_xls_files"] = []

    # --- CABERGS (CMAP): sem data e sem botão; processa automaticamente pelo upload ---
    if is_cmap and is_cabergs:
        data_pagamento = None
        submitted = False
    else:
        data_pagamento = st.date_input(
            "Data de pagamento",
            value=st.session_state.get("selected_date") or date.today(),
            format="DD/MM/YYYY",
            help=(
                "Serão consideradas linhas cuja **Data pgto remessa** "
                "ou **Data pgto recurso** coincidam com a data informada."
            ),
        )

        submitted = st.button("Continuar", type="primary", use_container_width=True)

    modelo_csv = st.session_state.get("modelo_csv") or ""

    return {
        "submitted": submitted,
        "convenio": convenio,
        "data_pagamento": data_pagamento,
        "modelo_csv": modelo_csv,
        "cabergs_xls_files": st.session_state.get("cabergs_xls_files", []),
    }

