"""Entry-point do Streamlit.

Rode com:
    streamlit run app.py

Estrutura (refactor):
- `convenio018/` contém o pacote do app (UI + serviços)
- `assets/` contém ícones e imagens

Este arquivo é propositalmente pequeno: só orquestra a UI.
"""

from __future__ import annotations

import streamlit as st

from convenio018.config import APP_ICON_PATH
from convenio018.ui.sidebar import ensure_session_defaults, render_sidebar
from convenio018.ui.tabs import (
    render_convenios,
    render_remessas,
    render_recursos,
    render_nfse,
    render_capa,
    render_unimed,
    render_glosa_mantida,
    render_ipe,
    render_controle,
)


def render_identificacao_convenios():
    st.title("Identificação de Convênios")
    tab_form, tab_remessas, tab_recursos = st.tabs([
        "Convênios 018",
        "Relatório de Remessas",
        "Relatório de Recurso de Glosa"
    ])
    with tab_form:
        render_convenios()
    with tab_remessas:
        render_remessas()
    with tab_recursos:
        render_recursos()


def main() -> None:
    # Config do Streamlit
    icon = str(APP_ICON_PATH) if APP_ICON_PATH.exists() else None
    st.set_page_config(
        page_title="Identificação de Convênios",
        page_icon=icon,
        layout="wide",
    )

    ensure_session_defaults()
    _sidebar = render_sidebar()

    paginas = {
        "Controle": [
            st.Page(
                render_controle,
                title="Emissão e Identificação",
                icon=":material/monitoring:",
                url_path="emissao-identificacao",
            ),
        ],
        "Rotinas Usuais": [
            st.Page(
                render_identificacao_convenios,
                title="Identificação Convênios",
                icon=":material/home:",
                default=True,
                url_path="identificacao-convenios",
            ),
            st.Page(
                render_nfse,
                title="Relatório NFS-e",
                icon=":material/receipt_long:",
                url_path="relatorio-nfse",
            ),
            st.Page(
                render_capa,
                title="Relatório Capa",
                icon=":material/summarize:",
                url_path="relatorio-capa",
            ),
            st.Page(
                render_unimed,
                title="Unimed",
                icon=":material/medical_services:",
                url_path="unimed",
            ),
            st.Page(
                render_glosa_mantida,
                title="Lançamentos Glosa Mantida",
                icon=":material/fact_check:",
                url_path="lancamentos-glosa",
            ),
        ],
        "Rotinas Separadas": [
            st.Page(
                render_ipe,
                title="Identificação Ipê",
                icon=":material/account_balance:",
                url_path="identificacao-ipe",
            ),
        ],
    }

    nav = st.navigation(paginas)
    nav.run()


if __name__ == "__main__":
    main()
