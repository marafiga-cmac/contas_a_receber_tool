"""Sidebar do Streamlit.

Aqui ficam apenas componentes de interface (inputs) e persistência em
`st.session_state`. Qualquer regra de negócio deve permanecer em `services/`.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from ..config import DEFAULT_CLIENT_SECRET
from ..state import SESSION_DEFAULTS


@dataclass(frozen=True)
class SidebarState:
    """Retorno tipado da sidebar para facilitar testes/manutenção."""

    unidade: str
    client_secret_path: str


def ensure_session_defaults() -> None:
    """Garante chaves esperadas no session_state.

    Mantém compatibilidade com o código legado (que espera certas keys).
    """

    for k, v in SESSION_DEFAULTS.items():
        st.session_state.setdefault(k, v)


def render_sidebar() -> SidebarState:
    """Renderiza a sidebar e atualiza o `st.session_state`.

    Retorna um objeto com os valores principais usados no app.
    """

    with st.sidebar:
        st.header("Centro Médico")

        unidade = st.radio(
            "Unidade",
            options=["CMAP", "CMAC"],
            index=(
                ["CMAP", "CMAC"].index(st.session_state.get("unidade"))
                if st.session_state.get("unidade") in ("CMAP", "CMAC")
                else 0
            ),
            help="Escolha o centro para carregar a planilha correta (CMAP ou CMAC).",
        )
        st.session_state["unidade"] = unidade

        st.markdown("---")
        st.subheader("Credenciais Google")

        cred_file = st.file_uploader(
            "Envie o client_secret.json (OAuth Desktop)",
            type=["json"],
            help="Peça ao TI para gerar no Google Cloud (OAuth Client ID tipo 'Desktop App').",
        )

        if cred_file is not None:
            # Mantém o comportamento antigo: salva no diretório atual
            with open(DEFAULT_CLIENT_SECRET, "wb") as f:
                f.write(cred_file.read())
            st.session_state["client_secret_path"] = DEFAULT_CLIENT_SECRET
            st.success(
                "Credenciais salvas com sucesso! Agora você pode autorizar o acesso ao Google Sheets."
            )

        client_secret_path = st.text_input(
            "Caminho do client_secret.json",
            value=st.session_state.get("client_secret_path") or DEFAULT_CLIENT_SECRET,
            help="Se você já salvou o arquivo em outro lugar, informe aqui.",
        ).strip()

        st.session_state["client_secret_path"] = client_secret_path or DEFAULT_CLIENT_SECRET

    return SidebarState(
        unidade=st.session_state["unidade"],
        client_secret_path=st.session_state["client_secret_path"],
    )
