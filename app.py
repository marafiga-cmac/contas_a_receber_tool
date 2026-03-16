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
)


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

    st.title("Identificação de Convênios")

    tab_form, tab_remessas, tab_recursos, tab_nfse, tab_capa, tab_unimed, tab_glosa_mantida = st.tabs(
        [
            "Convênios 018",
            "Relatório de Remessas",
            "Relatório de Recurso de Glosa",
            "Relatório NFS-e",
            "Relatório Capa",
            "Unimed",
            "Lançamentos Glosa Mantida",
        ]
    )

    with tab_form:
        render_convenios()

    with tab_remessas:
        render_remessas()

    with tab_recursos:
        render_recursos()

    with tab_nfse:
        render_nfse()

    with tab_capa:
        render_capa()

    with tab_unimed:
        render_unimed()

    with tab_glosa_mantida:
        render_glosa_mantida()


if __name__ == "__main__":
    main()
